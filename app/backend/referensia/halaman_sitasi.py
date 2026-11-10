"""Mesin Pencari Halaman Sitasi (Citation Page Finder) untuk Referensia.

Fitur:
1. Parsing berkas RIS (.ris / .txt) dari Mendeley, Zotero, Google Scholar, ScienceDirect, dll.
2. Melengkapi nomor halaman jurnal (Start Page / End Page / Page Range / Volume / Issue)
   via Crossref API & OpenAlex API.
3. Mencari letak nomor halaman kutipan spesifik (In-Text Citation Page Finder):
   Memindai teks PDF per halaman dengan pypdf untuk mencocokkan kalimat atau kata kunci kutipan,
   menemukan nomor halaman PDF dan estimasi nomor halaman terbitan jurnal, lengkap dengan snippet teks.
4. Menghasilkan format sitasi siap salin (APA 7th, IEEE, MLA) lengkap dengan nomor halaman.
5. Ekspor berkas RIS yang telah diperbarui dan rekapitulasi Word (.docx).
"""

import io
import os
import re
import unicodedata
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

import requests
from pypdf import PdfReader


def _norm_doi(doi: str) -> str:
    """Normalisasi format DOI (membersihkan awalan URL)."""
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", (doi or "").strip().lower())


def _bersihkan_spasi(teks: str) -> str:
    """Normalisasi spasi dan baris baru."""
    return re.sub(r"\s+", " ", teks or "").strip()


def _norm_teks_pencarian(teks: str) -> str:
    """Normalisasi teks untuk pencarian fuzzy/case-insensitive."""
    teks = unicodedata.normalize("NFKD", teks or "").encode("ascii", "ignore").decode("ascii")
    teks = teks.lower()
    # Bersihkan tanda hubung di akhir kata akibat pemenggalan baris (hyphenation)
    teks = re.sub(r"(\w+)-\s+(\w+)", r"\1\2", teks)
    teks = re.sub(r"[^a-z0-9\s]", " ", teks)
    return re.sub(r"\s+", " ", teks).strip()


def parse_ris_text(teks: str) -> List[Dict[str, Any]]:
    """Mem-parsing teks format RIS menjadi daftar entri referensi."""
    if not teks:
        return []

    # Pisahkan per rekaman RIS (berdasarkan tag 'ER  -')
    baris_mentah = teks.splitlines()
    rekaman_list: List[List[str]] = []
    current_rec: List[str] = []

    for b in baris_mentah:
        baris_strip = b.strip()
        if not baris_strip:
            continue
        current_rec.append(b)
        if re.match(r"^ER\s{1,2}-", baris_strip):
            rekaman_list.append(current_rec)
            current_rec = []

    if current_rec:
        rekaman_list.append(current_rec)

    hasil: List[Dict[str, Any]] = []

    for idx, lines in enumerate(rekaman_list, start=1):
        fields: Dict[str, List[str]] = {}
        last_tag: Optional[str] = None

        for baris in lines:
            m = re.match(r"^([A-Z0-9]{2})\s{1,2}-\s?(.*)$", baris)
            if m:
                last_tag = m.group(1).upper()
                val = m.group(2).strip()
                fields.setdefault(last_tag, []).append(val)
            elif last_tag and baris.startswith("   "):
                # Baris lanjutan (multi-line tag RIS)
                fields[last_tag][-1] += " " + baris.strip()

        # Lewati rekaman kosong
        if not fields or "ER" in fields and len(fields) == 1:
            continue

        def get_pertama(tags: List[str]) -> str:
            for t in tags:
                if t in fields and fields[t]:
                    v = fields[t][0].strip()
                    if v:
                        return v
            return ""

        tipe = get_pertama(["TY"]) or "JOUR"
        judul = get_pertama(["TI", "T1", "CT", "BT"])
        penulis_list = fields.get("AU", []) or fields.get("A1", []) or fields.get("A2", [])
        tahun = get_pertama(["PY", "Y1"])
        if tahun:
            m_th = re.search(r"\b(19\d\d|20\d\d)\b", tahun)
            tahun = m_th.group(1) if m_th else tahun[:4]

        sumber = get_pertama(["JO", "JF", "T2", "JA", "SO"])
        penerbit = get_pertama(["PB"])
        volume = get_pertama(["VL"])
        issue = get_pertama(["IS", "M1"])
        sp = get_pertama(["SP"])
        ep = get_pertama(["EP"])
        doi = _norm_doi(get_pertama(["DO", "DI"]))
        url = get_pertama(["UR", "L2"])
        pdf_path = get_pertama(["L1"])
        abstrak = get_pertama(["AB", "N2"])
        issn_isbn = get_pertama(["SN"])

        # Format rentang halaman yang ada
        halaman_ada = ""
        if sp and ep and sp != ep:
            halaman_ada = f"{sp}–{ep}"
        elif sp:
            halaman_ada = sp
        elif ep:
            halaman_ada = ep

        # Jika judul kosong tetapi ada info lain, beri judul default
        if not judul:
            if doi:
                judul = f"Referensi DOI {doi}"
            else:
                judul = f"Referensi #{idx}"

        hasil.append({
            "uid": f"ris_{idx}_{abs(hash(judul)) % 1000000:06d}",
            "no": idx,
            "tipe": tipe,
            "judul": judul,
            "penulis": [p.strip() for p in penulis_list if p.strip()],
            "tahun": tahun,
            "sumber": sumber,
            "penerbit": penerbit,
            "volume": volume,
            "issue": issue,
            "sp": sp,
            "ep": ep,
            "halaman_ada": halaman_ada,
            "doi": doi,
            "url": url,
            "pdf_link": pdf_path,
            "abstrak": abstrak,
            "issn": issn_isbn,
            "status_halaman": "lengkap" if halaman_ada else "belum_ada",
            "hasil_cari": None,
        })

    return hasil


