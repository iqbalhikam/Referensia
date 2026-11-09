# =====================================================================
#  Referensia v1.0 — Buru Referensi Ilmiah Otomatis
#  Fitur baru : kuota NASIONAL & INTERNASIONAL yang PAS (tidak kurang,
#               tidak lebih). Mesin terus memperluas pencarian sampai
#               jumlahnya tepat.
#  v3         : rentang/umur tahun referensi + Google Dorks (filetype:pdf)
#  Metadata   : OpenAlex + Crossref (gratis, resmi)
#  PDF        : hanya sumber OPEN ACCESS / legal
# =====================================================================
import os, io, re, sys, json, math, time, html, base64, zipfile, shutil, datetime, unicodedata, warnings
import urllib.parse as up
from concurrent.futures import ThreadPoolExecutor

import requests
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

warnings.filterwarnings("ignore")
try:
    from pypdf import PdfReader
except ImportError:  # dipasang otomatis bila belum ada
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pypdf"], check=False)
    try:
        from pypdf import PdfReader
    except ImportError:
        PdfReader = None
try:
    import google.colab  # noqa: F401
    DI_COLAB = True
except ImportError:
    DI_COLAB = False

WARNA = {"bg": "#0E0F1F", "panel": "#171831", "pink": "#818CF8", "violet": "#FBBF24",
         "teks": "#F1F0FF", "abu": "#9C9BC4"}
WARNA_KAT = {"Nasional": "#818CF8", "Internasional": "#FBBF24"}
IKON_KAT = {"Nasional": "🇮🇩", "Internasional": "🌍"}
WIB = datetime.timezone(datetime.timedelta(hours=7))
MAKS_BYTE_PDF = 80 * 1024 * 1024

_PROG = None

# Konsol Windows (cp1252) tidak bisa menulis emoji — paksa UTF-8 agar print tidak crash.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

def _emit(kind, **data):
    if _PROG:
        try:
            _PROG({"event": kind, **data})
        except Exception:
            pass

class _LogTee:
    """Teruskan print() mesin sebagai event log ke UI, tetap tulis ke stdout asli."""
    def __init__(self, asli):
        self.asli, self.buf = asli, ""
    def write(self, t):
        self.asli.write(t)
        self.buf += t
        while "\n" in self.buf:
            baris, self.buf = self.buf.split("\n", 1)
            if baris.strip():
                _emit("log", text=baris.rstrip())
    def flush(self):
        self.asli.flush()
    def __getattr__(self, nama):
        return getattr(self.asli, nama)

SESI = requests.Session()
SESI.headers.update({"User-Agent": "Mozilla/5.0 (Referensia/1.0)"})
_adapter = requests.adapters.HTTPAdapter(pool_connections=16, pool_maxsize=16, max_retries=1)
SESI.mount("https://", _adapter)
SESI.mount("http://", _adapter)

KATA_UMUM = set("""
yang dan di ke dari pada untuk dengan dalam terhadap oleh atau ini itu adalah sebagai juga tidak akan
dapat bisa ada antara serta secara bagi tentang karena maka agar sehingga namun tetapi hingga telah sudah
para sebuah suatu kepada lebih sangat masih pun saja yaitu yakni dll dsb studi kasus penelitian analisis
pengaruh hubungan peran dampak tinjauan kajian upaya penerapan implementasi melalui berbasis efektivitas
kota kabupaten tahun pelajaran semester kelas tingkat jurnal skripsi tesis disertasi artikel buku
the of and in on to for with by from at as an a is are was were be been this that these those its it into
using use used based via study studies analysis effect effects impact role review case between among
toward towards their our we not or but how what which within upon about influence relationship
""".split())

JENIS_OPENALEX = {
    "Semua": "article|book|book-chapter|dissertation|preprint|review|report",
    "Artikel Jurnal": "article|review",
    "Buku / Bab Buku": "book|book-chapter",
    "Skripsi / Tesis / Disertasi": "dissertation",
}
JENIS_CROSSREF = {
    "Semua": ["journal-article", "book", "book-chapter", "monograph", "edited-book",
              "dissertation", "posted-content", "report", "proceedings-article"],
    "Artikel Jurnal": ["journal-article", "proceedings-article"],
    "Buku / Bab Buku": ["book", "book-chapter", "monograph", "edited-book"],
    "Skripsi / Tesis / Disertasi": ["dissertation"],
}
CROSSREF_KE_JENIS = {"journal-article": "article", "proceedings-article": "article", "book": "book",
                     "monograph": "book", "edited-book": "book", "book-chapter": "book-chapter",
                     "dissertation": "dissertation", "posted-content": "preprint", "report": "report"}
NAMA_JENIS = {"article": "Artikel", "review": "Artikel Review", "book": "Buku", "book-chapter": "Bab Buku",
              "dissertation": "Skripsi/Tesis/Disertasi", "preprint": "Preprint", "report": "Laporan"}
FIELD_OPENALEX = ("id,doi,title,display_name,publication_year,type,language,cited_by_count,authorships,"
                  "primary_location,best_oa_location,locations,open_access,abstract_inverted_index,relevance_score")
PENANDA_LOKAL = ["universitas", "institut ", "indonesia", "sekolah tinggi", "politeknik", "stkip", "stie ",
                 "stai ", "uin ", "iain ", "lppm", "yayasan", "perkumpulan", "asosiasi", "ikatan ", "lembaga ",
                 "penerbit", "brin", "kementerian", "nusantara", "akademi ", "muhammadiyah", "nahdlatul"]


# ============================ utilitas teks ============================
def bersih(s):
    s = re.sub(r"<[^>]+>", " ", str(s or ""))
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def _ascii(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()

def tokenisasi(s):
    return [t for t in re.findall(r"[a-z0-9]+", _ascii(s).lower())
            if len(t) > 2 and t not in KATA_UMUM and not t.isdigit()]

def abstrak_openalex(inv):
    if not inv:
        return ""
    posisi = [(i, kata) for kata, idx in inv.items() for i in idx]
    return " ".join(k for _, k in sorted(posisi))

AWALAN = {"", "me", "mem", "men", "meng", "meny", "pe", "pem", "pen", "peng", "peny", "per",
          "ber", "be", "di", "ter", "ke", "se", "un", "re"}
AKHIRAN = {"", "an", "kan", "i", "nya", "annya", "lah", "s", "es", "ing", "ed", "al", "ly", "ion", "ions"}

def _cocok_kata(k, t):
    """Cocokkan kata + imbuhan umum (belajar ~ pembelajaran, media ≠ mediator)."""
    if k == t:
        return True
    if len(k) < 4:
        return False
    i = t.find(k)
    return i >= 0 and t[:i] in AWALAN and t[i + len(k):] in AKHIRAN

def cocok(kunci, token_set):
    return any(_cocok_kata(kunci, t) or _cocok_kata(t, kunci) for t in token_set)

_PENANDA_ID = {"dan", "yang", "di", "terhadap", "pada", "dengan", "untuk", "dalam", "dari", "sebagai",
               "melalui", "pengaruh", "analisis", "hubungan", "penerapan"}
_PENANDA_EN = {"the", "of", "and", "in", "on", "for", "with", "to", "from", "an", "a", "toward", "using", "among"}

def tebak_bahasa(teks):
    kata = re.findall(r"[a-z]+", _ascii(teks).lower())
    skor_id = sum(k in _PENANDA_ID for k in kata)
    skor_en = sum(k in _PENANDA_EN for k in kata)
    return "id" if skor_id > skor_en else ("en" if skor_en > skor_id else "")

def email_valid(e):
    e = (e or "").strip()
    return e if re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}", e) and not e.endswith("example.com") else ""

def nama_aman(s, maks=90):
    s = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", str(s or ""))
    s = re.sub(r"\s+", " ", s).strip(" .")
    if len(s) > maks:
        s = s[:maks].rsplit(" ", 1)[0].strip(" .")
    return s or "Tanpa Judul"

def slug(s, maks=40):
    s = re.sub(r"[^A-Za-z0-9]+", "_", _ascii(s)).strip("_")
    return s[:maks].rstrip("_") or "topik"

def nama_file_pdf(rec):
    judul = nama_aman(rec["judul"])
    if rec["doi"]:
        return f"{nama_aman(rec['doi'].replace('/', '_'), 70)} - {judul}.pdf"
    return f"TanpaDOI-{nama_aman(rec['id'], 30)} - {judul}.pdf"

def potong(s, n):
    s = s or ""
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"

def penulis_singkat(p):
    if not p:
        return "-"
    return p[0] if len(p) == 1 else (f"{p[0]} & {p[1]}" if len(p) == 2 else f"{p[0]} dkk.")

def kunci_judul(judul):
    return re.sub(r"[^a-z0-9]", "", _ascii(judul).lower())[:80]


# ============================ terjemahan topik ============================
def terjemahkan(teks, ke):
    """Terjemahkan topik (gratis, tanpa API key). Return (hasil, bahasa_asal)."""
    try:
        r = SESI.get("https://translate.googleapis.com/translate_a/single",
                     params={"client": "gtx", "sl": "auto", "tl": ke, "dt": "t", "q": teks}, timeout=15)
        d = r.json()
        hasil = "".join(seg[0] for seg in d[0] if seg and seg[0]).strip()
        if hasil:
            return hasil, (d[2] or "")
    except Exception:
        pass
    try:
        asal = "en" if ke == "id" else "id"
        r = SESI.get("https://api.mymemory.translated.net/get", params={"q": teks, "langpair": f"{asal}|{ke}"}, timeout=15)
        hasil = bersih(r.json()["responseData"]["translatedText"])
        if hasil and "MYMEMORY" not in hasil.upper():
            return hasil, asal
    except Exception:
        pass
    return teks, ""

def siapkan_topik(topik, topik_inggris_manual=""):
    hasil_en, asal = terjemahkan(topik, "en")
    if asal == "en" or (not asal and tebak_bahasa(topik) == "en"):
        topik_en = topik
        topik_id = terjemahkan(topik, "id")[0]
    else:
        topik_id, topik_en = topik, hasil_en
    topik_en_skor = topik_en
    if (topik_inggris_manual or "").strip():
        manual = bersih(topik_inggris_manual)
        # versi manual dipakai untuk mencari; gabungan manual + terjemahan dipakai untuk menilai konteks
        topik_en_skor = manual if manual.lower() == topik_en.lower() else f"{manual} {topik_en}"
        topik_en = manual
    return topik_id, topik_en, topik_en_skor


# ============================ data & pencarian ============================
def rapikan_openalex(w):
    doi = (w.get("doi") or "").replace("https://doi.org/", "").strip().lower()
    pl = w.get("primary_location") or {}
    src = pl.get("source") or {}
    pdfs, halaman = [], []
    for loc in [w.get("best_oa_location")] + list(w.get("locations") or []):
        if not loc:
            continue
        if loc.get("pdf_url"):
            pdfs.append(loc["pdf_url"])
        if loc.get("is_oa") and loc.get("landing_page_url"):
            halaman.append(loc["landing_page_url"])
    oa = w.get("open_access") or {}
    if oa.get("oa_url"):
        halaman.append(oa["oa_url"])
    penulis = [(a.get("author") or {}).get("display_name") for a in (w.get("authorships") or [])]
    wid = (w.get("id") or "").rsplit("/", 1)[-1]
    judul = bersih(w.get("title") or w.get("display_name"))
    return dict(
        uid=doi or wid or kunci_judul(judul), id=wid, doi=doi, judul=judul, penulis=[p for p in penulis if p],
        tahun=w.get("publication_year"), jenis=w.get("type") or "",
        sumber=bersih(src.get("display_name")), sumber_id=(src.get("id") or "").rsplit("/", 1)[-1],
        sumber_tipe=src.get("type") or "",
        issn=bersih(src.get("issn_l") or next(iter(src.get("issn") or []), "")),
        penerbit=bersih(src.get("host_organization_name")), bahasa=w.get("language") or "", negara=None,
        sitasi=w.get("cited_by_count") or 0, abstrak=bersih(abstrak_openalex(w.get("abstract_inverted_index"))),
        pdf_urls=list(dict.fromkeys(pdfs)), halaman_oa=list(dict.fromkeys(halaman)),
        halaman=pl.get("landing_page_url") or "",
        url=f"https://doi.org/{doi}" if doi else (pl.get("landing_page_url") or w.get("id") or ""),
        skor_api=float(w.get("relevance_score") or 0), asal="OpenAlex", is_oa=bool(oa.get("is_oa")),
        sudah_dilengkapi=False)

def rapikan_crossref(it):
    doi = (it.get("DOI") or "").strip().lower()
    try:
        tahun = it["issued"]["date-parts"][0][0]
    except Exception:
        tahun = None
    penulis = []
    for a in it.get("author") or []:
        nama = " ".join(x for x in [a.get("given"), a.get("family")] if x) or a.get("name")
        if nama:
            penulis.append(nama)
    judul = bersih((it.get("title") or [""])[0])
    return dict(
        uid=doi or kunci_judul(judul), id=doi, doi=doi, judul=judul, penulis=penulis, tahun=tahun,
        jenis=CROSSREF_KE_JENIS.get(it.get("type"), it.get("type") or ""),
        sumber=bersih((it.get("container-title") or [""])[0]), sumber_id="", sumber_tipe="",
        issn=next(iter(it.get("ISSN") or []), ""),
        penerbit=bersih(it.get("publisher")),
        bahasa=tebak_bahasa(judul), negara=None, sitasi=it.get("is-referenced-by-count") or 0,
        abstrak=bersih(it.get("abstract")), pdf_urls=[], halaman_oa=[], halaman="",
        url=f"https://doi.org/{doi}", skor_api=float(it.get("score") or 0), asal="Crossref", is_oa=False,
        sudah_dilengkapi=False)


class Konteks:
    """Menyimpan pengaturan & status satu kali pencarian."""
    def __init__(self, **kw):
        self.__dict__.update(kw)
        self.openalex_mati = False
        self.negara_cache = {}
        self.prefix_cache = {}
        self.doaj_cache = {}
        self.sinta_cache = {}
        self.predator_disaring = 0
        self.kat_kini = ""
        self.stat = {"ditarik": {"Nasional": 0, "Internasional": 0},
                     "duplikat": {"Nasional": 0, "Internasional": 0},
                     "predator": {"Nasional": 0, "Internasional": 0},
                     "dinilai": {"Nasional": set(), "Internasional": set()}}

    def oa_params(self, params):
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["mailto"] = self.email
        return params

    def matikan_openalex(self, kode):
        if not self.openalex_mati:
            print(f"   ⚠️ OpenAlex berhenti merespons (kode {kode}) — kemungkinan kuota gratis jaringan Colab habis.")
            print("      Mesin lanjut lewat Crossref. Agar lebih stabil, isi openalex_api_key (gratis di openalex.org/settings/api).")
        self.openalex_mati = True

def filter_dasar(ctx, longgar_tahun=False, longgar_doi=False):
    f = [f"type:{JENIS_OPENALEX.get(ctx.jenis, JENIS_OPENALEX['Semua'])}"]
    if not longgar_tahun:
        if ctx.tahun_dari:
            f.append(f"from_publication_date:{ctx.tahun_dari}-01-01")
        if ctx.tahun_sampai:
            f.append(f"to_publication_date:{ctx.tahun_sampai}-12-31")
    if ctx.wajib_doi and not longgar_doi:
        f.append("has_doi:true")
    return f

def openalex_tarik(ctx, query, mode, filters, maks=200, inti=None):
    if ctx.openalex_mati:
        return []
    inti = inti or " ".join(dict.fromkeys(tokenisasi(query))) or re.sub(r"[^\w\s]", " ", query)
    hasil, hal = [], 1
    while len(hasil) < maks and hal <= math.ceil(maks / 100):
        f = list(filters)
        params = {"per-page": 100, "page": hal, "select": FIELD_OPENALEX}
        if mode == "presisi":
            f.append(f"title_and_abstract.search:{inti}")
        else:
            params["search"] = query
        params["filter"] = ",".join(f)
        try:
            r = SESI.get("https://api.openalex.org/works", params=ctx.oa_params(params), timeout=45)
        except Exception:
            break
        if r.status_code != 200:
            ctx.matikan_openalex(r.status_code)
            break
        res = r.json().get("results", [])
        hasil += [rapikan_openalex(w) for w in res]
        if len(res) < 100:
            break
        hal += 1
    return hasil

def isi_negara(ctx, recs):
    """Cari negara asal jurnal/sumber (untuk membedakan nasional vs internasional)."""
    perlu = [r["sumber_id"] for r in recs if r["sumber_id"] and r["sumber_id"] not in ctx.negara_cache]
    perlu = list(dict.fromkeys(perlu))
    for i in range(0, len(perlu), 50):
        if ctx.openalex_mati:
            break
        bagian = perlu[i:i + 50]
        try:
            r = SESI.get("https://api.openalex.org/sources",
                         params=ctx.oa_params({"filter": "openalex:" + "|".join(bagian),
                                               "select": "id,country_code", "per-page": 50}), timeout=30)
            if r.status_code != 200:
                ctx.matikan_openalex(r.status_code)
                break
            for s in r.json().get("results", []):
                ctx.negara_cache[s["id"].rsplit("/", 1)[-1]] = (s.get("country_code") or "").upper()
        except Exception:
            break
        for b in bagian:
            ctx.negara_cache.setdefault(b, "")
    for r in recs:
        if r["sumber_id"] and r["negara"] is None and r["sumber_id"] in ctx.negara_cache:
            r["negara"] = ctx.negara_cache[r["sumber_id"]] or None

def crossref_tarik(ctx, query, maks=200, offset=0, longgar_tahun=False):
    filt = [f"type:{t}" for t in JENIS_CROSSREF.get(ctx.jenis, JENIS_CROSSREF["Semua"])]
    if not longgar_tahun:
        if ctx.tahun_dari:
            filt.append(f"from-pub-date:{ctx.tahun_dari}")
        if ctx.tahun_sampai:
            filt.append(f"until-pub-date:{ctx.tahun_sampai}")
    params = {"query": query, "rows": min(maks, 200), "offset": offset, "filter": ",".join(filt),
              "select": "DOI,title,author,issued,type,container-title,publisher,abstract,is-referenced-by-count,score,ISSN"}
    if ctx.email:
        params["mailto"] = ctx.email
    try:
        r = SESI.get("https://api.crossref.org/works", params=params, timeout=60)
        r.raise_for_status()
        return [rapikan_crossref(it) for it in r.json()["message"]["items"]]
    except Exception as e:
        print(f"   ⚠️ Crossref gagal ({e})")
        return []


def snowball_tarik(ctx, pool, maks=60):
    """Snowballing: tetangga sitasi (cites / cited_by) dari paper unggulan di pool."""
    seeds = sorted(pool.values(), key=lambda r: -r.get("skor", 0))[:3]
    hasil = []
    for s in seeds:
        wid = s.get("id") or ""
        if not wid.startswith("W"):
            continue
        for filt in (f"cites:{wid}", f"cited_by:{wid}"):
            if ctx.openalex_mati:
                break
            try:
                r = SESI.get("https://api.openalex.org/works",
                             params=ctx.oa_params({"filter": filt + "," + ",".join(filter_dasar(ctx)),
                                                   "per-page": 30, "select": FIELD_OPENALEX}), timeout=30)
                if r.status_code != 200:
                    ctx.matikan_openalex(r.status_code)
                    break
                hasil += [rapikan_openalex(w) for w in r.json().get("results", [])]
            except Exception:
                break
    return hasil[:maks]

# ============================ nasional / internasional ============================
def indikasi_nasional(r):
    for u in [r.get("halaman"), *r["pdf_urls"], *r["halaman_oa"]]:
        if u and re.match(r"https?://[^/]*\.id(?::\d+)?(/|$)", u, re.I):
            return True
    nama = f" {r['sumber']} {r['penerbit']} ".lower()
    if any(p in nama for p in PENANDA_LOKAL):
        return True
    return r["bahasa"] == "id"

def negara_dari_prefix(ctx, doi):
    """Cek lokasi penerbit lewat pemilik prefix DOI di Crossref (mis. 'Medan, Indonesia')."""
    prefix = doi.split("/")[0]
    if prefix in ctx.prefix_cache:
        return ctx.prefix_cache[prefix]
    hasil = None
    try:
        r = SESI.get(f"https://api.crossref.org/prefixes/{prefix}", params={"mailto": ctx.email} if ctx.email else {},
                     timeout=20)
        if r.status_code == 200:
            m = r.json()["message"]
            nama = (m.get("name") or "").lower()
            lokasi = ""
            mid = (m.get("member") or "").rstrip("/").rsplit("/", 1)[-1]
            if mid.isdigit():
                r2 = SESI.get(f"https://api.crossref.org/members/{mid}", timeout=20)
                if r2.status_code == 200:
                    lokasi = (r2.json()["message"].get("location") or "").lower()
            if "indonesia" in lokasi or re.match(r"^(pt|cv)\s", nama) or any(p in f" {nama} " for p in PENANDA_LOKAL):
                hasil = "ID"
            elif lokasi:
                hasil = "LUAR"
    except Exception:
        pass
    ctx.prefix_cache[prefix] = hasil
    return hasil

REPO_UMUM_PREFIX = ("10.5281/", "10.6084/", "10.31219/", "10.17605/", "10.13140/", "10.20944/", "10.21203/",
                    "10.48550/", "10.2139/", "10.31234/", "10.35542/", "10.31235/")
REPO_UMUM_NAMA = ("zenodo", "figshare", "researchgate", "ssrn", "arxiv", "research square", "preprints",
                  "osf preprints", "open science framework", "academia.edu", "scribd")

def repositori_umum(r):
    """Unggahan bebas (Zenodo, ResearchGate, preprint) tidak dihitung sebagai jurnal nasional/internasional."""
    if r["doi"].startswith(REPO_UMUM_PREFIX):
        return True
    nama = f"{r['sumber']} {r['penerbit']}".lower()
    return any(x in nama for x in REPO_UMUM_NAMA)

def tentukan_kategori(r):
    if repositori_umum(r):
        return None
    if r.get("negara") == "ID":
        return "Nasional"
    if indikasi_nasional(r) and not r.get("negara"):
        return "Nasional"
    if r.get("negara") or r["bahasa"] == "ms" or (
            (r["bahasa"] == "en" or tebak_bahasa(r["judul"]) == "en") and (r["sumber"] or r["penerbit"])):
        # repositori umum (Zenodo dsb.) bukan jurnal internasional, kecuali untuk skripsi/tesis
        if r.get("sumber_tipe") == "repository" and r["jenis"] != "dissertation":
            return None
        return "Internasional"
    return None


# ============================ analisis relevansi ============================
# ============================ kualitas: DOAJ, SINTA, predator ============================
# Turunan Beall's list / daftar hitam penerbit predator yang well-known.
# Frasa spesifik (bukan substring pendek) agar tidak salah tangkap, mis. "genomics".
PENERBIT_PREDATOR = (
    "omics international", "omics publishing", "omics group", "longdom", "waset",
    "world academy of science, engineering and technology",
    "scientific research publishing", "scirp", "academic journals", "academicjournals",
    "international organization of scientific research", "iosr journals",
    "blue eyes intelligence", "blueeyes", "global journals", "globaljournals",
    "international institute for science, technology and education", "iiste",
    "sciencedomain", "science domain international", "medwell journals", "ansinet",
    "asian network for scientific information", "thescipub", "science publications",
    "juniper publishers", "iris publishers", "gavin publishers", "allied academies",
    "scholink", "coalesce research", "oatext", "avens publishing", "herbert publications",
    "peertechz", "herald scholarly",
)

def terindikasi_predator(r):
    nama = f" {r.get('penerbit', '')} {r.get('sumber', '')} ".lower()
    return any(p in nama for p in PENERBIT_PREDATOR)

def _doaj_issn(issn):
    """True bila jurnal ber-ISSN ini terindeks DOAJ; None bila tak bisa dicek."""
    try:
        r = SESI.get(f"https://doaj.org/api/search/journals/issn:{issn}", params={"pageSize": 1}, timeout=15)
        if r.status_code == 200:
            return bool(r.json().get("total"))
        if r.status_code == 404:
            return False
    except Exception:
        pass
    return None

def cek_doaj(ctx, recs):
    perlu = list(dict.fromkeys(r.get("issn") for r in recs
                               if r.get("issn") and r.get("issn") not in ctx.doaj_cache))
    if perlu:
        with ThreadPoolExecutor(6) as ex:
            hasil = list(ex.map(_doaj_issn, perlu))
        for issn, h in zip(perlu, hasil):
            ctx.doaj_cache[issn] = h
    for r in recs:
        r["doaj"] = bool(ctx.doaj_cache.get(r.get("issn")))

def _sinta_nama(nama):
    """Peringkat akreditasi SINTA (S1–S6) bila jurnal ditemukan; best-effort, gagal = None."""
    for domain in ("https://sinta.kemdiktisaintek.go.id", "https://sinta.kemdikbud.go.id"):
        try:
            r = SESI.get(f"{domain}/journals", params={"q": nama}, timeout=12)
            if r.status_code != 200:
                continue
            teks = r.text
            posisi = teks.lower().find(nama.lower())
            if posisi < 0:
                continue
            m = re.search(r">\s*S([1-6])\s*<", teks[posisi:posisi + 1200])
            return f"S{m.group(1)}" if m else None
        except Exception:
            continue
    return None

def cek_sinta(ctx, recs):
    calon = [r for r in recs if r.get("sumber") and (
        r.get("negara") == "ID" or r.get("bahasa") == "id" or indikasi_nasional(r))]
    perlu = list(dict.fromkeys(r["sumber"] for r in calon if r["sumber"] not in ctx.sinta_cache))[:40]
    if perlu:
        with ThreadPoolExecutor(4) as ex:
            hasil = list(ex.map(_sinta_nama, perlu))
        for nama, h in zip(perlu, hasil):
            ctx.sinta_cache[nama] = h
    for r in recs:
        r["sinta"] = ctx.sinta_cache.get(r.get("sumber")) or ""

def cek_kualitas(ctx, recs):
    for r in recs:
        r.setdefault("doaj", False)
        r.setdefault("sinta", "")
    if not ctx.cek_indeks or not recs:
        return
    print("   🛡️ Memeriksa indeks DOAJ & akreditasi SINTA …")
    cek_doaj(ctx, recs)
    cek_sinta(ctx, recs)
    for r in recs:
        bonus = (4 if r["doaj"] else 0) + (4 if r["sinta"] else 0)
        if bonus:
            r["skor"] = min(100.0, round(r["skor"] + bonus, 1))
    n_doaj = sum(1 for r in recs if r["doaj"])
    n_sinta = sum(1 for r in recs if r["sinta"])
    print(f"      ✓ Terindeks DOAJ: {n_doaj} · Terakreditasi SINTA: {n_sinta} (bonus skor diterapkan)")


def analisis_relevansi(topik, recs):
    if not recs:
        return []
    kunci = list(dict.fromkeys(tokenisasi(topik))) or re.findall(r"[a-z0-9]+", _ascii(topik).lower())
    dok = [f"{r['judul']} {r['judul']} {r['abstrak']}" for r in recs]
    try:
        vec = TfidfVectorizer(tokenizer=tokenisasi, lowercase=False, token_pattern=None,
                              ngram_range=(1, 2), sublinear_tf=True)
        X = vec.fit_transform(dok + [topik])
        sim = cosine_similarity(X[-1], X[:-1]).ravel()
    except ValueError:
        sim = np.zeros(len(recs))
    sim_n = sim / sim.max() if sim.max() > 0 else sim

    urut = tokenisasi(topik)
    frasa = list(dict.fromkeys(f"{a} {b}" for a, b in zip(urut, urut[1:])))
    toks = [(tokenisasi(r["judul"]), tokenisasi(r["abstrak"])) for r in recs]
    n = len(recs)
    bobot = {}
    for k in kunci:  # kata yang lebih spesifik (jarang di kandidat) lebih menentukan
        df_k = sum(1 for lj, la in toks if cocok(k, set(lj)) or cocok(k, set(la)))
        bobot[k] = math.log((1 + n) / (1 + df_k)) + 1
    total_bobot = sum(bobot.values()) or 1

    cakupan, kata_saja = [], []
    for r, (lj, la) in zip(recs, toks):
        tj, ta = set(lj), set(la)
        nilai, ada = 0.0, []
        for k in kunci:
            if cocok(k, tj):
                nilai += bobot[k]; ada.append(k)
            elif cocok(k, ta):
                nilai += 0.6 * bobot[k]; ada.append(k)
        nk = nilai / total_bobot
        kata_saja.append(nk)
        r["kata_cocok"] = ada
        if frasa:
            gj, ga = " ".join(lj), " ".join(la)
            nf = sum(1.0 if f in gj else (0.6 if f in ga else 0) for f in frasa) / len(frasa)
            cakupan.append(0.75 * nk + 0.25 * nf)
        else:
            cakupan.append(nk)
    cakupan = np.array(cakupan)

    api = np.zeros(n)
    for asal in {r["asal"] for r in recs}:
        idx = [i for i, r in enumerate(recs) if r["asal"] == asal]
        mx = max(recs[i]["skor_api"] for i in idx) or 1
        for i in idx:
            api[i] = recs[i]["skor_api"] / mx
    sit = np.array([math.log1p(r["sitasi"] or 0) for r in recs])
    sit = sit / sit.max() if sit.max() > 0 else sit
    th = np.array([r["tahun"] or 0 for r in recs], dtype=float)
    ada_th = th[th > 0]
    if len(ada_th) and ada_th.max() > ada_th.min():
        baru = np.where(th > 0, (th - ada_th.min()) / (ada_th.max() - ada_th.min()), 0)
    else:
        baru = np.zeros(n)

    skor = (0.40 * sim_n + 0.30 * cakupan + 0.17 * api + 0.08 * sit + 0.05 * baru) * 100
    for i, r in enumerate(recs):
        r["skor"] = round(float(skor[i]), 1)
        r["kemiripan"] = float(sim[i])
        r["kata_saja"] = float(kata_saja[i])
    return kunci