SESI_HTTP = requests.Session()
SESI_HTTP.headers.update({
    "User-Agent": "ReferensiaDesktop/1.0 (https://github.com; mailto:referensia@app.local)"
})


def cari_metadata_halaman_crossref(doi: str = "", judul: str = "", penulis: str = "") -> Optional[Dict[str, Any]]:
    """Mencari metadata halaman, volume, issue, dan link via Crossref API."""
    try:
        if doi:
            url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
            res = SESI_HTTP.get(url, timeout=12)
            if res.status_code == 200:
                data = res.json().get("message", {})
                return _ekstrak_crossref_data(data)

        if judul:
            q = f"{judul} {penulis}".strip()
            url = f"https://api.crossref.org/works?query.bibliographic={urllib.parse.quote(q)}&rows=1"
            res = SESI_HTTP.get(url, timeout=12)
            if res.status_code == 200:
                items = res.json().get("message", {}).get("items", [])
                if items:
                    it = items[0]
                    # Verifikasi kesesuaian judul (minimal kata kunci cocok)
                    judul_ditemukan = (it.get("title") or [""])[0]
                    if _cek_kemiripan_judul(judul, judul_ditemukan):
                        return _ekstrak_crossref_data(it)
    except Exception:
        pass
    return None


def _cek_kemiripan_judul(j1: str, j2: str) -> bool:
    """Memastikan judul yang dikembalikan dari API sesuai dengan yang dicari."""
    s1 = set(_norm_teks_pencarian(j1).split())
    s2 = set(_norm_teks_pencarian(j2).split())
    if not s1 or not s2:
        return False
    inter = len(s1 & s2)
    return (inter / min(len(s1), len(s2))) >= 0.5


def _ekstrak_crossref_data(data: dict) -> Dict[str, Any]:
    pages = str(data.get("page") or "").strip()
    article_number = str(data.get("article-number") or "").strip()
    volume = str(data.get("volume") or "").strip()
    issue = str(data.get("issue") or "").strip()
    container = (data.get("container-title") or [""])[0]
    doi = _norm_doi(data.get("DOI") or "")

    sp, ep = "", ""
    if pages:
        parts = re.split(r"[-–—\s]+", pages)
        if len(parts) >= 2:
            sp, ep = parts[0], parts[1]
        elif len(parts) == 1:
            sp = parts[0]
    elif article_number:
        sp = article_number

    pdf_url = ""
    for lk in data.get("link", []):
        ct = lk.get("content-type", "")
        if "pdf" in ct and lk.get("URL"):
            pdf_url = lk.get("URL")
            break

    return {
        "sumber_api": "Crossref",
        "doi": doi,
        "page_raw": pages,
        "sp": sp,
        "ep": ep,
        "halaman_rentang": f"{sp}–{ep}" if sp and ep and sp != ep else (sp or article_number),
        "volume": volume,
        "issue": issue,
        "sumber": container,
        "article_number": article_number,
        "pdf_url": pdf_url,
    }


def cari_metadata_halaman_openalex(doi: str = "", judul: str = "") -> Optional[Dict[str, Any]]:
    """Mencari metadata biblio dan URL PDF Open Access via OpenAlex API."""
    try:
        url = ""
        if doi:
            url = f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(doi)}"
        elif judul:
            url = f"https://api.openalex.org/works?search={urllib.parse.quote(judul)}&per-page=1"

        if not url:
            return None

        res = SESI_HTTP.get(url, timeout=12)
        if res.status_code == 200:
            d = res.json()
            work = d if doi else (d.get("results") or [None])[0]
            if not work:
                return None

            if not doi and judul and not _cek_kemiripan_judul(judul, work.get("title") or ""):
                return None

            biblio = work.get("biblio") or {}
            sp = str(biblio.get("first_page") or "").strip()
            ep = str(biblio.get("last_page") or "").strip()
            vol = str(biblio.get("volume") or "").strip()
            iss = str(biblio.get("issue") or "").strip()

            best_oa = work.get("best_oa_location") or {}
            pdf_url = best_oa.get("pdf_url") or ""
            landing_url = best_oa.get("landing_page_url") or ""

            halaman_rentang = f"{sp}–{ep}" if sp and ep and sp != ep else sp

            return {
                "sumber_api": "OpenAlex",
                "doi": _norm_doi(work.get("doi") or doi),
                "sp": sp,
                "ep": ep,
                "halaman_rentang": halaman_rentang,
                "volume": vol,
                "issue": iss,
                "pdf_url": pdf_url or landing_url,
                "is_oa": (work.get("open_access") or {}).get("is_oa", False),
            }
    except Exception:
        pass
    return None


def cari_metadata_halaman_gabungan(item: Dict[str, Any]) -> Dict[str, Any]:
    """Menggabungkan pencarian Crossref dan OpenAlex untuk hasil paling akurat."""
    doi = _norm_doi(item.get("doi", ""))
    judul = item.get("judul", "")
    penulis_str = ", ".join(item.get("penulis", [])[:2])

    hasil_cr = cari_metadata_halaman_crossref(doi=doi, judul=judul, penulis=penulis_str)
    hasil_oa = cari_metadata_halaman_openalex(doi=doi or (hasil_cr.get("doi") if hasil_cr else ""), judul=judul)

    sp = item.get("sp") or (hasil_cr.get("sp") if hasil_cr else "") or (hasil_oa.get("sp") if hasil_oa else "")
    ep = item.get("ep") or (hasil_cr.get("ep") if hasil_cr else "") or (hasil_oa.get("ep") if hasil_oa else "")
    vol = item.get("volume") or (hasil_cr.get("volume") if hasil_cr else "") or (hasil_oa.get("volume") if hasil_oa else "")
    iss = item.get("issue") or (hasil_cr.get("issue") if hasil_cr else "") or (hasil_oa.get("issue") if hasil_oa else "")
    doi_final = doi or (hasil_cr.get("doi") if hasil_cr else "") or (hasil_oa.get("doi") if hasil_oa else "")
    sumber_final = item.get("sumber") or (hasil_cr.get("sumber") if hasil_cr else "")
    pdf_url = (hasil_oa.get("pdf_url") if hasil_oa else "") or (hasil_cr.get("pdf_url") if hasil_cr else "") or item.get("pdf_link") or ""

    halaman_rentang = ""
    if sp and ep and sp != ep:
        halaman_rentang = f"{sp}–{ep}"
    elif sp:
        halaman_rentang = sp
    elif ep:
        halaman_rentang = ep

    return {
        "sp": sp,
        "ep": ep,
        "halaman_rentang": halaman_rentang,
        "volume": vol,
        "issue": iss,
        "doi": doi_final,
        "sumber": sumber_final,
        "pdf_url": pdf_url,
        "status": "ditemukan" if halaman_rentang else "tidak_ditemukan",
    }