AMBANG = [  # makin ke bawah makin longgar (dipakai bila kuota belum terpenuhi)
    lambda r: r["kata_saja"] >= 0.5 or r["kemiripan"] >= 0.20,
    lambda r: r["kata_saja"] >= 0.34 or r["kemiripan"] >= 0.12,
    lambda r: r["kata_saja"] > 0 or r["kemiripan"] >= 0.03,
]

def label_relevansi(s):
    return "🔥 Sangat relevan" if s >= 65 else ("✅ Relevan" if s >= 45 else "🟡 Pendukung")


# ============================ open access & unduh PDF ============================
def lengkapi(rec, ctx):
    """Lengkapi tautan PDF legal + negara sumber (sekali per referensi)."""
    if rec["sudah_dilengkapi"]:
        return rec
    rec["sudah_dilengkapi"] = True
    if rec["doi"] and rec["asal"] == "Crossref":
        try:
            p = {"select": "id,primary_location,best_oa_location,locations,open_access,language,abstract_inverted_index"}
            r = SESI.get(f"https://api.openalex.org/works/doi:{rec['doi']}", params=p, timeout=25)
            if r.status_code == 200:
                o = rapikan_openalex(r.json())
                rec["pdf_urls"] += o["pdf_urls"]
                rec["halaman_oa"] += o["halaman_oa"]
                rec["halaman"] = rec["halaman"] or o["halaman"]
                rec["bahasa"] = o["bahasa"] or rec["bahasa"]
                rec["abstrak"] = rec["abstrak"] or o["abstrak"]
                rec["is_oa"] = rec["is_oa"] or o["is_oa"]
                rec["sumber_id"] = rec["sumber_id"] or o["sumber_id"]
                rec["sumber_tipe"] = rec["sumber_tipe"] or o["sumber_tipe"]
                rec["sumber"] = rec["sumber"] or o["sumber"]
        except Exception:
            pass
    if rec["sumber_id"] and rec["negara"] is None:
        if rec["sumber_id"] in ctx.negara_cache:
            rec["negara"] = ctx.negara_cache[rec["sumber_id"]] or None
        else:
            try:
                r = SESI.get(f"https://api.openalex.org/sources/{rec['sumber_id']}",
                             params={"select": "id,country_code"}, timeout=20)
                if r.status_code == 200:
                    kode = (r.json().get("country_code") or "").upper()
                    ctx.negara_cache[rec["sumber_id"]] = kode
                    rec["negara"] = kode or None
            except Exception:
                pass
    if rec["negara"] is None and rec["doi"] and not indikasi_nasional(rec):
        rec["negara"] = negara_dari_prefix(ctx, rec["doi"])
    if rec["doi"] and ctx.email:
        try:
            r = SESI.get(f"https://api.unpaywall.org/v2/{rec['doi']}", params={"email": ctx.email}, timeout=25)
            if r.status_code == 200:
                for loc in r.json().get("oa_locations") or []:
                    if loc.get("url_for_pdf"):
                        rec["pdf_urls"].append(loc["url_for_pdf"])
                    if loc.get("url_for_landing_page"):
                        rec["halaman_oa"].append(loc["url_for_landing_page"])
                    rec["is_oa"] = True
        except Exception:
            pass
    rec["pdf_urls"] = list(dict.fromkeys(rec["pdf_urls"]))
    rec["halaman_oa"] = list(dict.fromkeys(rec["halaman_oa"]))
    return rec

def _varian_url(u):
    m = re.search(r"/article/view/(\d+)/(\d+)", u)  # trik jurnal OJS: halaman baca -> unduh
    if m:
        return [u.replace(m.group(0), f"/article/download/{m.group(1)}/{m.group(2)}"), u]
    return [u]

def _ambil(url, batas_detik=45):
    t0 = time.time()
    with SESI.get(url, timeout=(8, 20), stream=True, allow_redirects=True,
                  headers={"Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8"}) as r:
        if r.status_code != 200:
            return None, url
        jenis = (r.headers.get("Content-Type") or "").lower()
        if jenis and not any(x in jenis for x in ("pdf", "html", "octet-stream", "download", "force")):
            return None, url
        buf = bytearray()
        for chunk in r.iter_content(65536):
            buf.extend(chunk)
            if len(buf) > MAKS_BYTE_PDF or time.time() - t0 > batas_detik:
                return None, url
            if len(buf) >= 2048 and b"%PDF-" not in buf[:1024] and "html" not in jenis and b"<" not in buf[:1024]:
                return None, url
        return bytes(buf), r.url

def _pdf_dari_meta(isi, base):
    teks = isi[:600000].decode("utf-8", "ignore")
    pola = [r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]*content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*name=["\']citation_pdf_url']
    hasil = []
    for p in pola:
        hasil += [requests.compat.urljoin(base, html.unescape(u)) for u in re.findall(p, teks, re.I)]
    return hasil

def punya_jalur_pdf(r, ctx):
    return bool(r["pdf_urls"] or r["halaman_oa"] or r.get("_pdf_bytes")
                or (ctx.pakai_dork and ctx.dork_kuota > 0 and len(ctx.mesin_mati) < 2) or (r["asal"] == "Crossref" and not r["sudah_dilengkapi"])
                or (r["doi"] and ctx.email and not r["sudah_dilengkapi"]))

def unduh_pdf(rec, folder):
    if rec.get("_pdf_bytes"):
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, rec["nama_file"]), "wb") as f:
            f.write(rec.pop("_pdf_bytes"))
        rec["sumber_pdf"] = "Google Dorks"
        return rec["nama_file"]
    antrian = []
    for u in rec["pdf_urls"]:
        antrian += _varian_url(u)
    antrian += rec["halaman_oa"][:3]
    dicoba, percobaan, t0 = set(), 0, time.time()
    while antrian and percobaan < 8 and time.time() - t0 < 90:
        u = antrian.pop(0)
        if not u or u in dicoba:
            continue
        dicoba.add(u)
        percobaan += 1
        try:
            isi, akhir = _ambil(u)
        except Exception:
            continue
        if not isi:
            continue
        if b"%PDF-" in isi[:1024]:
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, rec["nama_file"]), "wb") as f:
                f.write(isi)
            rec["sumber_pdf"] = "Open Access"
            return rec["nama_file"]
        for m in _pdf_dari_meta(isi, akhir):
            if m not in dicoba:
                antrian.insert(0, m)
    return None


# ============================ Google Dorks (filetype:pdf) ============================
# Operator dork (filetype:pdf, site:, -site:) dijalankan lewat DuckDuckGo & Brave, karena
# Google Search sekarang mewajibkan JavaScript untuk permintaan otomatis dari Colab.
UA_BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/126.0 Safari/537.36",
              "Accept-Language": "id-ID,id;q=0.9,en;q=0.8", "Accept": "text/html,application/xhtml+xml"}
SITUS_BAJAKAN = ("sci-hub", "scihub", "libgen", "library.lol", "z-lib", "zlibrary", "singlelogin", "annas-archive",
                 "dokumen.pub", "pdfcoffee", "epdf.pub", "vdoc.pub", "ebin.pub", "doku.pub", "idoc.pub", "kupdf",
                 "documents.pub", "dokumen.tips", "fdocuments", "pdfdrive", "123dok", "studocu", "scribd",
                 "coursehero", "docplayer", "pdfroom", "pdfslide", "vdocuments", "pdfcookie", "dokumen.site")

def _mirip_pdf(u):
    p = up.urlparse(u).path.lower()
    return p.endswith(".pdf") or "/download/" in p or "/bitstream/" in p or "pdf" in p.rsplit("/", 1)[-1]

def situs_bajakan(u):
    host = up.urlparse(u).netloc.lower()
    return any(x in host for x in SITUS_BAJAKAN)

def dork_cari(ctx, q, maks=15):
    """Jalankan satu kueri dork, kembalikan daftar URL PDF."""
    if ctx.dork_kuota <= 0 or len(ctx.mesin_mati) >= 2:
        return []
    ctx.dork_kuota -= 1
    hasil = []
    for mesin in ("duckduckgo", "brave"):
        if mesin in ctx.mesin_mati:
            continue
        try:
            if mesin == "duckduckgo":
                r = requests.post("https://lite.duckduckgo.com/lite/", data={"q": q}, headers=UA_BROWSER, timeout=15)
                ls = [up.unquote(x) for x in re.findall(r'uddg=([^&"\']+)', r.text)]
                ls += re.findall(r'<a rel="nofollow" href="(https?://[^"]+)"', r.text)
            else:
                r = requests.get("https://search.brave.com/search", params={"q": q, "source": "web"},
                                 headers=UA_BROWSER, timeout=15)
                ls = re.findall(r'href="(https?://[^"]+)"', r.text)
            if r.status_code != 200:
                ctx.mesin_mati.add(mesin)
                continue
        except Exception:
            continue
        for l in ls:
            l = html.unescape(l)
            host = up.urlparse(l).netloc.lower()
            if not host or any(x in host for x in ("duckduckgo", "brave.com", "bing.com", "google.")):
                continue
            if _mirip_pdf(l) and not situs_bajakan(l) and l not in hasil:
                hasil.append(l)
        if len(hasil) >= 3:
            break
    time.sleep(1.0)
    if len(ctx.mesin_mati) >= 2 and not ctx.dork_diumumkan:
        ctx.dork_diumumkan = True
        print("      ⚠️ Mesin dorks sedang membatasi koneksi Colab ini — dorks dilewati, sumber lain tetap jalan.")
    return hasil[:maks]

def teks_pdf(isi, halaman=2):
    if PdfReader is None:
        return "", ""
    try:
        rd = PdfReader(io.BytesIO(isi))
        judul_meta = ""
        try:
            judul_meta = (rd.metadata.title if rd.metadata else "") or ""
        except Exception:
            pass
        teks = " \n".join((rd.pages[i].extract_text() or "") for i in range(min(halaman, len(rd.pages))))
        return teks, str(judul_meta)
    except Exception:
        return "", ""

def dalam_rentang(th, ctx):
    if not (ctx.tahun_dari or ctx.tahun_sampai):
        return True
    if not th:
        return False
    return (not ctx.tahun_dari or th >= ctx.tahun_dari) and (not ctx.tahun_sampai or th <= ctx.tahun_sampai)

def rekam_dari_pdf(url, isi, ctx):
    """Ubah PDF temuan dorks jadi referensi lengkap (cari DOI di dalam PDF -> metadata resmi)."""
    teks, judul_meta = teks_pdf(isi)
    if len(teks) < 200:
        return None
    m = re.search(r"\b10\.\d{4,9}/[^\s\"'<>]+", teks)
    doi = m.group(0).rstrip(".,;:)]}").lower() if m else ""
    rec = None
    if doi:
        try:
            r = SESI.get(f"https://api.openalex.org/works/doi:{doi}",
                         params={"select": FIELD_OPENALEX.replace(",relevance_score", "")}, timeout=20)
            if r.status_code == 200:
                rec = rapikan_openalex(r.json())
        except Exception:
            pass
        if rec is None:
            try:
                r = SESI.get(f"https://api.crossref.org/works/{doi}", timeout=20)
                if r.status_code == 200:
                    rec = rapikan_crossref(r.json()["message"])
            except Exception:
                pass
    if rec is None:
        if ctx.wajib_doi:
            return None
        judul = bersih(judul_meta) if len(bersih(judul_meta).split()) >= 4 else ""
        if not judul:
            baris = [bersih(b) for b in teks.split("\n")[:25]]
            calon = [b for b in baris if 5 <= len(b.split()) <= 30
                     and not re.search(r"(issn|vol\.|volume|doi|http|©|e-mail|email)", b, re.I)]
            judul = max(calon, key=len) if calon else ""
        if len(judul) < 15:
            return None
        th = re.findall(r"\b(19[89]\d|20[0-3]\d)\b", teks[:3000])
        dom = up.urlparse(url).netloc
        jenis = "dissertation" if re.search(r"\b(skripsi|tesis|thesis|disertasi|dissertation)\b",
                                            teks[:4000], re.I) else "article"
        rec = dict(uid="dork:" + kunci_judul(judul), id="dork-" + slug(dom, 25), doi="", judul=judul, penulis=[],
                   tahun=int(th[0]) if th else None, jenis=jenis, sumber=dom, sumber_id="", sumber_tipe="",
                   issn="", penerbit="", bahasa=tebak_bahasa(teks[:3000]), negara=None, sitasi=0,
                   abstrak=bersih(teks[:1500]), pdf_urls=[], halaman_oa=[], halaman=url, url=url, skor_api=0.0,
                   asal="Google Dorks", is_oa=True, sudah_dilengkapi=False)
    rec["asal"] = "Google Dorks"
    rec["halaman"] = rec["halaman"] or url
    rec["pdf_urls"].insert(0, url)
    rec["_pdf_bytes"] = isi
    return rec

def dork_pdf_untuk(rec, ctx, folder):
    """Referensi sudah jelas tapi PDF belum dapat: cari judulnya dengan dork filetype:pdf."""
    kata = rec["judul"].split()[:14]
    if len(kata) < 3:
        return None
    urls = dork_cari(ctx, f'"{" ".join(kata)}" filetype:pdf', maks=5)
    kunci = set(tokenisasi(rec["judul"]))
    for u in urls[:4]:
        try:
            isi, _ = _ambil(u, 40)
        except Exception:
            continue
        if not isi or b"%PDF-" not in isi[:1024]:
            continue
        teks, judul_meta = teks_pdf(isi)
        token = set(tokenisasi(teks + " " + judul_meta))
        doi_cocok = rec["doi"] and rec["doi"] in teks.lower().replace(" ", "")
        rasio = len([k for k in kunci if k in token]) / max(1, len(kunci))
        if doi_cocok or rasio >= 0.7:  # pastikan PDF-nya memang artikel yang sama
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, rec["nama_file"]), "wb") as f:
                f.write(isi)
            rec["sumber_pdf"] = "Google Dorks"
            return rec["nama_file"]
    return None