def unduh_atau_baca_pdf_bytes(pdf_source: Any) -> Optional[bytes]:
    """Mengambil bytes PDF dari path lokal, URL, atau raw bytes."""
    if isinstance(pdf_source, bytes):
        return pdf_source

    if isinstance(pdf_source, str):
        if os.path.isfile(pdf_source):
            try:
                with open(pdf_source, "rb") as f:
                    return f.read()
            except Exception:
                return None
        elif pdf_source.startswith("http://") or pdf_source.startswith("https://"):
            try:
                res = SESI_HTTP.get(pdf_source, timeout=20, stream=True)
                if res.status_code == 200:
                    ct = res.headers.get("content-type", "").lower()
                    # Hanya proses bila ukuran tidak berlebihan (maks 50 MB)
                    konten = res.content
                    if b"%PDF" in konten[:1024]:
                        return konten
            except Exception:
                return None
    return None


def pindai_halaman_kutipan_pdf(
    pdf_bytes: bytes,
    teks_kutipan: str,
    start_page_jurnal: str = "",
) -> Dict[str, Any]:
    """Memindai teks PDF per halaman untuk mencari nomor halaman teks kutipan."""
    if not pdf_bytes or not teks_kutipan.strip():
        return {"ditemukan": False, "pesan": "PDF atau teks kutipan kosong"}

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        total_halaman_pdf = len(reader.pages)
    except Exception as e:
        return {"ditemukan": False, "pesan": f"Gagal membaca berkas PDF: {e}"}

    query_norm = _norm_teks_pencarian(teks_kutipan)
    kata_query = [k for k in query_norm.split() if len(k) > 2]
    if not kata_query:
        kata_query = query_norm.split()

    # Cek apakah start_page_jurnal adalah bilangan
    sp_num = None
    if start_page_jurnal:
        m_num = re.search(r"\b(\d+)\b", str(start_page_jurnal))
        if m_num:
            sp_num = int(m_num.group(1))

    kecocokan_list: List[Dict[str, Any]] = []

    for no_hal_pdf, page in enumerate(reader.pages, start=1):
        try:
            teks_halaman = page.extract_text() or ""
        except Exception:
            teks_halaman = ""

        if not teks_halaman.strip():
            continue

        teks_hal_norm = _norm_teks_pencarian(teks_halaman)

        # 1. Exact substring match
        skor_cocok = 0.0
        pos_cocok = teks_hal_norm.find(query_norm)
        pos_mentah = -1

        if pos_cocok >= 0 and len(query_norm) >= 6:
            skor_cocok = 1.0
            # Ambil snippet dari teks asli
            pos_mentah = teks_halaman.lower().find(teks_kutipan.lower().strip()[:25])
        else:
            # 2. Token overlap search (jika parafrase atau beda format baris)
            kata_hal = set(teks_hal_norm.split())
            if kata_query:
                cocok_kata = sum(1 for k in kata_query if k in kata_hal)
                rasio = cocok_kata / len(kata_query)
                if rasio >= 0.70:
                    skor_cocok = round(rasio, 2)
                    # Cari kemunculan kata kunci pertama untuk posisi snippet
                    k1 = kata_query[0]
                    pos_mentah = teks_halaman.lower().find(k1)

        if skor_cocok >= 0.70:
            # Buat snippet konteks
            if pos_mentah >= 0:
                awal = max(0, pos_mentah - 120)
                akhir = min(len(teks_halaman), pos_mentah + len(teks_kutipan) + 120)
                snippet = _bersihkan_spasi(teks_halaman[awal:akhir])
            else:
                snippet = _bersihkan_spasi(teks_halaman[:250])

            # Estimasi halaman jurnal
            hal_jurnal_terdeteksi = ""
            # Cek angka di awal atau akhir halaman teks (header/footer)
            baris_hal = [b.strip() for b in teks_halaman.splitlines() if b.strip()]
            for b in (baris_hal[:3] + baris_hal[-3:]):
                m_hal = re.search(r"^\D*(\d{1,5})\D*$", b)
                if m_hal:
                    n = int(m_hal.group(1))
                    if 1 <= n <= 9999:
                        hal_jurnal_terdeteksi = str(n)
                        break

            if not hal_jurnal_terdeteksi and sp_num is not None:
                hal_jurnal_terdeteksi = str(sp_num + (no_hal_pdf - 1))

            kecocokan_list.append({
                "halaman_pdf": no_hal_pdf,
                "total_halaman_pdf": total_halaman_pdf,
                "halaman_jurnal": hal_jurnal_terdeteksi or str(no_hal_pdf),
                "skor_cocok": skor_cocok,
                "tipe_cocok": "Tepat (Exact)" if skor_cocok >= 0.99 else "Mirip (Fuzzy Overlap)",
                "snippet": f"… {snippet} …",
            })

    if not kecocokan_list:
        return {
            "ditemukan": False,
            "total_halaman_pdf": total_halaman_pdf,
            "pesan": f"Teks kutipan tidak ditemukan di seluruh {total_halaman_pdf} halaman PDF.",
        }

    # Urutkan berdasarkan skor kecocokan tertinggi
    kecocokan_list.sort(key=lambda x: x["skor_cocok"], reverse=True)
    terbaik = kecocokan_list[0]

    return {
        "ditemukan": True,
        "total_halaman_pdf": total_halaman_pdf,
        "halaman_pdf": terbaik["halaman_pdf"],
        "halaman_jurnal": terbaik["halaman_jurnal"],
        "skor_cocok": terbaik["skor_cocok"],
        "tipe_cocok": terbaik["tipe_cocok"],
        "snippet": terbaik["snippet"],
        "semua_kecocokan": kecocokan_list[:5],
    }