# ============================ mesin kuota (inti v2) ============================
def isi_kuota(kat, pool, target, terpilih, ambang, ctx):
    """Ambil kandidat terbaik sampai kuota kategori PAS. Tidak pernah melebihi target."""
    folder_kat = os.path.join(ctx.folder_pdf, kat)
    lain = "Internasional" if kat == "Nasional" else "Nasional"
    urut = sorted(pool.values(), key=lambda r: -r.get("skor", 0))
    lewati = ctx.ditolak[kat] | (ctx.gagal_pdf[kat] if ctx.wajib_pdf else set())
    kandidat = [r for r in urut if r["uid"] not in lewati and r["uid"] not in ctx.dipilih_uid
                and AMBANG[ambang](r) and (not ctx.wajib_pdf or punya_jalur_pdf(r, ctx))]
    while len(terpilih) < target and kandidat:
        kurang = target - len(terpilih)
        batch, kandidat = kandidat[:max(kurang * 2, 8)], kandidat[max(kurang * 2, 8):]
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(lambda r: lengkapi(r, ctx), batch))
        for r in batch:
            ctx.stat["dinilai"][kat].add(r["uid"])
        valid = []
        for r in batch:
            r["kategori"] = tentukan_kategori(r)
            if r["kategori"] == kat and r["uid"] not in ctx.dipilih_uid:
                valid.append(r)
            else:
                ctx.ditolak[kat].add(r["uid"])
                if r["kategori"] == lain:
                    ctx.pindahan[lain].append(r)  # salah kamar -> titipkan ke kategori lain
        if not valid:
            continue
        if ctx.wajib_pdf:
            for r in valid:
                if not r.get("nama_file"):
                    r["nama_file"] = ctx.nama_unik(nama_file_pdf(r))
            with ThreadPoolExecutor(8) as ex:
                hasil = list(ex.map(lambda r: unduh_pdf(r, folder_kat) if punya_jalur_pdf(r, ctx) else None, valid))
            for r, h in zip(valid, hasil):
                r["pdf"] = h
            if ctx.pakai_dork:  # PDF belum dapat -> cari judulnya dengan Google Dorks
                jumlah_ok = sum(1 for r in valid if r["pdf"])
                for r in valid:
                    if jumlah_ok >= kurang or ctx.dork_kuota <= 0:
                        break
                    if not r["pdf"]:
                        r["pdf"] = dork_pdf_untuk(r, ctx, folder_kat)
                        jumlah_ok += bool(r["pdf"])
            for r in valid:
                if not r["pdf"]:
                    ctx.gagal_pdf[kat].add(r["uid"])
            sukses = [r for r in valid if r["pdf"]]
            ambil, lebih = sukses[:kurang], sukses[kurang:]
            for r in lebih:  # jangan lebih: hapus PDF cadangan
                try:
                    os.remove(os.path.join(folder_kat, r["pdf"]))
                except OSError:
                    pass
                r["pdf"] = None
        else:
            ambil = valid[:kurang]
            for r in ambil:
                r.setdefault("pdf", None)
        for r in ambil:
            terpilih.append(r)
            ctx.dipilih_uid.add(r["uid"])
        print(f"      … {IKON_KAT[kat]} {kat}: {len(terpilih)}/{target}")

def tambah_ke_pool(pool, recs, ctx=None):
    baru = 0
    kat = getattr(ctx, "kat_kini", "") if ctx is not None else ""
    stat = getattr(ctx, "stat", None) if ctx is not None else None
    catat = bool(kat) and stat is not None
    judul_ada = {kunci_judul(r["judul"]) for r in pool.values()}
    for r in recs:
        if catat:
            stat["ditarik"][kat] += 1
        if len(r["judul"]) < 8:
            continue
        if r["uid"] in pool:
            if catat:
                stat["duplikat"][kat] += 1
            continue
        if ctx is not None and ctx.saring_predator and terindikasi_predator(r):
            ctx.predator_disaring += 1
            if catat:
                stat["predator"][kat] += 1
            continue
        kj = kunci_judul(r["judul"])
        if kj in judul_ada:
            if catat:
                stat["duplikat"][kat] += 1
            continue
        judul_ada.add(kj)
        pool[r["uid"]] = r
        baru += 1
    return baru

def cari_kategori(kat, target, ctx):
    """Cari sampai kuota PAS dengan perluasan bertahap."""
    terpilih, pool = [], {}
    if target <= 0:
        return terpilih, pool, []
    ctx.kat_kini = kat
    topik = ctx.topik_id if kat == "Nasional" else ctx.topik_en
    topik_skor = ctx.topik_id if kat == "Nasional" else ctx.topik_en_skor
    set_filter = ([["primary_location.source.country_code:ID"], ["language:id"]] if kat == "Nasional"
                  else [["primary_location.source.country_code:!ID", "language:en"]])
    kunci = tokenisasi(topik)

    def ambil_openalex(mode, lt=False, ld=False, inti=None, maks=200):
        hasil = []
        for fs in set_filter:
            bagian = openalex_tarik(ctx, topik, mode, filter_dasar(ctx, lt, ld) + fs, maks, inti)
            if "primary_location.source.country_code:ID" in fs:  # dijamin jurnal Indonesia
                for r in bagian:
                    r["negara"] = "ID"
            hasil += bagian
        isi_negara(ctx, hasil)
        return hasil

    def ambil_crossref(lt=False, offset=0):
        hasil = crossref_tarik(ctx, topik, 200, offset, lt)
        return [r for r in hasil if tentukan_kategori(r) in (kat, None)]

    def ambil_kata_dikurangi():
        if len(kunci) < 3:
            return []
        n = max(1, len(pool))
        frek = {k: sum(1 for r in pool.values() if cocok(k, set(tokenisasi(r["judul"] + " " + r["abstrak"]))))
                for k in dict.fromkeys(kunci)}
        hasil = []
        for buang in sorted(frek, key=lambda k: -frek[k] / n)[:2]:  # buang kata paling umum dulu
            sisa = " ".join(k for k in dict.fromkeys(kunci) if k != buang)
            hasil += ambil_openalex("presisi", inti=sisa, maks=100)
        return hasil

    def ambil_dork():
        inti = " ".join(dict.fromkeys(tokenisasi(topik)))
        if kat == "Nasional":
            qs = [f"{topik} filetype:pdf site:ac.id", f"{inti} filetype:pdf site:id"]
            if ctx.jenis.startswith("Skripsi"):
                qs.insert(0, f"skripsi {inti} filetype:pdf site:ac.id")
        else:
            qs = [f"{topik} filetype:pdf -site:id", f"{inti} filetype:pdf"]
        urls = []
        for q in qs:
            urls += dork_cari(ctx, q)
        urls = list(dict.fromkeys(urls))[:20]

        def proses(u):
            try:
                isi, _ = _ambil(u, 40)
                if isi and b"%PDF-" in isi[:1024]:
                    return rekam_dari_pdf(u, isi, ctx)
            except Exception:
                pass
            return None
        with ThreadPoolExecutor(6) as ex:
            recs = [r for r in ex.map(proses, urls) if r]
        boleh = set(JENIS_OPENALEX.get(ctx.jenis, JENIS_OPENALEX["Semua"]).split("|"))
        recs = [r for r in recs if r["jenis"] in boleh and dalam_rentang(r["tahun"], ctx)]
        isi_negara(ctx, recs)
        print(f"      🔎 Google Dorks: {len(urls)} PDF ditemukan, {len(recs)} lolos cek metadata")
        return recs

    tahapan = [  # (nama, fungsi pencarian, tingkat ambang, catatan jika dipakai)
        ("Pencarian presisi (semua kata kunci di judul/abstrak)", lambda: ambil_openalex("presisi"), 0, None),
        ("Memperluas pencarian (judul, abstrak & teks lengkap)", lambda: ambil_openalex("luas", maks=300), 0, None),
        ("Menambah sumber Crossref", lambda: ambil_crossref(), 0, None),
        *([("Snowballing (jejaring sitasi paper unggulan)", lambda: snowball_tarik(ctx, pool), 0, None)]
          if ctx.snowball else []),
        *([("Google Dorks (filetype:pdf)", ambil_dork, 0, None)] if ctx.pakai_dork else []),
        ("Variasi kata kunci", ambil_kata_dikurangi, 1, None),
        ("Menambah halaman Crossref", lambda: ambil_crossref(offset=200), 1, None),
    ]
    if ctx.longgarkan and (ctx.tahun_dari or ctx.tahun_sampai):
        tahapan.append(("Melonggarkan rentang tahun", lambda: ambil_openalex("luas", lt=True, maks=300)
                        + ambil_crossref(lt=True), 1, "di luar rentang tahun (rentang dilonggarkan)"))
    if ctx.longgarkan and ctx.wajib_doi:
        tahapan.append(("Mengizinkan referensi tanpa DOI", lambda: ambil_openalex(
            "luas", lt=ctx.longgarkan, ld=True, maks=300), 1, "tanpa DOI"))
    tahapan.append(("Menurunkan ambang relevansi", lambda: [], 2, "berelevansi rendah (pendukung)"))

    if ctx.pindahan[kat]:  # kandidat 'salah kamar' dari kategori lain (sudah dihitung saat ditarik)
        simpan_kat, ctx.kat_kini = ctx.kat_kini, ""
        tambah_ke_pool(pool, ctx.pindahan[kat], ctx)
        ctx.kat_kini = simpan_kat
        analisis_relevansi(topik_skor, list(pool.values()))
        isi_kuota(kat, pool, target, terpilih, 0, ctx)

    catatan = []
    for nama, fungsi, ambang, label in tahapan:
        if len(terpilih) >= target:
            break
        print(f"   ↳ {IKON_KAT[kat]} {nama} …")
        sebelum = len(terpilih)
        baru = tambah_ke_pool(pool, fungsi(), ctx)
        if baru or ambang:
            analisis_relevansi(topik_skor, list(pool.values()))
        isi_kuota(kat, pool, target, terpilih, ambang, ctx)
        if label and len(terpilih) > sebelum:
            catatan.append(f"{len(terpilih) - sebelum} referensi {kat.lower()} {label}")

    if len(terpilih) < target and ctx.wajib_pdf and ctx.longgarkan:
        print(f"   ↳ {IKON_KAT[kat]} PDF legal tidak cukup → melengkapi dengan referensi tanpa PDF agar jumlah pas …")
        ctx.wajib_pdf, simpan = False, ctx.wajib_pdf
        sebelum = len(terpilih)
        isi_kuota(kat, pool, target, terpilih, 2, ctx)
        ctx.wajib_pdf = simpan
        if len(terpilih) > sebelum:
            catatan.append(f"{len(terpilih) - sebelum} referensi {kat.lower()} tanpa PDF (tidak ada versi legal gratis)")
    terpilih = terpilih[:target]  # pengaman: tidak pernah lebih
    return terpilih, pool, catatan


# ============================ ekspor (Mendeley dkk.) ============================
RIS_TY = {"article": "JOUR", "review": "JOUR", "preprint": "JOUR", "book": "BOOK",
          "book-chapter": "CHAP", "dissertation": "THES", "report": "RPRT"}

def _nama_ris(n):
    n = n.strip()
    if "," in n:
        return n
    b = n.split()
    return n if len(b) < 2 else f"{b[-1]}, {' '.join(b[:-1])}"

def buat_ris(rows, topik):
    keluar = []
    for r in rows:
        L = [f"TY  - {RIS_TY.get(r['jenis'], 'GEN')}"]
        def tambah(tag, val):
            val = re.sub(r"\s+", " ", str(val or "")).strip()
            if val:
                L.append(f"{tag}  - {val}")
        tambah("TI", r["judul"])
        for p in r["penulis"]:
            tambah("AU", _nama_ris(p))
        tambah("PY", r["tahun"])
        if r["jenis"] == "dissertation":
            tambah("PB", r["sumber"] or r["penerbit"])
        else:
            tambah("T2", r["sumber"])
            tambah("PB", r["penerbit"])
        tambah("DO", r["doi"])
        tambah("UR", r["url"])
        tambah("LA", r["bahasa"])
        tambah("AB", r["abstrak"])
        tambah("KW", r["kategori"])
        tambah("KW", "Referensia")
        tambah("N1", f"Referensia - {r['kategori']} - skor relevansi {r['skor']}/100 untuk topik: {topik}")
        if r.get("pdf"):
            tambah("L1", f"PDF/{r['kategori']}/{r['pdf']}")
        L.append("ER  - ")
        keluar.append("\n".join(L))
    return "\n\n".join(keluar) + "\n"

BIB_TY = {"article": "article", "review": "article", "preprint": "misc", "book": "book",
          "book-chapter": "incollection", "dissertation": "thesis", "report": "techreport"}

def _bib(s):
    s = str(s or "").replace("{", "(").replace("}", ")")
    return s.replace("&", r"\&").replace("%", r"\%").replace("#", r"\#")

def buat_bib(rows):
    keluar, kunci_ada = [], set()
    for r in rows:
        nama1 = slug(r["penulis"][0].split()[-1] if r["penulis"] else "anon", 20).lower()
        kata1 = (tokenisasi(r["judul"]) or ["ref"])[0][:15]
        k = f"{nama1}{r['tahun'] or ''}{kata1}"
        while k in kunci_ada:
            k += "x"
        kunci_ada.add(k)
        f = {"title": r["judul"], "author": " and ".join(r["penulis"]), "year": r["tahun"],
             ("booktitle" if r["jenis"] == "book-chapter" else "journal"):
                 r["sumber"] if r["jenis"] not in ("book", "dissertation") else "",
             ("school" if r["jenis"] == "dissertation" else "publisher"):
                 r["penerbit"] or (r["sumber"] if r["jenis"] == "dissertation" else ""),
             "doi": r["doi"], "url": r["url"], "keywords": f"{r['kategori']}, Referensia",
             "abstract": r["abstrak"], "file": f"PDF/{r['kategori']}/{r['pdf']}" if r.get("pdf") else ""}
        isi = ",\n".join(f"  {a} = {{{_bib(b)}}}" for a, b in f.items() if b)
        keluar.append(f"@{BIB_TY.get(r['jenis'], 'misc')}{{{k},\n{isi}\n}}")
    return "\n\n".join(keluar) + "\n"


# ============================ tampilan ============================
FONT = "font-family:system-ui,Segoe UI,Roboto,sans-serif"

# ============================ analisis isi: ringkasan, metode, sitasi ============================
def ringkas_abstrak(abstrak, kunci, maks=3):
    """Ringkasan extractive: kalimat paling relevan dengan topik, urutan asli dipertahankan."""
    if not abstrak:
        return ""
    kalimat = [k.strip() for k in re.split(r"(?<=[.!?])\s+", abstrak) if len(k.strip()) > 20]
    if len(kalimat) <= maks:
        return " ".join(kalimat)
    ks = list(dict.fromkeys(kunci))
    skor = []
    for i, k in enumerate(kalimat):
        tok = set(tokenisasi(k))
        cov = sum(1 for a in ks if cocok(a, tok)) / max(1, len(ks))
        cue = 0.15 if re.search(r"\b(hasil|result\w*|menunjukkan|show\w*|findings|conclud\w*|simpulan)", k, re.I) else 0
        skor.append((cov + cue + (0.1 if i == 0 else 0), i))
    pilih = sorted(sorted(skor, reverse=True)[:maks], key=lambda x: x[1])
    return " ".join(kalimat[i] for _, i in pilih)

def hasil_utama(abstrak):
    """Satu kalimat temuan/hasil paling kuat dari abstrak (untuk matriks literatur)."""
    if not abstrak:
        return ""
    kalimat = [k.strip() for k in re.split(r"(?<=[.!?])\s+", abstrak) if len(k.strip()) > 20]
    terbaik, skor_ter = "", 0
    for k in kalimat:
        s = 0
        if re.search(r"\b(hasil|result\w*|menunjukkan|show\w*|findings|terbukti|signifikan|significant|"
                     r"conclud\w*|simpulan|meningkat|menurunkan|berpengaruh|efektif|effective)", k, re.I):
            s += 1
        if re.search(r"\b(hasil|result\w*|findings|simpulan|conclusion\w*)", k, re.I):
            s += 1
        if s > skor_ter:
            terbaik, skor_ter = k, s
    return terbaik

def lengkapi_abstrak_s2(rows):
    """Lengkapi abstrak kosong lewat Semantic Scholar (best-effort, tanpa API key)."""
    kurang = [r for r in rows if not (r.get("abstrak") or "").strip() and r.get("doi")]
    for mulai in range(0, len(kurang), 50):
        bagian = kurang[mulai:mulai + 50]
        try:
            r = SESI.post("https://api.semanticscholar.org/graph/v1/paper/batch",
                          params={"fields": "abstract"},
                          json={"ids": [f"DOI:{x['doi']}" for x in bagian]}, timeout=30)
            if r.status_code != 200:
                break
            for rec, data in zip(bagian, r.json() or []):
                if data and data.get("abstract"):
                    rec["abstrak"] = bersih(data["abstract"])
        except Exception:
            break
    return sum(1 for r in kurang if (r.get("abstrak") or "").strip())


def ekstrak_metode(abstrak, judul=""):
    """Deteksi heuristik pendekatan/desain/sampel/analisis/instrumen dari abstrak + judul (ID + EN)."""
    kosong = {"pendekatan": "", "desain": "", "sampel": "", "analisis": [], "instrumen": []}
    t = f"{judul or ''} {abstrak or ''}".lower()
    if not t.strip():
        return kosong
    pendekatan = []
    if re.search(r"kuantitatif|quantitative", t):
        pendekatan.append("Kuantitatif")
    if re.search(r"kualitatif|qualitative", t):
        pendekatan.append("Kualitatif")
    if re.search(r"mixed[- ]method|metode campuran", t):
        pendekatan.append("Mixed method")
    if re.search(r"literature review|systematic review|tinjauan (pustaka|literatur)|meta[- ]analys|scoping review", t):
        pendekatan.append("Review literatur")
    desain = []
    for label, pola in [
        ("Survei", r"surve[iy]|kuesioner|questionnaire"),
        ("Eksperimen", r"experiment|eksperimen|randomized|\brct\b|pretest|posttest|quasi"),
        ("Studi kasus", r"case study|studi kasus"),
        ("Korelasional", r"correlat|korelas"),
        ("PTK", r"action research|penelitian tindakan"),
        ("Fenomenologi", r"phenomenolog|fenomenolog"),
        ("Etnografi", r"ethnograph|etnograf"),
        ("R&D", r"research and development|penelitian pengembangan"),
        ("Pengembangan sistem", r"pengembangan (sistem|aplikasi|media|website|situs|perangkat lunak)|"
                                r"perancangan (sistem|aplikasi|website)|waterfall|prototype|sdlc"),
        ("Data mining/prediktif", r"data mining|machine learning|deep learning|"
                                  r"prediksi|prediction|peramalan|forecast|klasifikasi|classification"),
    ]:
        if re.search(pola, t):
            desain.append(label)
    s = re.search(r"\bn\s*=\s*(\d+)", t) or re.search(
        r"(\d+)\s+(?:responden|respondents|participants|students|mahasiswa|siswa|subjects|samples|"
        r"pasien|pelanggan|konsumen|transaksi|data|records|items)\b", t) or re.search(
        r"data\s*(?:sebanyak|berjumlah)\s*(\d+)", t)
    analisis = []
    for label, pola in [
        ("Regresi", r"regress|regresi"),
        ("SEM", r"\bsem\b|structural equation"),
        ("PLS", r"\bpls\b|smartpls"),
        ("ANOVA", r"\banova\b|\bancova\b"),
        ("Uji t", r"\bt[- ]test\b|\buji[- ]t\b"),
        ("Chi-square", r"chi[- ]square|khi kuadrat"),
        ("Korelasi", r"pearson|spearman|correlation analysis|analisis korelasi"),
        ("Analisis tematik", r"thematic|tematik"),
        ("Analisis konten", r"content analysis|analisis (isi|konten)"),
        ("Grounded theory", r"grounded theory"),
        ("Miles & Huberman", r"huberman|reduksi data|data reduction"),
        ("Naive Bayes", r"naive\s*bayes"),
        ("Random Forest", r"random\s*forest"),
        ("Regresi linear", r"regresi\s*(linear|berganda|sederhana)|linear regression|multiple regression"),
        ("KNN", r"k-?nearest\s*neighbou?r|\bknn\b|k-nn"),
        ("SVM", r"support\s*vector\s*machine|\bsvm\b"),
        ("Decision tree", r"decision\s*tree|\bcart\b|c4\.5|c5\.0"),
        ("K-Means", r"k-?means"),
        ("ARIMA/VARIMA", r"\bvarima\b|\barima\b"),
        ("Exponential smoothing", r"exponential\s*smoothing|pemulusan eksponensial"),
        ("Trend moment", r"trend\s*moment"),
        ("FP-Growth", r"frequent\s*pattern\s*growth|fp-?growth"),
        ("Apriori", r"apriori|association\s*rule|aturan\s*asosiasi"),
        ("LSTM", r"\blstm\b|long\s*short[- ]term\s*memory"),
        ("CNN", r"convolutional|\bcnn\b"),
        ("Jaringan saraf", r"neural\s*network|jaringan\s*saraf"),
        ("SAW/TOPSIS/MOORA/AHP", r"\bsaw\b|topsis|moora|\bahp\b|weighted (product|sum)"),
        ("Akurasi/confusion matrix", r"confusion matrix|akurasi|accuracy|mape|\brmse\b"),
    ]:
        if re.search(pola, t):
            analisis.append(label)
    instrumen = []
    for label, pola in [
        ("Dataset", r"dataset|data\s*(sekunder|historis|histori|penjualan|transaksi)"),
        ("Kuesioner", r"kuesioner|questionnaire|angket"),
        ("Wawancara", r"wawancara|interview"),
        ("Observasi", r"observasi|observation"),
        ("Tes", r"\btests?\b|\btes\b|pretest|posttest"),
        ("Dokumentasi", r"dokumentasi|documentation"),
    ]:
        if re.search(pola, t):
            instrumen.append(label)
    return {"pendekatan": " + ".join(dict.fromkeys(pendekatan)), "desain": ", ".join(desain[:3]),
            "sampel": f"n = {s.group(1)}" if s else "", "analisis": analisis[:5], "instrumen": instrumen[:4]}

def teks_metode(m):
    bagian = [m.get("pendekatan"), m.get("desain"), m.get("sampel"),
              ", ".join(m.get("analisis") or []), ", ".join(m.get("instrumen") or [])]
    return " · ".join(b for b in bagian if b) or "-"

def _pisah_nama(nama):
    nama = bersih(nama)
    if "," in nama:
        fam, rest = nama.split(",", 1)
        return fam.strip(), rest.strip().split()
    p = nama.split()
    if len(p) == 1:
        return p[0], []
    return p[-1], p[:-1]

def _inisial(parts):
    return " ".join(f"{w[0].upper()}." for w in parts if w and w[0].isalpha())

def nama_apa(nama):
    fam, gv = _pisah_nama(nama)
    ini = _inisial(gv)
    return f"{fam}, {ini}" if ini else fam

def nama_ieee(nama):
    fam, gv = _pisah_nama(nama)
    ini = _inisial(gv)
    return f"{ini} {fam}" if ini else fam

def buat_apa(r):
    ps = r.get("penulis") or []
    if not ps:
        penulis = "(Penulis tidak diketahui)"
    elif len(ps) > 20:
        penulis = ", ".join(nama_apa(p) for p in ps[:19]) + ", … " + nama_apa(ps[-1])
    elif len(ps) == 1:
        penulis = nama_apa(ps[0])
    else:
        penulis = ", ".join(nama_apa(p) for p in ps[:-1]) + ", & " + nama_apa(ps[-1])
    tahun = r.get("tahun") or "t.t."
    judul = (r.get("judul") or "").rstrip(".")
    doi = f" https://doi.org/{r['doi']}" if r.get("doi") else ""
    if r.get("jenis") in ("book", "monograph", "edited-book") and r.get("penerbit"):
        return f"{penulis} ({tahun}). {judul}. {r['penerbit']}.{doi}"
    if r.get("sumber"):
        return f"{penulis} ({tahun}). {judul}. {r['sumber']}.{doi}"
    return f"{penulis} ({tahun}). {judul}.{doi}"

def buat_ieee(r, no):
    ps = r.get("penulis") or []
    if not ps:
        penulis = "Anon."
    elif len(ps) > 6:
        penulis = nama_ieee(ps[0]) + " et al."
    else:
        penulis = ", ".join(nama_ieee(p) for p in ps[:-1]) + (" and " if len(ps) > 1 else "") + nama_ieee(ps[-1])
    tahun = r.get("tahun") or "n.d."
    bagian = f'"{r.get("judul", "")},"'
    if r.get("sumber"):
        bagian += f" {r['sumber']},"
    bagian += f" {tahun}"
    if r.get("doi"):
        bagian += f", doi: {r['doi']}"
    return f"[{no}] {penulis}, {bagian}."

def buat_docx(rows, fmt, path):
    """Daftar pustaka Word dengan hanging indent 1,27 cm (siap tempel ke skripsi)."""
    from docx import Document
    from docx.shared import Cm, Pt
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    for r in rows:
        p = doc.add_paragraph(r["apa"] if fmt == "apa" else r["ieee"])
        pf = p.paragraph_format
        pf.left_indent = Cm(1.27)
        pf.first_line_indent = Cm(-1.27)
        pf.space_after = Pt(6)
    doc.save(path)

def buat_matriks_xlsx(rows, path, catatan=None):
    catatan = catatan or {}
    df = pd.DataFrame([{
        "No": i, "Kategori": r.get("kategori", ""), "Penulis": "; ".join(r.get("penulis") or []),
        "Tahun": r.get("tahun"), "Judul": r.get("judul"), "Sumber": r.get("sumber"),
        "Pendekatan": (r.get("metode") or {}).get("pendekatan", ""),
        "Desain": (r.get("metode") or {}).get("desain", ""),
        "Sampel": (r.get("metode") or {}).get("sampel", ""),
        "Teknik Analisis": ", ".join((r.get("metode") or {}).get("analisis") or []),
        "Instrumen": ", ".join((r.get("metode") or {}).get("instrumen") or []),
        "Hasil Utama": r.get("hasil_utama", ""), "DOI": r.get("doi"), "Sitasi APA": r.get("apa", ""),
        "Catatan": catatan.get(r.get("uid"), ""),
    } for i, r in enumerate(rows, 1)])
    with pd.ExcelWriter(path, engine="openpyxl") as x:
        df.to_excel(x, index=False, sheet_name="Matriks Literatur")

def buat_matriks_docx(result, catatan, path):
    """Matriks literatur versi Word — impor Notion (Import → Word) paling andal, tabel asli."""
    from docx import Document
    from docx.shared import Pt
    catatan = catatan or {}
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(11)
    doc.add_heading(f"Matriks Literatur — {result['topik']}", level=1)
    for kat in ("Nasional", "Internasional"):
        rows = result["hasil"].get(kat) or []
        if not rows:
            continue
        doc.add_heading(f"{kat} ({len(rows)})", level=2)
        t = doc.add_table(rows=1, cols=6)
        t.style = "Table Grid"
        for i, h in enumerate(["No", "Judul", "Tahun", "Metode", "Hasil utama", "Catatan"]):
            t.rows[0].cells[i].text = h
        for i, r in enumerate(rows, 1):
            m = r.get("metode") or {}
            metode = " · ".join(x for x in [m.get("pendekatan"), m.get("desain"), m.get("sampel"),
                                           ", ".join(m.get("analisis") or [])] if x)
            sel = t.add_row().cells
            sel[0].text = str(i)
            sel[1].text = r.get("judul") or ""
            sel[2].text = str(r.get("tahun") or "")
            sel[3].text = metode
            sel[4].text = r.get("hasil_utama") or ""
            sel[5].text = catatan.get(r.get("uid"), "")
    doc.add_heading("Daftar Pustaka (APA)", level=2)
    for kat in ("Nasional", "Internasional"):
        for r in result["hasil"].get(kat) or []:
            if r.get("apa"):
                p = doc.add_paragraph(r["apa"])
                p.paragraph_format.left_indent = None
    doc.save(path)


def _tabel_matriks_doc(doc, result, catatan):
    catatan = catatan or {}
    for kat in ("Nasional", "Internasional"):
        rows = result["hasil"].get(kat) or []
        if not rows:
            continue
        doc.add_heading(f"{kat} ({len(rows)})", level=2)
        t = doc.add_table(rows=1, cols=6)
        t.style = "Table Grid"
        for i, h in enumerate(["No", "Judul", "Tahun", "Metode", "Hasil utama", "Catatan"]):
            t.rows[0].cells[i].text = h
        for i, r in enumerate(rows, 1):
            m = r.get("metode") or {}
            metode = " · ".join(x for x in [m.get("pendekatan"), m.get("desain"), m.get("sampel"),
                                           ", ".join(m.get("analisis") or [])] if x)
            sel = t.add_row().cells
            sel[0].text = str(i)
            sel[1].text = r.get("judul") or ""
            sel[2].text = str(r.get("tahun") or "")
            sel[3].text = metode
            sel[4].text = r.get("hasil_utama") or ""
            sel[5].text = catatan.get(r.get("uid"), "")


def _tabel_prisma(result):
    prisma = result.get("prisma") or {}
    per = prisma.get("per_kategori") or {}
    tahap = [("Record ditemukan (OpenAlex, Crossref, dork, snowball)", "ditarik"),
             ("Duplikat dihapus", "duplikat"),
             ("Disaring filter predator", "predator"),
             ("Kandidat unik setelah penyaringan", "kandidat"),
             ("Kandidat dinilai kelayakannya", "dinilai"),
             ("Tidak lolos / tidak terpilih", "ditolak"),
             ("Referensi dimasukkan", "masuk")]
    return [(label, *[per.get(kat, {}).get(kunci, 0) for kat in ("Nasional", "Internasional")],
             prisma.get(kunci, 0)) for label, kunci in tahap]