def format_sitasi_halaman(item: Dict[str, Any], halaman_jurnal: str = "") -> Dict[str, str]:
    """Menghasilkan sitasi In-Text dan Daftar Pustaka lengkap dengan nomor halaman."""
    penulis_list = item.get("penulis", [])
    tahun = item.get("tahun") or "t.t."
    judul = item.get("judul", "").rstrip(".")
    sumber = item.get("sumber", "")
    vol = item.get("volume", "")
    iss = item.get("issue", "")
    doi = item.get("doi", "")
    hlm = halaman_jurnal or item.get("halaman_ada") or item.get("sp") or ""

    # 1. Format Nama Sitasi Dalam Teks (In-Text)
    def _nama_keluarga(p: str) -> str:
        p = p.strip()
        if "," in p:
            return p.split(",")[0].strip()
        parts = p.split()
        return parts[-1] if parts else p

    if not penulis_list:
        nama_intext = "Anonim"
    elif len(penulis_list) == 1:
        nama_intext = _nama_keluarga(penulis_list[0])
    elif len(penulis_list) == 2:
        n1 = _nama_keluarga(penulis_list[0])
        n2 = _nama_keluarga(penulis_list[1])
        nama_intext = f"{n1} & {n2}"
    else:
        n1 = _nama_keluarga(penulis_list[0])
        nama_intext = f"{n1} et al."

    # Format Sitasi Dalam Teks
    intext_apa = f"({nama_intext}, {tahun}, hlm. {hlm})" if hlm else f"({nama_intext}, {tahun})"
    intext_ieee = f"[{item.get('no', 1)}, p. {hlm}]" if hlm else f"[{item.get('no', 1)}]"
    intext_mla = f"({nama_intext} {hlm})" if hlm else f"({nama_intext})"

    # 2. Format Daftar Pustaka (APA 7th)
    def _nama_belakang_depan(p: str) -> str:
        parts = p.split(",")
        if len(parts) >= 2:
            return f"{parts[0].strip()}, {parts[1].strip()[0]}."
        p_parts = p.strip().split()
        if len(p_parts) >= 2:
            return f"{p_parts[-1]}, {p_parts[0][0]}."
        return p

    if penulis_list:
        penulis_apa = ", ".join(_nama_belakang_depan(p) for p in penulis_list[:6])
        if len(penulis_list) > 6:
            penulis_apa += " et al."
    else:
        penulis_apa = "Anonim"

    # Volume & Issue string
    vol_iss = ""
    if vol and iss:
        vol_iss = f", {vol}({iss})"
    elif vol:
        vol_iss = f", {vol}"

    hal_dp = f", {item.get('halaman_rentang') or item.get('halaman_ada') or hlm}" if (item.get('halaman_rentang') or item.get('halaman_ada') or hlm) else ""
    doi_str = f" https://doi.org/{doi}" if doi else ""
    sumber_str = f". *{sumber}*" if sumber else ""

    daftar_pustaka_apa = f"{penulis_apa} ({tahun}). {judul}{sumber_str}{vol_iss}{hal_dp}.{doi_str}".strip()

    return {
        "intext_apa": intext_apa,
        "intext_ieee": intext_ieee,
        "intext_mla": intext_mla,
        "daftar_pustaka_apa": daftar_pustaka_apa,
    }


def proses_cari_halaman_item(item: Dict[str, Any], query_kutipan: str = "") -> Dict[str, Any]:
    """Memproses satu item referensi: mencari metadata halaman + memindai PDF bila relevan."""
    meta = cari_metadata_halaman_gabungan(item)

    sp = meta.get("sp") or item.get("sp") or ""
    ep = meta.get("ep") or item.get("ep") or ""
    halaman_rentang = meta.get("halaman_rentang") or item.get("halaman_ada") or ""
    vol = meta.get("volume") or item.get("volume") or ""
    iss = meta.get("issue") or item.get("issue") or ""
    doi = meta.get("doi") or item.get("doi") or ""
    sumber = meta.get("sumber") or item.get("sumber") or ""
    pdf_url = meta.get("pdf_url") or item.get("pdf_link") or ""

    hasil_scan_pdf = None

    # Jika user memberikan kalimat/teks kutipan untuk dicari halamannya di PDF:
    if query_kutipan.strip() and pdf_url:
        pdf_bytes = unduh_atau_baca_pdf_bytes(pdf_url)
        if pdf_bytes:
            hasil_scan_pdf = pindai_halaman_kutipan_pdf(
                pdf_bytes=pdf_bytes,
                teks_kutipan=query_kutipan,
                start_page_jurnal=sp,
            )

    hlm_final = (
        (hasil_scan_pdf.get("halaman_jurnal") if hasil_scan_pdf and hasil_scan_pdf.get("ditemukan") else "")
        or halaman_rentang
        or sp
    )

    item_diperbarui = {
        **item,
        "sp": sp,
        "ep": ep,
        "halaman_rentang": halaman_rentang,
        "volume": vol,
        "issue": iss,
        "doi": doi,
        "sumber": sumber,
        "pdf_link": pdf_url,
    }

    sitasi = format_sitasi_halaman(item_diperbarui, halaman_jurnal=hlm_final)

    return {
        "uid": item.get("uid"),
        "no": item.get("no"),
        "judul": item.get("judul"),
        "penulis": item.get("penulis"),
        "tahun": item.get("tahun"),
        "sumber": sumber,
        "volume": vol,
        "issue": iss,
        "sp": sp,
        "ep": ep,
        "halaman_rentang": halaman_rentang,
        "doi": doi,
        "pdf_url": pdf_url,
        "status_halaman": "lengkap" if halaman_rentang else ("ada_awal" if sp else "tidak_ditemukan"),
        "scan_pdf": hasil_scan_pdf,
        "sitasi": sitasi,
    }


def proses_cari_halaman_batch(items: List[Dict[str, Any]], query_kutipan: str = "") -> List[Dict[str, Any]]:
    """Memproses banyak item secara paralel menggunakan ThreadPoolExecutor."""
    with ThreadPoolExecutor(max_workers=min(8, max(2, len(items)))) as ex:
        hasil = list(ex.map(lambda it: proses_cari_halaman_item(it, query_kutipan), items))
    return hasil


def buat_ris_terupdate(items: List[Dict[str, Any]]) -> str:
    """Menghasilkan teks berkas RIS baru dengan nomor halaman SP/EP yang sudah dilengkapi."""
    keluar = []
    for r in items:
        tipe = r.get("tipe") or "JOUR"
        L = [f"TY  - {tipe}"]

        def tambah(tag, val):
            val = re.sub(r"\s+", " ", str(val or "")).strip()
            if val:
                L.append(f"{tag}  - {val}")

        tambah("TI", r.get("judul"))
        for p in r.get("penulis", []):
            tambah("AU", p)
        tambah("PY", r.get("tahun"))
        tambah("JO", r.get("sumber"))
        tambah("T2", r.get("sumber"))
        tambah("VL", r.get("volume"))
        tambah("IS", r.get("issue"))
        tambah("SP", r.get("sp"))
        tambah("EP", r.get("ep"))
        tambah("DO", r.get("doi"))
        tambah("UR", r.get("url") or (f"https://doi.org/{r['doi']}" if r.get("doi") else ""))
        if r.get("pdf_url") or r.get("pdf_link"):
            tambah("L1", r.get("pdf_url") or r.get("pdf_link"))
        if r.get("abstrak"):
            tambah("AB", r.get("abstrak"))
        L.append("ER  - ")
        keluar.append("\n".join(L))

    return "\n\n".join(keluar) + "\n"