def buat_laporan_docx(result, catatan, path):
    """Laporan tinjauan siap Bab 2: PRISMA, tema & gap, matriks, daftar pustaka APA."""
    from docx import Document
    from docx.shared import Pt
    catatan = catatan or {}
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    doc.add_heading("Laporan Tinjauan Literatur", level=0)
    doc.add_paragraph(f"Topik: {result.get('topik', '')}")
    doc.add_paragraph(f"Disusun otomatis oleh Referensia pada "
                      f"{datetime.datetime.now(WIB):%d-%m-%Y %H:%M} WIB. Jumlah referensi: "
                      f"{result.get('total', 0)} ({len(result['hasil'].get('Nasional') or [])} nasional, "
                      f"{len(result['hasil'].get('Internasional') or [])} internasional).")

    doc.add_heading("1. Alur seleksi literatur (PRISMA)", level=1)
    if result.get("prisma"):
        t = doc.add_table(rows=1, cols=4)
        t.style = "Table Grid"
        for i, h in enumerate(["Tahap", "Nasional", "Internasional", "Total"]):
            t.rows[0].cells[i].text = h
        for label, n, i_, total in _tabel_prisma(result):
            sel = t.add_row().cells
            for j, nilai in enumerate([label, n, i_, total]):
                sel[j].text = str(nilai)
        doc.add_paragraph("Angka diambil otomatis dari tahap pencarian yang benar-benar dijalankan mesin, "
                          "bukan perkiraan manual. Tahap 'tidak lolos' mencakup skor relevansi rendah, "
                          "kategori tidak sesuai, dan PDF legal tidak tersedia.")
    else:
        doc.add_paragraph("Statistik alur seleksi tidak tersedia untuk hasil pencarian lama. "
                          "Jalankan pencarian baru agar diagram PRISMA ikut tercatat.")

    doc.add_heading("2. Tema dan peluang penelitian (research gap)", level=1)
    tema = result.get("tema_kat") or {}
    for kat in ("Nasional", "Internasional"):
        if tema.get(kat):
            doc.add_heading(f"Tema dominan — {kat}", level=2)
            doc.add_paragraph(", ".join(tema[kat]))
    gap = ((result.get("analisis") or {}).get("gap")) or []
    if gap:
        doc.add_heading("Kutipan penanda celah penelitian", level=2)
        for g in gap:
            doc.add_paragraph(f"“{g['teks']}” — {g.get('judul', '')} ({g.get('tahun') or '—'})")
    else:
        doc.add_paragraph("Tidak ada kalimat penanda celah penelitian yang terdeteksi pada abstrak.")

    doc.add_heading("3. Matriks literatur", level=1)
    _tabel_matriks_doc(doc, result, catatan)

    doc.add_heading("4. Daftar pustaka (APA 7)", level=1)
    for kat in ("Nasional", "Internasional"):
        for r in result["hasil"].get(kat) or []:
            if r.get("apa"):
                doc.add_paragraph(r["apa"])
    doc.save(path)


def _sel_md(t):
    return str(t or "").replace("|", "\\|").replace("\n", " ").strip() or "—"

def buat_markdown(result, catatan=None):
    """Matriks literatur + sitasi format Markdown, siap tempel ke Notion/Obsidian."""
    catatan = catatan or {}
    baris = [f"# Referensia — {result['topik']}", "",
             f"> Kueri nasional: {result.get('topik_id', '')} · internasional: {result.get('topik_en', '')}",
             f"> {result.get('total', 0)} referensi · {result.get('jumlah_pdf', 0)} PDF legal", ""]
    for kat in ("Nasional", "Internasional"):
        rows = result["hasil"].get(kat) or []
        if not rows:
            continue
        baris += [f"## {'🇮🇩' if kat == 'Nasional' else '🌍'} {kat} ({len(rows)})", "",
                  "| No | Judul | Tahun | Metode | Hasil utama | Catatan | DOI |",
                  "| --- | --- | --- | --- | --- | --- | --- |"]
        for r in rows:
            m = r.get("metode") or {}
            metode = " · ".join(x for x in [m.get("pendekatan"), m.get("desain"), m.get("sampel")] if x)
            doi = f"[{r['doi']}](https://doi.org/{r['doi']})" if r.get("doi") else "—"
            baris.append("| {} | {} | {} | {} | {} | {} | {} |".format(
                r["no"], _sel_md(r.get("judul")), r.get("tahun") or "—", _sel_md(metode),
                _sel_md(r.get("hasil_utama")), _sel_md(catatan.get(r.get("uid"))), doi))
        baris += ["", f"### Sitasi APA — {kat}", ""]
        for r in rows:
            if r.get("apa"):
                baris.append(f"{r['no']}. {r['apa']}")
        baris.append("")
    return "\n".join(baris)

ZOTERO_JENIS = {"article": "journalArticle", "review": "journalArticle", "preprint": "preprint",
                "book": "book", "book-chapter": "bookSection", "dissertation": "thesis", "report": "report"}

def zotero_item(r):
    creators = []
    for p in r.get("penulis") or []:
        fam, gv = _pisah_nama(p)
        creators.append({"creatorType": "author", "lastName": fam, "firstName": " ".join(gv)})
    tags = [{"tag": t} for t in (r.get("kategori"), "Referensia") if t]
    return {"itemType": ZOTERO_JENIS.get(r.get("jenis"), "journalArticle"),
            "title": r.get("judul", ""), "creators": creators, "date": str(r.get("tahun") or ""),
            "DOI": r.get("doi", ""), "publicationTitle": r.get("sumber", ""),
            "publisher": r.get("penerbit", ""), "abstractNote": r.get("abstrak", ""), "tags": tags}


def kartu(html_isi, judul=None, warna=None):
    w = warna or WARNA["pink"]
    j = f'<div style="font-size:15px;font-weight:800;color:{w};margin-bottom:8px">{judul}</div>' if judul else ""
    return (f'<div style="background:{WARNA["panel"]};color:{WARNA["teks"]};border:1px solid #2C2E52;'
            f'border-radius:16px;padding:16px;margin:10px 0;{FONT}">{j}{html_isi}</div>')

def judul_besar(teks, sub=""):
    _emit("banner", title=teks, subtitle=re.sub(r"<[^>]+>", " ", sub))

def kartu_verifikasi(hasil, target):
    counts = {kat: {"n": len(hasil[kat]), "target": target[kat]}
              for kat in ("Nasional", "Internasional") if target[kat] > 0}
    semua_pas = all(c["n"] == c["target"] for c in counts.values())
    _emit("verification", counts=counts, semua_pas=semua_pas)
    return semua_pas

def banner_penutup():
    _emit("closing")
    print("=" * 52)
    print("  MASUKKAN FILE DALAM ZIP KE MENDELEY / ZOTERO")
    print("  TERIMA KASIH SUDAH MEMAKAI REFERENSIA")
    print("=" * 52)

def tabel_html(rows, warna):
    sel = "padding:8px 10px;border-bottom:1px solid #2C2E52;vertical-align:top"
    kepala = "".join(f'<th style="{sel};text-align:left;color:{warna};white-space:nowrap">{h}</th>'
                     for h in ["No", "Skor", "Relevansi", "Judul & Penulis", "Tahun", "Jenis", "Indeks", "DOI", "PDF"])
    isi = []
    for r in rows:
        doi = (f'<a href="https://doi.org/{html.escape(r["doi"])}" target="_blank" style="color:{WARNA["violet"]}">'
               f'{html.escape(r["doi"])}</a>') if r["doi"] else "-"
        indeks = " · ".join(x for x in ("DOAJ" if r.get("doaj") else "",
                                        f'SINTA {r["sinta"]}' if r.get("sinta") else "") if x) or "-"
        isi.append(
            f'<tr><td style="{sel}">{r["no"]}</td><td style="{sel};font-weight:800">{r["skor"]}</td>'
            f'<td style="{sel};white-space:nowrap">{label_relevansi(r["skor"])}</td>'
            f'<td style="{sel};min-width:240px"><b>{html.escape(r["judul"])}</b><br>'
            f'<span style="color:{WARNA["abu"]}">{html.escape(penulis_singkat(r["penulis"]))}'
            f'{" — " + html.escape(r["sumber"]) if r["sumber"] else ""}</span></td>'
            f'<td style="{sel}">{r["tahun"] or "-"}</td><td style="{sel}">{NAMA_JENIS.get(r["jenis"], r["jenis"])}</td>'
            f'<td style="{sel};white-space:nowrap">{indeks}</td>'
            f'<td style="{sel};word-break:break-all;min-width:140px">{doi}</td>'
            f'<td style="{sel}">{"✅" if r.get("pdf") else "—"}</td></tr>')
    return (f'<div style="overflow-x:auto"><table style="border-collapse:collapse;width:100%;font-size:13px;'
            f'color:{WARNA["teks"]}"><thead><tr>{kepala}</tr></thead><tbody>{"".join(isi)}</tbody></table></div>')

def tema_dominan(rows, kunci, n=10):
    dok = [f"{r['judul']} {r['abstrak']}" for r in rows]
    if len(dok) < 2:
        return []
    try:
        vec = TfidfVectorizer(tokenizer=tokenisasi, lowercase=False, token_pattern=None, ngram_range=(1, 2),
                              sublinear_tf=True)
        X = vec.fit_transform(dok)
    except ValueError:
        return []
    bobot = np.asarray(X.sum(axis=0)).ravel()
    fitur = vec.get_feature_names_out()
    hasil = []
    for i in bobot.argsort()[::-1]:
        f = fitur[i]
        if any(cocok(k, set(f.split())) for k in kunci) or any(f in h or h in f for h in hasil):
            continue
        hasil.append(f)
        if len(hasil) >= n:
            break
    return hasil

def _kalimat(teks):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", teks or "") if len(s.strip()) > 20]


POLA_GAP = re.compile(
    r"belum (?:banyak|ada|diteliti|dikaji|optimal|maksimal)|masih (?:sedikit|jarang|terbatas|kurang|menjadi)|"
    r"lack(?:s|ing)? of|limited (?:research|studies|evidence|attention)|few studies|no (?:study|research)|"
    r"little (?:is known|research)|future research|penelitian (?:selanjutnya|lanjutan)|belum pernah|"
    r"masih menjadi (?:tantangan|kendala|masalah)|however,? (?:few|little)", re.I)


def _gap_dari(rows, maks=6):
    """Kutipan kalimat yang menandakan celah penelitian, diambil apa adanya dari abstrak."""
    hasil, teks_ada = [], set()
    for r in rows:
        for s in _kalimat(r.get("abstrak")):
            if not POLA_GAP.search(s):
                continue
            kunci = s.lower()[:80]
            if kunci in teks_ada:
                continue
            teks_ada.add(kunci)
            hasil.append({"teks": potong(s, 320), "judul": r.get("judul", ""),
                          "tahun": r.get("tahun"), "uid": r.get("uid", "")})
            if len(hasil) >= maks:
                return hasil
    return hasil


def klaster_topik(rows, kunci=None, maks_klaster=4):
    """Kelompokkan referensi berdasarkan kemiripan TF-IDF; label dari istilah teratas."""
    kunci = kunci or []
    rows = [r for r in rows if (r.get("judul") or "").strip()]
    if len(rows) < 5:
        return []
    dok = [f"{r['judul']} {r.get('abstrak') or ''}" for r in rows]
    try:
        from sklearn.cluster import KMeans
        vec = TfidfVectorizer(tokenizer=tokenisasi, lowercase=False, token_pattern=None,
                              ngram_range=(1, 2), sublinear_tf=True, min_df=1, max_df=0.9)
        X = vec.fit_transform(dok)
        k = min(maks_klaster, max(2, len(rows) // 3))
        model = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
        fitur = vec.get_feature_names_out()
    except Exception:
        return []
    hasil = []
    for i in range(k):
        idx = [j for j, lab in enumerate(model.labels_) if lab == i]
        if not idx:
            continue
        label = []
        for j in model.cluster_centers_[i].argsort()[::-1]:
            f = fitur[j]
            if any(cocok(kk, set(f.split())) for kk in kunci):
                continue
            if any(f in l or l in f for l in label):
                continue
            label.append(f)
            if len(label) >= 3:
                break
        hasil.append({"label": " · ".join(label) or f"Klaster {i + 1}", "jumlah": len(idx),
                      "judul": [rows[j]["judul"] for j in idx][:8]})
    hasil.sort(key=lambda c: -c["jumlah"])
    return hasil


def statistik_tren(result):
    """Ringkasan tren & gap dari referensi terpilih (tanpa panggilan jaringan)."""
    hasil = result.get("hasil") or {}
    semua = [r for kat in ("Nasional", "Internasional") for r in hasil.get(kat) or []]
    tahun_ada = sorted({r.get("tahun") for r in semua if r.get("tahun")})
    tahun = [{"tahun": t, **{kat: sum(1 for r in hasil.get(kat) or [] if r.get("tahun") == t)
                             for kat in ("Nasional", "Internasional")}} for t in tahun_ada]
    hitung = {}
    for r in semua:
        nama = (r.get("sumber") or "").strip()
        if nama:
            hitung[nama] = hitung.get(nama, 0) + 1
    sumber = [{"nama": n, "jumlah": c} for n, c in sorted(hitung.items(), key=lambda x: -x[1])[:10]]
    pendekatan, analisis = {}, {}
    for r in semua:
        m = r.get("metode") or {}
        p = m.get("pendekatan") or "Tidak terdeteksi"
        pendekatan[p] = pendekatan.get(p, 0) + 1
        for a in m.get("analisis") or []:
            analisis[a] = analisis.get(a, 0) + 1
    indeks = {"DOAJ": sum(1 for r in semua if r.get("doaj")),
              "SINTA": sum(1 for r in semua if r.get("sinta")),
              "Tidak terdeteksi": sum(1 for r in semua if not r.get("doaj") and not r.get("sinta"))}
    kunci = {}
    for kat in ("Nasional", "Internasional"):
        freq = {}
        for r in hasil.get(kat) or []:
            for k in dict.fromkeys(r.get("kata_cocok") or []):
                freq[k] = freq.get(k, 0) + 1
        kunci[kat] = [{"kata": k, "jumlah": n} for k, n in sorted(freq.items(), key=lambda x: -x[1])[:10]]
    return {"tahun": tahun, "sumber": sumber, "pendekatan": pendekatan, "analisis": analisis,
            "indeks": indeks, "kunci": kunci,
            "klaster": klaster_topik(semua, (result.get("kunci_kat") or {}).get("Nasional") or []),
            "gap": _gap_dari(semua)}


def buat_prisma(hasil, pool_kat, stat):
    """Angka diagram PRISMA dari pencatatan tahap pencarian nyata."""
    per = {}
    for kat in ("Nasional", "Internasional"):
        dinilai = stat["dinilai"].get(kat) or set()
        masuk = len(hasil.get(kat) or [])
        per[kat] = {
            "ditarik": int(stat["ditarik"].get(kat, 0)),
            "duplikat": int(stat["duplikat"].get(kat, 0)),
            "predator": int(stat["predator"].get(kat, 0)),
            "kandidat": len(pool_kat.get(kat) or {}),
            "dinilai": len(dinilai),
            "ditolak": max(0, len(dinilai) - masuk),
            "masuk": masuk,
            "tanpa_pdf": sum(1 for r in hasil.get(kat) or [] if not r.get("pdf")),
        }
    kunci = ("ditarik", "duplikat", "predator", "kandidat", "dinilai", "ditolak", "masuk", "tanpa_pdf")
    return {"per_kategori": per, **{k: sum(v[k] for v in per.values()) for k in kunci}}


def buat_grafik(hasil, kunci_kat, folder):
    plt.rcParams.update({"figure.facecolor": WARNA["bg"], "axes.facecolor": WARNA["panel"],
                         "axes.edgecolor": "#2C2E52", "text.color": WARNA["teks"], "axes.labelcolor": WARNA["teks"],
                         "xtick.color": WARNA["abu"], "ytick.color": WARNA["abu"], "font.size": 10,
                         "legend.facecolor": WARNA["panel"], "legend.edgecolor": "#2C2E52"})
    gambar = []
    tahun = sorted({r["tahun"] for kat in hasil for r in hasil[kat] if r["tahun"]})
    if tahun:
        fig, ax = plt.subplots(figsize=(7, 3.3))
        bawah = np.zeros(len(tahun))
        for kat in ("Nasional", "Internasional"):
            if not hasil[kat]:
                continue
            nilai = np.array([sum(1 for r in hasil[kat] if r["tahun"] == t) for t in tahun])
            ax.bar([str(t) for t in tahun], nilai, bottom=bawah, color=WARNA_KAT[kat], label=kat)
            bawah += nilai
        ax.set_title("Sebaran Tahun Terbit", color=WARNA["teks"], fontweight="bold")
        ax.set_ylabel("Jumlah")
        ax.legend()
        plt.xticks(rotation=45, ha="right")
        fig.tight_layout()
        p = os.path.join(folder, "grafik_tahun.png"); fig.savefig(p, dpi=150); gambar.append(p)
        plt.show(); plt.close(fig)
    for kat in ("Nasional", "Internasional"):
        rows, kunci = hasil[kat], kunci_kat.get(kat) or []
        if not rows or not kunci:
            continue
        jumlah = [sum(1 for r in rows if k in r.get("kata_cocok", [])) for k in kunci]
        fig, ax = plt.subplots(figsize=(7, max(2.2, 0.45 * len(kunci) + 0.9)))
        ax.barh(kunci[::-1], jumlah[::-1], color=WARNA_KAT[kat])
        ax.set_title(f"{kat}: kata kunci dibahas oleh berapa referensi?", color=WARNA["teks"], fontweight="bold")
        ax.set_xlabel(f"Jumlah referensi (dari {len(rows)})")
        fig.tight_layout()
        p = os.path.join(folder, f"grafik_kata_kunci_{kat.lower()}.png"); fig.savefig(p, dpi=150); gambar.append(p)
        plt.show(); plt.close(fig)
    return gambar

def blok_prisma_html(prisma):
    if not prisma:
        return ""
    per = prisma.get("per_kategori") or {}
    kepala = "".join(f"<th style='text-align:left;padding:6px 10px'>Tahap</th>")
    kepala += "".join(f"<th style='padding:6px 10px'>🇮🇩 Nasional</th><th style='padding:6px 10px'>🌍 Internasional</th>"
                      f"<th style='padding:6px 10px'>Total</th>")
    baris = ""
    for label, n, i_, total in _tabel_prisma({"prisma": prisma}):
        baris += (f"<tr><td style='padding:6px 10px;border-top:1px solid #2C2E52'>{html.escape(label)}</td>"
                  f"<td style='padding:6px 10px;text-align:center;border-top:1px solid #2C2E52'>{n}</td>"
                  f"<td style='padding:6px 10px;text-align:center;border-top:1px solid #2C2E52'>{i_}</td>"
                  f"<td style='padding:6px 10px;text-align:center;font-weight:700;border-top:1px solid #2C2E52'>{total}</td></tr>")
    return (f"<h2>🔎 Alur Seleksi Literatur (PRISMA)</h2><div class='box'>"
            f"<table style='border-collapse:collapse;width:100%;font-size:13px;color:{WARNA['teks']}'>"
            f"<thead><tr>{kepala}</tr></thead><tbody>{baris}</tbody></table>"
            f"<div class='meta' style='margin-top:8px'>Angka otomatis dari tahap pencarian mesin, bukan perkiraan. "
            f"'Tidak lolos' mencakup skor rendah, kategori tidak sesuai, dan PDF legal tidak tersedia.</div></div>")


def blok_gap_html(analisis):
    gap = (analisis or {}).get("gap") or []
    if not gap:
        return ""
    item = "".join(
        f"<li style='margin:6px 0'>“{html.escape(g.get('teks', ''))}”<br>"
        f"<span class='meta'>— {html.escape(g.get('judul', ''))} ({g.get('tahun') or '—'})</span></li>"
        for g in gap)
    return (f"<h2>🧭 Petunjuk Celah Penelitian</h2><div class='box'><ul style='margin:0;padding-left:18px'>"
            f"{item}</ul></div>")


def laporan_html(ctx, hasil, kunci_kat, tema_kat, ringkasan, gambar, prisma=None, analisis=None):
    img = "".join(f'<img src="data:image/png;base64,{base64.b64encode(open(g, "rb").read()).decode()}" '
                  f'style="max-width:100%;border-radius:12px;margin:8px 0">' for g in gambar)
    bagian = []
    for kat in ("Nasional", "Internasional"):
        if not hasil[kat]:
            continue
        daftar = []
        for r in hasil[kat]:
            doi = (f'<a href="https://doi.org/{html.escape(r["doi"])}">{html.escape(r["doi"])}</a>' if r["doi"] else "-")
            daftar.append(
                f'<div class="ref"><div class="no" style="color:{WARNA_KAT[kat]}">#{r["no"]} · Skor {r["skor"]} · '
                f'{label_relevansi(r["skor"])}</div><h3>{html.escape(r["judul"])}</h3>'
                f'<div class="meta">{html.escape(", ".join(r["penulis"][:6]) or "-")} · {r["tahun"] or "-"} · '
                f'{NAMA_JENIS.get(r["jenis"], r["jenis"])}{" · " + html.escape(r["sumber"]) if r["sumber"] else ""}</div>'
                f'<div class="meta">DOI: {doi} · Sitasi: {r["sitasi"]} · PDF: '
                f'{html.escape(r["pdf"]) if r.get("pdf") else "tidak tersedia (cek tautan DOI)"}</div>'
                f'<div class="meta">Kata kunci yang cocok: {html.escape(", ".join(r.get("kata_cocok", [])) or "-")}</div>'
                f'<p>{html.escape(potong(r["abstrak"], 700)) or "<i>Abstrak tidak tersedia.</i>"}</p>'
                f'<div class="meta"><b>Ringkasan:</b> {html.escape(r.get("ringkasan") or "-")}</div>'
                f'<div class="meta"><b>Metode:</b> {html.escape(teks_metode(r.get("metode") or {}))}</div>'
                f'<div class="meta"><b>Hasil utama:</b> {html.escape(r.get("hasil_utama") or "-")}</div>'
                f'<div class="meta"><b>APA:</b> {html.escape(r.get("apa", "-"))}<br>'
                f'<b>IEEE:</b> {html.escape(r.get("ieee", "-"))}</div></div>')
        chips_k = "".join(f'<span class="chip">{html.escape(k)}</span>' for k in kunci_kat.get(kat, []))
        chips_t = "".join(f'<span class="chip">{html.escape(t)}</span>' for t in tema_kat.get(kat, [])) or "-"
        bagian.append(f'<h2 style="color:{WARNA_KAT[kat]}">{IKON_KAT[kat]} Referensi {kat} ({len(hasil[kat])})</h2>'
                      f'<div class="box"><b>Kata kunci:</b><br>{chips_k}<br><br><b>Tema yang sering muncul:</b><br>{chips_t}</div>'
                      + "".join(daftar))
    return f"""<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Laporan Referensia — {html.escape(ctx.topik)}</title>
<style>body{{background:{WARNA['bg']};color:{WARNA['teks']};{FONT};margin:0;padding:18px;line-height:1.55}}
.wrap{{max-width:900px;margin:auto}} h1{{background:linear-gradient(90deg,{WARNA['pink']},{WARNA['violet']});-webkit-background-clip:text;background-clip:text;color:transparent;font-size:30px;margin:6px 0}}
h2{{margin-top:28px}} .box,.ref{{background:{WARNA['panel']};border:1px solid #2C2E52;border-radius:16px;padding:16px;margin:12px 0}}
.no{{font-weight:800;font-size:13px}} h3{{margin:6px 0;font-size:17px}} .meta{{color:{WARNA['abu']};font-size:13px;margin:3px 0}}
a{{color:{WARNA['violet']};word-break:break-all}} .chip{{display:inline-block;background:#232547;border-radius:99px;padding:4px 10px;margin:3px;font-size:13px}}</style></head>
<body><div class="wrap"><div class="meta">Referensia v1.0</div><h1>Laporan Analisis Referensi</h1>
<div class="box"><b>Topik:</b> {html.escape(ctx.topik)}<br><b>Kueri nasional:</b> {html.escape(ctx.topik_id)}<br>
<b>Kueri internasional:</b> {html.escape(ctx.topik_en)}<br>{ringkasan}</div>
<div class="box">{img}</div>{blok_prisma_html(prisma)}{blok_gap_html(analisis)}{"".join(bagian)}
<div class="meta" style="text-align:center;margin:24px 0">Skor = kemiripan isi (TF-IDF) 40% + cakupan kata kunci & frasa 30% + peringkat mesin pencari 17% + sitasi 8% + kebaruan 5%.<br>
Nasional = jurnal/penerbit/repositori Indonesia · Internasional = jurnal/penerbit luar Indonesia.<br>
Terima kasih sudah memakai Referensia 💜</div></div></body></html>"""


# ============================ program utama ============================
def jalankan_referensia(judul_topik, jumlah_nasional=10, jumlah_internasional=5, jenis_referensi="Semua",
                      umur_maksimal=0, tahun_dari=0, tahun_sampai=0, wajib_ada_DOI=True, wajib_ada_PDF=True,
                      longgarkan_jika_kurang=True, pakai_google_dorks=True, judul_topik_inggris="", email="",
                      openalex_api_key="", simpan_ke_google_drive=True, saring_predator=True, cek_indeks=True,
                      pakai_snowball=True, progress=None):
    global _PROG
    _PROG = progress
    _stdout_asli = sys.stdout
    if progress:
        sys.stdout = _LogTee(_stdout_asli)
    try:
        return _jalankan(judul_topik, jumlah_nasional, jumlah_internasional, jenis_referensi,
                         umur_maksimal, tahun_dari, tahun_sampai, wajib_ada_DOI, wajib_ada_PDF,
                         longgarkan_jika_kurang, pakai_google_dorks, judul_topik_inggris, email,
                         openalex_api_key, simpan_ke_google_drive, saring_predator, cek_indeks, pakai_snowball)
    finally:
        sys.stdout = _stdout_asli
        _PROG = None

def _jalankan(judul_topik, jumlah_nasional, jumlah_internasional, jenis_referensi,
              umur_maksimal, tahun_dari, tahun_sampai, wajib_ada_DOI, wajib_ada_PDF,
              longgarkan_jika_kurang, pakai_google_dorks, judul_topik_inggris, email,
              openalex_api_key, simpan_ke_google_drive, saring_predator=True, cek_indeks=True,
              pakai_snowball=True):
    topik = bersih(judul_topik)
    target = {"Nasional": max(0, int(jumlah_nasional or 0)), "Internasional": max(0, int(jumlah_internasional or 0))}
    if len(topik) < 3:
        _emit("warning", text="Kolom judul_topik masih kosong. Isi dulu, lalu jalankan lagi.")
        return None
    if sum(target.values()) == 0:
        _emit("warning", text="Isi minimal salah satu: jumlah_nasional atau jumlah_internasional.")
        return None
    mulai = time.time()
    sekarang = datetime.datetime.now(WIB)
    th_ini = sekarang.year
    umur = max(0, int(umur_maksimal or 0))
    if umur:  # contoh: umur 5 di tahun 2026 -> 2021–2026
        t_dari, t_sampai = th_ini - umur, th_ini
    else:
        t_dari, t_sampai = int(tahun_dari or 0), int(tahun_sampai or 0)
        if t_dari and t_sampai and t_dari > t_sampai:
            t_dari, t_sampai = t_sampai, t_dari
    t_dari = t_dari if 1900 < t_dari <= th_ini + 1 else 0
    t_sampai = t_sampai if 1900 < t_sampai <= th_ini + 1 else 0
    teks_rentang = (f"{t_dari or '…'}–{t_sampai or th_ini}" if (t_dari or t_sampai) else "semua tahun")
    if umur:
        teks_rentang += f" (umur maks. {umur} tahun)"
    akar = "/content/Referensia_hasil" if DI_COLAB else os.path.abspath("Referensia_hasil")
    folder = os.path.join(akar, f"Referensia_{slug(topik)}_{sekarang:%Y%m%d_%H%M%S}")
    folder_pdf = os.path.join(folder, "PDF")
    os.makedirs(folder_pdf, exist_ok=True)

    judul_besar("Referensia 🔎", f"Topik: {html.escape(topik)}<br>Target: 🇮🇩 {target['Nasional']} Nasional · "
                               f"🌍 {target['Internasional']} Internasional — harus PAS<br>📅 {teks_rentang}")
    print("🌐 [1/4] Menyiapkan kata kunci nasional & internasional …")
    topik_id, topik_en, topik_en_skor = siapkan_topik(topik, judul_topik_inggris)
    print(f"   🇮🇩 Nasional      : {topik_id}")
    print(f"   🌍 Internasional : {topik_en}")
    print(f"   📅 Rentang tahun : {teks_rentang}")
    if pakai_google_dorks:
        print("   🔎 Google Dorks   : aktif (filetype:pdf, situs bajakan otomatis dilewati)")

    nama_dipakai = set()
    def nama_unik(nm):
        dasar, i = nm, 2
        while nm.lower() in nama_dipakai:
            nm = f"{dasar[:-4]}_{i}.pdf"; i += 1
        nama_dipakai.add(nm.lower())
        return nm

    ctx = Konteks(topik=topik, topik_id=topik_id, topik_en=topik_en, topik_en_skor=topik_en_skor, jenis=jenis_referensi,
                  tahun_dari=t_dari, tahun_sampai=t_sampai, teks_rentang=teks_rentang,
                  pakai_dork=bool(pakai_google_dorks), dork_kuota=40, mesin_mati=set(), dork_diumumkan=False,
                  wajib_doi=bool(wajib_ada_DOI), wajib_pdf=bool(wajib_ada_PDF),
                  longgarkan=bool(longgarkan_jika_kurang), email=email_valid(email),
                  saring_predator=bool(saring_predator), cek_indeks=bool(cek_indeks),
                  snowball=bool(pakai_snowball),
                  api_key=(openalex_api_key or "").strip(), folder_pdf=folder_pdf, nama_unik=nama_unik,
                  ditolak={"Nasional": set(), "Internasional": set()},
                  gagal_pdf={"Nasional": set(), "Internasional": set()},
                  pindahan={"Nasional": [], "Internasional": []}, dipilih_uid=set())

    print("🔎 [2/4] Mencari, menganalisis & mengunduh sampai jumlahnya PAS …")
    hasil, pool_kat, catatan, kunci_kat = {}, {}, [], {}
    for kat in ("Nasional", "Internasional"):
        if target[kat] <= 0:
            hasil[kat] = []
            continue
        print(f" {IKON_KAT[kat]} {kat.upper()} — target {target[kat]}")
        rows, pool, cat = cari_kategori(kat, target[kat], ctx)
        hasil[kat], pool_kat[kat] = rows, pool
        catatan += cat
        kunci_kat[kat] = list(dict.fromkeys(tokenisasi(topik_id if kat == "Nasional" else topik_en_skor)))
        if len(rows) < target[kat]:
            catatan.append(f"{kat}: hanya ditemukan {len(rows)} dari {target[kat]} meski semua tahap pencarian sudah "
                           f"dijalankan. Coba topik yang lebih umum, perlebar rentang tahun, atau aktifkan pelonggaran.")
    if ctx.saring_predator and ctx.predator_disaring:
        print(f"   🛡️ Filter predator: {ctx.predator_disaring} kandidat dari penerbit terindikasi predator disaring")

    # PDF terbaik-usaha bila PDF tidak diwajibkan
    if not ctx.wajib_pdf:
        print("📥 Mengunduh PDF legal yang tersedia …")
        semua = [r for kat in hasil for r in hasil[kat]]
        for r in semua:
            r["nama_file"] = r.get("nama_file") or nama_unik(nama_file_pdf(r))
        with ThreadPoolExecutor(8) as ex:
            out = list(ex.map(lambda r: unduh_pdf(r, os.path.join(folder_pdf, r["kategori"])), semua))
        for r, o in zip(semua, out):
            r["pdf"] = o
        if ctx.pakai_dork:
            for r in semua:
                if not r["pdf"] and ctx.dork_kuota > 0:
                    r["pdf"] = dork_pdf_untuk(r, ctx, os.path.join(folder_pdf, r["kategori"]))

    # urutkan & nomori
    cek_kualitas(ctx, [r for kat in hasil for r in hasil[kat]])
    for kat in hasil:
        hasil[kat].sort(key=lambda r: -r["skor"])
        for no, r in enumerate(hasil[kat], 1):
            r["no"] = no
            r.setdefault("pdf", None)
    # bersihkan PDF yang tidak terpilih (jangan lebih)
    dipakai = {(r["kategori"], r["pdf"]) for kat in hasil for r in hasil[kat] if r.get("pdf")}
    for kat in ("Nasional", "Internasional"):
        d = os.path.join(folder_pdf, kat)
        if os.path.isdir(d):
            for fn in os.listdir(d):
                if (kat, fn) not in dipakai:
                    os.remove(os.path.join(d, fn))
            if not os.listdir(d):
                os.rmdir(d)

    print("📊 [3/4] Menyusun hasil analisis …")
    n_abstrak = lengkapi_abstrak_s2([r for kat in hasil for r in hasil[kat]])
    if n_abstrak:
        print(f"   📚 Abstrak dilengkapi dari Semantic Scholar: {n_abstrak} referensi")
    no_global = 0
    for kat in ("Nasional", "Internasional"):
        for r in hasil[kat]:
            r["ringkasan"] = ringkas_abstrak(r["abstrak"], kunci_kat[kat])
            r["metode"] = ekstrak_metode(r["abstrak"], r["judul"])
            r["hasil_utama"] = hasil_utama(r["abstrak"])
            r["apa"] = buat_apa(r)
            no_global += 1
            r["ieee"] = buat_ieee(r, no_global)
    print(f"   ✍️ Ringkasan, tabel metode & sitasi APA/IEEE disusun untuk {no_global} referensi")
    semua_pas = kartu_verifikasi(hasil, target)
    semua = [r for kat in ("Nasional", "Internasional") for r in hasil[kat]]
    if not semua:
        _emit("info", text="Belum ada referensi yang cocok. Coba topik lain atau pengaturan yang lebih longgar.")
        return None
    n_pdf = sum(1 for r in semua if r.get("pdf"))
    tahun_ada = [r["tahun"] for r in semua if r["tahun"]]
    ringkasan = (f"Target: 🇮🇩 {target['Nasional']} Nasional · 🌍 {target['Internasional']} Internasional · "
                 f"📅 {teks_rentang}<br>"
                 f"Didapat: 🇮🇩 <b>{len(hasil['Nasional'])}</b> · 🌍 <b>{len(hasil['Internasional'])}</b> · "
                 f"PDF legal: <b>{n_pdf}/{len(semua)}</b><br>Kandidat dianalisis: <b>"
                 f"{sum(len(p) for p in pool_kat.values())}</b> · Rentang tahun: <b>"
                 f"{(str(min(tahun_ada)) + '–' + str(max(tahun_ada))) if tahun_ada else '-'}</b> · Rata-rata skor: "
                 f"<b>{np.mean([r['skor'] for r in semua]):.1f}/100</b>")
    _emit("summary", html=ringkasan)
    if catatan:
        _emit("notes", items=list(catatan))

    tema_kat = {}
    for kat in ("Nasional", "Internasional"):
        if not hasil[kat]:
            continue
        tema_kat[kat] = tema_dominan(hasil[kat], kunci_kat[kat])
        teratas = sorted(hasil[kat], key=lambda r: -(r["sitasi"] or 0))[:3]
        _emit("analysis", kategori=kat, kunci=kunci_kat[kat], tema=tema_kat[kat],
              teratas=[{"judul": r["judul"], "tahun": r["tahun"], "sitasi": r["sitasi"]} for r in teratas])
    gambar = buat_grafik(hasil, kunci_kat, folder)
    for kat in ("Nasional", "Internasional"):
        if hasil[kat]:
            _emit("table", kategori=kat)

    prisma = buat_prisma(hasil, pool_kat, ctx.stat)
    analisis = statistik_tren({"hasil": hasil, "kunci_kat": kunci_kat})
    if prisma["ditarik"]:
        print(f"   🔎 PRISMA: {prisma['ditarik']} record ditemukan · {prisma['duplikat']} duplikat · "
              f"{prisma['predator']} predator disaring · {prisma['masuk']} masuk")

    print("📦 [4/4] Membuat file Mendeley & ZIP …")
    with open(os.path.join(folder, "01_IMPOR_REFERENSI.ris"), "w", encoding="utf-8") as f:
        f.write(buat_ris(semua, topik))
    with open(os.path.join(folder, "referensi.bib"), "w", encoding="utf-8") as f:
        f.write(buat_bib(semua))
    with open(os.path.join(folder, "daftar_DOI.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(r["doi"] for r in semua if r["doi"]) + "\n")
    with open(os.path.join(folder, "02_SITASI_APA.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(r["apa"] for r in semua) + "\n")
    with open(os.path.join(folder, "03_SITASI_IEEE.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(r["ieee"] for r in semua) + "\n")
    buat_docx(semua, "apa", os.path.join(folder, "daftar_pustaka_APA.docx"))
    buat_docx(semua, "ieee", os.path.join(folder, "daftar_pustaka_IEEE.docx"))
    buat_matriks_xlsx(semua, os.path.join(folder, "matriks_literatur.xlsx"))
    pd.DataFrame([{
        "Kategori": r["kategori"], "No": r["no"], "Skor Relevansi": r["skor"], "Label": label_relevansi(r["skor"]),
        "Judul": r["judul"], "Penulis": "; ".join(r["penulis"]), "Tahun": r["tahun"],
        "Jenis": NAMA_JENIS.get(r["jenis"], r["jenis"]), "Sumber/Jurnal": r["sumber"], "Penerbit": r["penerbit"],
        "Negara Penerbit": {"ID": "Indonesia", "LUAR": "Luar Indonesia"}.get(r.get("negara"), r.get("negara") or "-"), "DOI": r["doi"], "Tautan": r["url"], "Sitasi": r["sitasi"],
        "Kata Kunci Cocok": ", ".join(r.get("kata_cocok", [])), "Ditemukan via": r["asal"],
        "PDF via": r.get("sumber_pdf", "-") if r.get("pdf") else "-",
        "File PDF": f"PDF/{r['kategori']}/{r['pdf']}" if r.get("pdf") else "-", "Abstrak": r["abstrak"],
        "Ringkasan": r.get("ringkasan", ""), "Pendekatan": r.get("metode", {}).get("pendekatan", ""),
        "Desain": r.get("metode", {}).get("desain", ""), "Sampel": r.get("metode", {}).get("sampel", ""),
        "Teknik Analisis": ", ".join(r.get("metode", {}).get("analisis", [])),
        "Instrumen": ", ".join(r.get("metode", {}).get("instrumen", [])),
        "Hasil Utama": r.get("hasil_utama", ""),
        "Sitasi APA": r.get("apa", ""), "Sitasi IEEE": r.get("ieee", "")}
        for r in semua]).to_csv(os.path.join(folder, "daftar_referensi.csv"), index=False, encoding="utf-8-sig")
    buat_laporan_docx({"topik": topik, "hasil": hasil, "tema_kat": tema_kat, "prisma": prisma,
                       "analisis": analisis, "total": len(semua)},
                      {}, os.path.join(folder, "04_LAPORAN_TINJAUAN.docx"))
    with open(os.path.join(folder, "Laporan_Analisis_Referensia.html"), "w", encoding="utf-8") as f:
        f.write(laporan_html(ctx, hasil, kunci_kat, tema_kat, ringkasan, gambar, prisma, analisis))
    with open(os.path.join(folder, "BACA_DULU.txt"), "w", encoding="utf-8") as f:
        f.write(f"""Referensia v1.0
Topik      : {topik}
Kueri ID   : {topik_id}
Kueri EN   : {topik_en}
Rentang    : {teks_rentang}
Dibuat     : {sekarang:%d-%m-%Y %H:%M} WIB
Hasil      : Nasional {len(hasil['Nasional'])}/{target['Nasional']} · Internasional {len(hasil['Internasional'])}/{target['Internasional']}

ISI ZIP
- PDF/Nasional/                -> PDF referensi nasional (nama file = DOI - Judul)
- PDF/Internasional/           -> PDF referensi internasional (nama file = DOI - Judul)
- 01_IMPOR_REFERENSI.ris       -> semua referensi + tautan PDF + tag Nasional/Internasional
- referensi.bib                -> versi BibTeX (alternatif impor / LaTeX)
- daftar_DOI.txt               -> daftar DOI (tambah manual lewat DOI di Mendeley)
- 02_SITASI_APA.txt            -> daftar pustaka format APA 7 (siap tempel ke Word)
- 03_SITASI_IEEE.txt           -> daftar pustaka format IEEE (bernomor)
- daftar_pustaka_APA.docx      -> daftar pustaka Word, hanging indent rapi
- daftar_pustaka_IEEE.docx     -> versi IEEE
- matriks_literatur.xlsx       -> matriks Bab 2: penulis/tahun/metode/hasil utama
- daftar_referensi.csv         -> tabel referensi + kategori + skor + ringkasan + metode + sitasi
- 04_LAPORAN_TINJAUAN.docx     -> laporan siap Bab 2: alur PRISMA, tema & gap, matriks, daftar pustaka
- Laporan_Analisis_Referensia.html -> laporan analisis lengkap + abstrak

CARA MEMASUKKAN KE REFERENCE MANAGER (PILIH SALAH SATU)
A. Mendeley Reference Manager (laptop/PC):
   1. Ekstrak ZIP ini dulu (jangan dibuka langsung dari dalam ZIP).
   2. File -> Import library -> RIS (.ris) -> pilih 01_IMPOR_REFERENSI.ris -> Import.
      (Alternatif: File -> Import library -> BibTeX (.bib) -> referensi.bib.)
   3. Seret PDF dari folder PDF/Nasional atau PDF/Internasional ke referensi
      yang sesuai di Mendeley agar full-text menempel.
B. Zotero (laptop/PC):
   1. Ekstrak ZIP, lalu Zotero -> File -> Import... -> pilih 01_IMPOR_REFERENSI.ris.
   2. Centang "Copy files to the Zotero storage folder" -> Next/Finish.
      (Atau pakai tombol "Kirim ke Zotero" di aplikasi Referensia saat Zotero berjalan.)
   3. PDF belum menempel: klik kanan item -> "Find Available PDF",
      atau seret file dari folder PDF/ ke item yang sesuai.
C. Tanpa file (lewat DOI):
   1. Buka daftar_DOI.txt, salin DOI.
   2. Tambah entri lewat DOI di Mendeley (Add new) atau Zotero (tombol +).
   3. PDF dari folder PDF/ bisa diseret manual ke entri yang sesuai.

Nasional      = terbit di jurnal/penerbit/repositori Indonesia.
Internasional = terbit di jurnal/penerbit luar Indonesia.

TERIMA KASIH SUDAH MEMAKAI REFERENSIA
""")

    zip_path = folder + ".zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for dasar, _, files in os.walk(folder):
            for fn in files:
                p = os.path.join(dasar, fn)
                z.write(p, os.path.relpath(p, akar))
    ukuran = os.path.getsize(zip_path) / 1024 / 1024
    print(f"   ✓ ZIP siap: {os.path.basename(zip_path)} ({ukuran:.1f} MB) — selesai dalam {time.time() - mulai:.0f} detik")

    banner_penutup()
    _emit("done", zip_path=zip_path)
    return {
        "topik": topik, "topik_id": topik_id, "topik_en": topik_en,
        "target": target, "hasil": hasil, "catatan": catatan,
        "kunci_kat": kunci_kat, "tema_kat": tema_kat,
        "zip_path": zip_path, "folder": folder,
        "jumlah_pdf": n_pdf, "total": len(semua),
        "prisma": prisma, "analisis": analisis,
        "durasi_detik": round(time.time() - mulai),
    }