def buat_rekap_halaman_docx(items: List[Dict[str, Any]], query_kutipan: str = "") -> bytes:
    """Membuat berkas Word (.docx) berisi rekap sitasi dan nomor halaman."""
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    # Margin 1 inch
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Judul
    h1 = doc.add_heading(level=1)
    run_h1 = h1.add_run("Rekap Halaman Sitasi & Referensi")
    run_h1.font.name = "Calibri"
    run_h1.font.size = Pt(18)
    run_h1.font.bold = True
    run_h1.font.color.rgb = RGBColor(0x3B, 0x82, 0xF6)

    sub = doc.add_paragraph()
    run_sub = sub.add_run("Dihasilkan secara otomatis oleh Referensia — Pencari Halaman Sitasi")
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(10)
    run_sub.font.italic = True
    run_sub.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    if query_kutipan:
        p_q = doc.add_paragraph()
        run_q = p_q.add_run(f'Kata kunci / teks kutipan yang dicari: "{query_kutipan}"')
        run_q.font.name = "Calibri"
        run_q.font.size = Pt(10.5)
        run_q.font.bold = True

    doc.add_paragraph()

    for idx, it in enumerate(items, start=1):
        p_judul = doc.add_paragraph()
        r_no = p_judul.add_run(f"[{idx}] ")
        r_no.font.bold = True
        r_judul = p_judul.add_run(it.get("judul", "Tanpa Judul"))
        r_judul.font.bold = True
        r_judul.font.size = Pt(12)

        p_info = doc.add_paragraph()
        penulis = ", ".join(it.get("penulis", [])) or "Anonim"
        tahun = it.get("tahun") or "t.t."
        sumber = it.get("sumber") or "Jurnal/Prosiding"
        vol = it.get("volume") or ""
        iss = it.get("issue") or ""
        vol_iss = f" Vol {vol}, No {iss}" if vol and iss else (f" Vol {vol}" if vol else "")
        r_info = p_info.add_run(f"Penulis: {penulis} ({tahun}) | {sumber}{vol_iss}")
        r_info.font.size = Pt(10)
        r_info.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

        # Info Halaman
        p_hal = doc.add_paragraph()
        hlm_rentang = it.get("halaman_rentang") or (f"{it['sp']}–{it['ep']}" if it.get("sp") and it.get("ep") else it.get("sp", ""))
        r_hlm_label = p_hal.add_run("Nomor Halaman Jurnal: ")
        r_hlm_label.font.bold = True
        r_hlm_label.font.size = Pt(10)
        r_hlm_val = p_hal.add_run(hlm_rentang or "Belum terdata")
        r_hlm_val.font.size = Pt(10)
        r_hlm_val.font.bold = bool(hlm_rentang)

        scan = it.get("scan_pdf")
        if scan and scan.get("ditemukan"):
            p_scan = doc.add_paragraph()
            r_scan_label = p_scan.add_run(f"Lokasi Kutipan: Halaman {scan.get('halaman_jurnal')} (Halaman PDF ke-{scan.get('halaman_pdf')})\n")
            r_scan_label.font.bold = True
            r_scan_label.font.size = Pt(10)
            r_scan_label.font.color.rgb = RGBColor(0x05, 0x96, 0x69)
            r_snip = p_scan.add_run(f"Kutipan yang ditemukan: {scan.get('snippet')}")
            r_snip.font.italic = True
            r_snip.font.size = Pt(9.5)

        sitasi = it.get("sitasi") or {}
        if sitasi.get("intext_apa"):
            p_sit = doc.add_paragraph()
            r_sit_lbl = p_sit.add_run("Sitasi In-Text APA: ")
            r_sit_lbl.font.bold = True
            r_sit_lbl.font.size = Pt(9.5)
            r_sit_val = p_sit.add_run(sitasi["intext_apa"])
            r_sit_val.font.size = Pt(9.5)

        if sitasi.get("daftar_pustaka_apa"):
            p_dp = doc.add_paragraph()
            p_dp.paragraph_format.left_indent = Inches(0.5)
            p_dp.paragraph_format.first_line_indent = Inches(-0.5)
            r_dp_lbl = p_dp.add_run("Daftar Pustaka APA: ")
            r_dp_lbl.font.bold = True
            r_dp_lbl.font.size = Pt(9.5)
            r_dp_val = p_dp.add_run(sitasi["daftar_pustaka_apa"])
            r_dp_val.font.size = Pt(9.5)

        doc.add_paragraph("—" * 40)

    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

