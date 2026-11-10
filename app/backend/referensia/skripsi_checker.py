"""Modul Pemeriksa Skripsi (Skripsi Checker) — 100% Non-AI & Rule-Based.

Fitur Pemeriksaan Deterministik:
1. Validasi Silang Sitasi vs Daftar Pustaka (Cross-Referencing):
   - Deteksi sitasi dalam teks (APA, IEEE, naratif, tanda kurung).
   - Deteksi entri dalam Daftar Pustaka.
   - Menemukan sitasi yang TIDAK ADA di Daftar Pustaka (missing references).
   - Menemukan entri Daftar Pustaka yang TIDAK PERNAH DIKUTIP (orphan references).
2. Pemeriksaan Struktur Bab Standar Skripsi:
   - Judul, Abstrak (analisis panjang kata & kata kunci),
   - Bab I (Pendahuluan: latar belakang, rumusan masalah, tujuan, manfaat),
   - Bab II (Tinjauan Pustaka / Landasan Teori / Kerangka Berpikir),
   - Bab III (Metode Penelitian),
   - Bab IV (Hasil dan Pembahasan),
   - Bab V (Kesimpulan dan Saran / Penutup),
   - Daftar Pustaka.
3. Pemeriksaan EBI / PUEBI / KBBI Akademik:
   - Pemisahan kata depan 'di' vs imbuhan 'di-' (cth: 'di lakukan' -> 'dilakukan', 'didalam' -> 'di dalam').
   - Kamus 150+ kata tidak baku akademik umum (cth: 'analisa' -> 'analisis', 'hipotesa' -> 'hipotesis').
   - Deteksi pleonasme/pemborosan kata (cth: 'adalah merupakan', 'disebabkan karena', 'agar supaya').
   - Deteksi kata ganti orang pertama informal (cth: 'saya', 'aku', 'kami', 'kita').
4. Pemeriksaan Keterbacaan & Gaya Akademik:
   - Deteksi kalimat terlalu panjang (> 35 kata).
   - Deteksi paragraf terlalu pendek (1 kalimat) atau terlalu panjang (> 300 kata).
   - Statistik naskah: jumlah kata, jumlah paragraf, estimasi halaman.
5. Perhitungan Skor Kepatuhan Skripsi (0-100) & Rekomendasi Perbaikan.
6. Pembuatan Laporan Audit Word (.docx).
"""

import io
import re
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple

from pypdf import PdfReader
from docx import Document
from docx.shared import Inches, Pt, RGBColor


# =====================================================================
# KAMUS KATA TIDAK BAKU AKADEMIK (KBBI & EBI)
# =====================================================================
KATA_TIDAK_BAKU: Dict[str, str] = {
    "analisa": "analisis",
    "hipotesa": "hipotesis",
    "praktek": "praktik",
    "metodologi": "metode (jika maksudnya cara penelitian)",
    "obyek": "objek",
    "subyek": "subjek",
    "aktifitas": "aktivitas",
    "efektifitas": "efektivitas",
    "produktifitas": "produktivitas",
    "kreatifitas": "kreativitas",
    "sensitifitas": "sensitivitas",
    "kualitatip": "kualitatif",
    "kuantitatip": "kuantitatif",
    "jadwal": "jadwal",
    "jadual": "jadwal",
    "teori": "teori",
    "variable": "variabel",
    "respondent": "responden",
    "signifikan": "signifikan",
    "relevansi": "relevansi",
    "hirarki": "hierarki",
    "hirarkis": "hierarkis",
    "kategori": "kategori",
    "kwalitas": "kualitas",
    "kwantitas": "kuantitas",
    "frekuensi": "frekuensi",
    "prosentase": "persentase",
    "prosentasi": "persentase",
    "persen": "persen",
    "sekedar": "sekadar",
    "merubah": "mengubah",
    "merobah": "mengubah",
    "merinci": "memerinci",
    "mempraktekkan": "mempraktikkan",
    "mempersilahkan": "mempersilakan",
    "mensosialisasikan": "menyosialisasikan",
    "menterjemahkan": "menerjemahkan",
    "mentargetkan": "menargetkan",
    "mengkaji": "mengaji (atau menelaah)",
    "memfokuskan": "memfokuskan",
    "mempengaruhi": "memengaruhi",
    "mentolerir": "menoleransi",
    "mensyaratkan": "memsyaratkan / mensyaratkan",
    "mentransfer": "mentransfer",
    "standarisasi": "standardisasi",
    "legitimasi": "legitimasi",
    "kongkrit": "konkret",
    "konkrit": "konkret",
    "faham": "paham",
    "fikir": "pikir",
    "berfikir": "berpikir",
    "memikirkan": "memikirkan",
    "azas": "asas",
    "ijazah": "ijazah",
    "ijasah": "ijazah",
    "ijin": "izin",
    "resiko": "risiko",
    "sistematik": "sistematika / sistematis",
    "sistimatik": "sistematis",
    "substansi": "substansi",
    "komprehensip": "komprehensif",
    "deskriptip": "deskriptif",
    "positip": "positif",
    "negatip": "negatif",
    "motifasi": "motivasi",
    "inisiatip": "inisiatif",
    "inovatif": "inovatif",
    "pasip": "pasif",
    "produktip": "produktif",
    "relatip": "relatif",
    "kolektip": "kolektif",
    "efektip": "efektif",
    "obyektifitas": "objektivitas",
    "subyektifitas": "subjektivitas",
    "valid": "sahih / valid",
    "relyabel": "andal / reliabel",
    "akurasi": "keakuratan / akurasi",
    "antri": "antre",
    "atlit": "atlet",
    "apotik": "apotek",
    "cidera": "cedera",
    "debet": "debit",
    "detail": "detail / terperinci",
    "dimana": "di mana (tempat) / tempat (bukan kata sambung)",
    "disamping itu": "di samping itu",
    "didepan": "di depan",
    "dibelakang": "di belakang",
    "didalam": "di dalam",
    "diluar": "di luar",
    "diatas": "di atas",
    "dibawah": "di bawah",
    "disini": "di sini",
    "disitu": "di situ",
    "disana": "di sana",
    "disebelah": "di sebelah",
    "antar muka": "antarmuka",
    "tata bahasa": "tatabahasa",
    "kerja sama": "kerja sama (terpisah)",
    "kerjasama": "kerja sama",
    "tanda tangan": "tanda tangan",
    "tandatangan": "tanda tangan",
    "terimakasih": "terima kasih",
    "kacamata": "kacamata",
    "pasca sarjana": "pascasarjana",
    "sub bab": "subbab",
    "non formal": "nonformal",
    "multi disiplin": "multidisiplin",
    "semi konduktor": "semikonduktor",
    "beritahu": "beri tahu",
    "hakekat": "hakikat",
    "karir": "karier",
    "kolega": "kolega",
    "komplit": "lengkap / komplit",
    "nomer": "nomor",
    "parafrase": "parafrasa",
    "pedoman": "pedoman",
    "pondasi": "fondasi",
    "ramadhan": "ramadan",
    "sederhana": "sederhana",
    "silahkan": "silakan",
    "sintesa": "sintesis",
    "sosialisasi": "sosialisasi",
    "standard": "standar",
    "subjek": "subjek",
    "sumbangsih": "sumbangan / sumbangsih",
    "tarip": "tarif",
    "teladan": "teladan",
    "terlantar": "telantar",
    "terampil": "terampil",
    "trampil": "terampil",
    "terpercaya": "tepercaya",
    "terlanjur": "tlanjur / telanjur",
    "telenjur": "telanjur",
    "zaman": "zaman",
    "jaman": "zaman",
}

# PLEONASME / KATA BERLEBIHAN
FRASA_PLEONASME: Dict[str, str] = {
    "adalah merupakan": "merupakan (atau 'adalah')",
    "disebabkan karena": "disebabkan oleh (atau 'karena')",
    "agar supaya": "agar (atau 'supaya')",
    "seperti contohnya": "seperti (atau 'misalnya')",
    "demi untuk": "demi (atau 'untuk')",
    "amat sangat": "sangat",
    "sangat sekali": "sangat",
    "hanya ... saja": "hanya (atau 'saja')",
    "para hadirin": "hadirin",
    "banyak berbagai": "berbagai",
    "mulai sejak": "sejak (atau 'mulai')",
    "tujuan daripada": "tujuan dari",
    "terdiri dari": "terdiri atas",
    "berdasarkan atas": "berdasarkan pada (atau 'berdasarkan')",
    "bertujuan untuk": "bertujuan",
}

# KATA GANTI ORANG PERTAMA TIDAK FORMAL
KATA_ORANG_PERTAMA = {"saya", "aku", "kami", "kita", "penulis", "peneliti"}

# DAFTAR KATA KERJA PASIF UMUM (untuk cek salah pisah 'di ')
KATA_DASAR_PASIF = {
    "lakukan", "gunakan", "teliti", "analisis", "buat", "temukan", "dapatkan",
    "hasilkan", "jelaskan", "simpulkan", "sajikan", "kembangkan", "uji", "ukur",
    "hitung", "amati", "kumpulkan", "terapkan", "bandingkan", "tentukan", "bahas",
    "rumuskan", "identifikasi", "laksanakan", "capai", "butuhkan", "harapkan",
    "pilih", "susun", "bimbing", "tulis", "tinjau", "definisikan", "kaji",
}


def ekstrak_teks_dari_pdf(pdf_bytes: bytes) -> str:
    """Mengekstrak seluruh teks dari berkas PDF."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        paragraf = []
        for hal in reader.pages:
            t = hal.extract_text() or ""
            if t.strip():
                paragraf.append(t.strip())
        return "\n\n".join(paragraf)
    except Exception as e:
        raise ValueError(f"Gagal membaca berkas PDF: {e}")


def ekstrak_teks_dari_docx(docx_bytes: bytes) -> str:
    """Mengekstrak seluruh teks paragraf dari berkas DOCX."""
    try:
        doc = Document(io.BytesIO(docx_bytes))
        paragraf = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraf)
    except Exception as e:
        raise ValueError(f"Gagal membaca berkas Word (.docx): {e}")


def ekstrak_teks_dari_file(isi_bytes: bytes, nama_berkas: str = "") -> str:
    """Mengekstrak teks otomatis berdasarkan ekstensi atau magic header berkas."""
    nama = nama_berkas.lower()
    if nama.endswith(".pdf") or isi_bytes[:4] == b"%PDF":
        return ekstrak_teks_dari_pdf(isi_bytes)
    if nama.endswith(".docx") or isi_bytes[:2] == b"PK":
        return ekstrak_teks_dari_docx(isi_bytes)
    # Teks biasa / txt
    try:
        return isi_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return isi_bytes.decode("latin-1", errors="ignore")


# =====================================================================
# 1. PEMERIKSAAN SITASI & DAFTAR PUSTAKA (CROSS-CHECK)
# =====================================================================

def ekstrak_sitasi_in_text(teks: str) -> List[Dict[str, Any]]:
    """Mendeteksi sitasi dalam teks (dalam kurung maupun naratif)."""
    sitasi_ditemukan: List[Dict[str, Any]] = []

    # Pola 1: Tanda kurung, contoh: (Sugiyono, 2020), (Hidayat & Rahayu, 2021, hlm. 45), (Smith et al., 2019)
    pola_kurung = re.finditer(
        r"\(([A-Z][a-zA-Z\s\.\&\,\-]+?(?:et\sal\.|dkk\.)?)[,\s]+(19\d\d|20\d\d)(?:[,\s]+(?:hlm\.|hal\.|p\.|pp\.)?\s*[\d\-–]+)?\)",
        teks
    )
    for m in pola_kurung:
        penulis_mentah = m.group(1).strip()
        tahun = m.group(2)
        # Saring kata yang bukan nama penulis (misal nama bab, singkatan umum)
        if any(w in penulis_mentah.lower() for w in ["tabel", "gambar", "lampiran", "grafik", "pasal"]):
            continue
        # Ambil nama keluarga pertama
        nama_kunci = _ekstrak_nama_kunci(penulis_mentah)
        if nama_kunci and len(nama_kunci) > 1:
            sitasi_ditemukan.append({
                "teks_asli": m.group(0),
                "penulis": penulis_mentah,
                "nama_kunci": nama_kunci,
                "tahun": tahun,
                "tipe": "dalam_kurung",
                "posisi": m.start(),
            })

    # Pola 2: Sitasi naratif, contoh: Sugiyono (2020), Menurut Pratama dan Wijaya (2021)
    pola_naratif = re.finditer(
        r"\b([A-Z][a-zA-Z]+(?:\s+(?:dan|&)\s+[A-Z][a-zA-Z]+)?(?:\s+(?:et\sal\.|dkk\.))?)\s*\((19\d\d|20\d\d)\)",
        teks
    )
    for m in pola_naratif:
        penulis_mentah = m.group(1).strip()
        tahun = m.group(2)
        if any(w in penulis_mentah.lower() for w in ["tabel", "gambar", "lampiran", "grafik", "bab"]):
            continue
        nama_kunci = _ekstrak_nama_kunci(penulis_mentah)
        if nama_kunci and len(nama_kunci) > 1:
            sitasi_ditemukan.append({
                "teks_asli": m.group(0),
                "penulis": penulis_mentah,
                "nama_kunci": nama_kunci,
                "tahun": tahun,
                "tipe": "naratif",
                "posisi": m.start(),
            })

    # Pola 3: Sitasi numerik IEEE, contoh: [1], [2, 3], [4-7]
    pola_ieee = re.finditer(r"\[(\d+(?:\s*[\,\-–]\s*\d+)*)\]", teks)
    for m in pola_ieee:
        sitasi_ditemukan.append({
            "teks_asli": m.group(0),
            "penulis": f"Referensi {m.group(0)}",
            "nama_kunci": m.group(0),
            "tahun": "",
            "tipe": "ieee",
            "posisi": m.start(),
        })

    return sitasi_ditemukan


def _ekstrak_nama_kunci(teks_penulis: str) -> str:
    """Mengambil nama belakang/kunci dari string penulis."""
    t = re.sub(r"\b(et\sal\.|dkk\.|dan|\&)\b", " ", teks_penulis, flags=re.I)
    t = re.sub(r"[^a-zA-Z\s]", " ", t)
    kata = [k for k in t.split() if len(k) > 1 and not k.isupper() or len(k) > 2]
    return kata[0].lower() if kata else ""


def pisahkan_bagian_daftar_pustaka(teks: str) -> Tuple[str, str]:
    """Memisahkan bagian isi tubuh naskah dan bagian Daftar Pustaka."""
    pola_dp = re.search(
        r"(?:\n\s*|^)(?:BAB\s+[IVXLCDM]+\s*\n)?\s*(DAFTAR\s+PUSTAKA|REFERENCES|BIBLIOGRAPHY|DAFTAR\s+RUJUKAN)\s*(?:\n|$)",
        teks,
        flags=re.I
    )
    if pola_dp:
        pos = pola_dp.start()
        naskah = teks[:pos]
        daftar_pustaka = teks[pos:]
        return naskah, daftar_pustaka
    return teks, ""


def ekstrak_entri_daftar_pustaka(teks_dp: str) -> List[Dict[str, Any]]:
    """Mengekstrak baris-baris referensi dalam Daftar Pustaka."""
    if not teks_dp.strip():
        return []

    # Bersihkan judul Daftar Pustaka
    baris = [b.strip() for b in teks_dp.splitlines() if b.strip()]
    if baris and re.match(r"^(?:DAFTAR\s+PUSTAKA|REFERENCES|BIBLIOGRAPHY)", baris[0], flags=re.I):
        baris = baris[1:]

    entri_list: List[str] = []
    current_entry = ""

    for b in baris:
        # Ciri awal entri baru: ada nama orang/angka [1] atau hanging indent
        m_awal = re.match(r"^(\[\d+\]|[A-Z][a-zA-Z\.\s\,\-]{2,40}\s*\(\d{4}\)|[A-Z][a-zA-Z\.\s\,\-]{2,40},\s+[A-Z])", b)
        if m_awal and current_entry:
            entri_list.append(current_entry)
            current_entry = b
        elif not current_entry:
            current_entry = b
        else:
            current_entry += " " + b

    if current_entry:
        entri_list.append(current_entry)

    hasil: List[Dict[str, Any]] = []
    for idx, e in enumerate(entri_list, start=1):
        m_th = re.search(r"\b(19\d\d|20\d\d)\b", e)
        tahun = m_th.group(1) if m_th else ""
        # Ambil nama pengarang pertama
        m_nama = re.match(r"^([A-Z][a-zA-Z\.\s\,\-]+?)(?:\(|\.|\,\s*\d{4})", e)
        penulis = m_nama.group(1).strip() if m_nama else e[:30]
        nama_kunci = _ekstrak_nama_kunci(penulis)

        hasil.append({
            "no": idx,
            "teks_lengkap": e,
            "penulis": penulis,
            "nama_kunci": nama_kunci,
            "tahun": tahun,
        })

    return hasil


def audit_sitasi_dan_daftar_pustaka(teks: str) -> Dict[str, Any]:
    """Pemeriksaan silang konsistensi sitasi dalam teks vs daftar pustaka."""
    naskah, teks_dp = pisahkan_bagian_daftar_pustaka(teks)
    sitasi_in_text = ekstrak_sitasi_in_text(naskah)
    entri_dp = ekstrak_entri_daftar_pustaka(teks_dp)

    # 1. Himpunan kunci sitasi unik
    sitasi_unik: Dict[str, Dict[str, Any]] = {}
    for s in sitasi_in_text:
        kunci = f"{s['nama_kunci']}_{s['tahun']}" if s['tahun'] else s['nama_kunci']
        if kunci not in sitasi_unik:
            sitasi_unik[kunci] = {
                "teks_asli": s["teks_asli"],
                "penulis": s["penulis"],
                "nama_kunci": s["nama_kunci"],
                "tahun": s["tahun"],
                "jumlah_kemunculan": 1,
            }
        else:
            sitasi_unik[kunci]["jumlah_kemunculan"] += 1

    # 2. Himpunan kunci daftar pustaka
    dp_kunci: Dict[str, Dict[str, Any]] = {}
    for d in entri_dp:
        kunci = f"{d['nama_kunci']}_{d['tahun']}" if d['tahun'] else d['nama_kunci']
        dp_kunci[kunci] = d

    # 3. Cari sitasi yang HILANG di Daftar Pustaka (Missing in References)
    sitasi_hilang: List[Dict[str, Any]] = []
    sitasi_cocok: List[Dict[str, Any]] = []

    teks_dp_lower = teks_dp.lower()
    for kunci, s in sitasi_unik.items():
        nk = s["nama_kunci"]
        th = s["tahun"]
        # Cek kecocokan kunci langsung atau kemunculan nama + tahun di teks DP
        ada_di_dp = False
        if kunci in dp_kunci:
            ada_di_dp = True
        elif nk and nk in teks_dp_lower and (not th or th in teks_dp_lower):
            ada_di_dp = True

        if ada_di_dp:
            sitasi_cocok.append(s)
        else:
            sitasi_hilang.append(s)

    # 4. Cari entri Daftar Pustaka yang TIDAK PERNAH DIKUTIP (Orphan References)
    teks_naskah_lower = naskah.lower()
    dp_tidak_dikutip: List[Dict[str, Any]] = []
    for d in entri_dp:
        nk = d["nama_kunci"]
        th = d["tahun"]
        kunci = f"{nk}_{th}" if th else nk
        dikutip = False
        if kunci in sitasi_unik:
            dikutip = True
        elif nk and len(nk) > 2 and nk in teks_naskah_lower and (not th or th in teks_naskah_lower):
            dikutip = True

        if not dikutip:
            dp_tidak_dikutip.append(d)

    return {
        "ada_bagian_daftar_pustaka": bool(teks_dp.strip()),
        "total_sitasi_in_text": len(sitasi_in_text),
        "total_sitasi_unik": len(sitasi_unik),
        "total_entri_daftar_pustaka": len(entri_dp),
        "jumlah_sitasi_cocok": len(sitasi_cocok),
        "jumlah_sitasi_hilang": len(sitasi_hilang),
        "jumlah_dp_tidak_dikutip": len(dp_tidak_dikutip),
        "sitasi_hilang": sitasi_hilang,
        "dp_tidak_dikutip": dp_tidak_dikutip,
        "sitasi_cocok": sitasi_cocok[:20],
    }


# =====================================================================
# 2. PEMERIKSAAN STRUKTUR BAB SKRIPSI
# =====================================================================

def audit_struktur_bab(teks: str) -> Dict[str, Any]:
    """Mengecek kelengkapan bab dan sub-bagian standar skripsi/tesis."""
    bab_target = [
        {
            "id": "judul",
            "nama": "Halaman Judul / Cover",
            "wajib": True,
            "regex": r"(?:SKRIPSI|TESIS|DISERTASI|PROPOSAL|LAPORAN\s+AKHIR)",
        },
        {
            "id": "abstrak",
            "nama": "Abstrak / Abstract",
            "wajib": True,
            "regex": r"(?:\n|^)\s*(ABSTRAK|ABSTRACT)\s*(?:\n|$)",
        },
        {
            "id": "bab1",
            "nama": "BAB I — Pendahuluan",
            "wajib": True,
            "regex": r"(?:BAB\s+(?:I|1)\b|PENDAHULUAN)",
            "sub": [
                {"id": "latar_belakang", "nama": "Latar Belakang", "regex": r"Latar\s+Belakang"},
                {"id": "rumusan_masalah", "nama": "Rumusan Masalah / Fokus Penelitian", "regex": r"(Rumusan\s+Masalah|Fokus\s+Penelitian|Pertanyaan\s+Penelitian)"},
                {"id": "tujuan", "nama": "Tujuan Penelitian", "regex": r"Tujuan\s+Penelitian"},
                {"id": "manfaat", "nama": "Manfaat Penelitian", "regex": r"Manfaat\s+Penelitian"},
            ]
        },
        {
            "id": "bab2",
            "nama": "BAB II — Tinjauan Pustaka / Landasan Teori",
            "wajib": True,
            "regex": r"(?:BAB\s+(?:II|2)\b|TINJAUAN\s+PUSTAKA|LANDASAN\s+TEORI|KAJIAN\s+TEORI)",
        },
        {
            "id": "bab3",
            "nama": "BAB III — Metode Penelitian",
            "wajib": True,
            "regex": r"(?:BAB\s+(?:III|3)\b|METODE\s+PENELITIAN|METODOLOGI\s+PENELITIAN)",
            "sub": [
                {"id": "desain", "nama": "Desain / Jenis Penelitian", "regex": r"(Jenis\s+Penelitian|Desain\s+Penelitian|Pendekatan\s+Penelitian)"},
                {"id": "populasi_sampel", "nama": "Populasi / Sampel / Partisipan", "regex": r"(Populasi|Sampel|Partisipan|Sumber\s+Data)"},
                {"id": "analisis_data", "nama": "Teknik Analisis Data", "regex": r"(Analisis\s+Data|Teknik\s+Analisis)"},
            ]
        },
        {
            "id": "bab4",
            "nama": "BAB IV — Hasil dan Pembahasan",
            "wajib": True,
            "regex": r"(?:BAB\s+(?:IV|4)\b|HASIL\s+DAN\s+PEMBAHASAN|HASIL\s+PENELITIAN)",
        },
        {
            "id": "bab5",
            "nama": "BAB V — Kesimpulan dan Saran",
            "wajib": True,
            "regex": r"(?:BAB\s+(?:V|5)\b|PENUTUP|KESIMPULAN\s+DAN\s+SARAN|SIMPULAN)",
        },
        {
            "id": "daftar_pustaka",
            "nama": "Daftar Pustaka / References",
            "wajib": True,
            "regex": r"(DAFTAR\s+PUSTAKA|REFERENCES|BIBLIOGRAPHY)",
        },
    ]

    hasil_bab: List[Dict[str, Any]] = []
    jumlah_ditemukan = 0

    for b in bab_target:
        ada = bool(re.search(b["regex"], teks, flags=re.I))
        if ada:
            jumlah_ditemukan += 1

        sub_hasil = []
        if "sub" in b:
            for s in b["sub"]:
                sub_ada = bool(re.search(s["regex"], teks, flags=re.I))
                sub_hasil.append({
                    "id": s["id"],
                    "nama": s["nama"],
                    "status": "lengkap" if sub_ada else "belum_ada",
                })

        hasil_bab.append({
            "id": b["id"],
            "nama": b["nama"],
            "wajib": b["wajib"],
            "status": "lengkap" if ada else "belum_ada",
            "sub": sub_hasil,
        })

    # Analisis khusus Abstrak (jumlah kata & kata kunci)
    analisis_abstrak = None
    m_abs = re.search(r"(?:\n|^)\s*(ABSTRAK|ABSTRACT)\s*\n+(.*?)(?=\n\s*(?:BAB|DAFTAR|KATA\s+PENGANTAR|ABSTRACT)|\Z)", teks, flags=re.I | re.S)
    if m_abs:
        teks_abstrak = m_abs.group(2).strip()
        kata_abstrak = len(teks_abstrak.split())
        ada_keywords = bool(re.search(r"(Kata\s+Kunci|Keywords?)\s*:", teks_abstrak, flags=re.I))
        analisis_abstrak = {
            "ditemukan": True,
            "jumlah_kata": kata_abstrak,
            "sesuai_standar_panjang": 100 <= kata_abstrak <= 300,
            "ada_kata_kunci": ada_keywords,
            "pesan": (
                "Panjang abstrak ideal (100–250 kata)"
                if 100 <= kata_abstrak <= 250
                else f"Jumlah kata abstrak ({kata_abstrak} kata) di luar rekomendasi standar (100–250 kata)."
            )
        }

    return {
        "total_bab_target": len(bab_target),
        "jumlah_ditemukan": jumlah_ditemukan,
        "persentase_kelengkapan": round((jumlah_ditemukan / len(bab_target)) * 100),
        "daftar_bab": hasil_bab,
        "analisis_abstrak": analisis_abstrak,
    }


# =====================================================================
# 3. PEMERIKSAAN BAHASA, EBI, KBBI, & PLEONASME (RULE-BASED)
# =====================================================================

def audit_bahasa_dan_tata_tulis(teks: str) -> Dict[str, Any]:
    """Pemeriksaan kata tidak baku, salah imbuhan di-, pleonasme, dan POV informal."""
    temuan: List[Dict[str, Any]] = []

    # 1. Cek Kata Tidak Baku KBBI
    for kata_salah, kata_baku in KATA_TIDAK_BAKU.items():
        # Cari kata dengan batas kata (\b)
        pola = re.compile(rf"\b{re.escape(kata_salah)}\b", re.I)
        for m in pola.finditer(teks):
            # Ambil konteks kalimat pendek di sekitar kata
            awal = max(0, m.start() - 40)
            akhir = min(len(teks), m.end() + 40)
            snippet = teks[awal:akhir].replace("\n", " ").strip()

            temuan.append({
                "kategori": "kata_tidak_baku",
                "tingkat": "peringatan",
                "teks_salah": m.group(0),
                "rekomendasi": kata_baku,
                "alasan": f"'{m.group(0)}' tidak baku menurut KBBI. Disarankan menggunakan '{kata_baku}'.",
                "cuplikan": f"… {snippet} …",
                "posisi": m.start(),
            })

    # 2. Cek Kesalahan Penulisan Imbuhan 'di ' (di + spasi + kata kerja pasif)
    # Contoh salah: 'di lakukan', 'di gunakan', 'di teliti'
    for kd in KATA_DASAR_PASIF:
        pola = re.compile(rf"\bdi\s+{kd}\b", re.I)
        for m in pola.finditer(teks):
            awal = max(0, m.start() - 35)
            akhir = min(len(teks), m.end() + 35)
            snippet = teks[awal:akhir].replace("\n", " ").strip()
            bentuk_benar = f"di{kd}"
            temuan.append({
                "kategori": "imbuhan_di_terpisah",
                "tingkat": "peringatan",
                "teks_salah": m.group(0),
                "rekomendasi": bentuk_benar,
                "alasan": f"Imbuhan pasif 'di-' harus dirangkai dengan kata kerja ('{bentuk_benar}'), bukan dipisah.",
                "cuplikan": f"… {snippet} …",
                "posisi": m.start(),
            })

    # 3. Cek Kesalahan Penulisan Kata Depan 'di' (digabung dengan tempat/arah)
    # Contoh salah: 'didalam', 'dimana', 'disekolah', 'didepan'
    KATA_TEMPAT_GABUNG = ["dalam", "luar", "depan", "belakang", "atas", "bawah", "mana", "sini", "situ", "sana"]
    for kt in KATA_TEMPAT_GABUNG:
        pola = re.compile(rf"\bdi{kt}\b", re.I)
        for m in pola.finditer(teks):
            awal = max(0, m.start() - 35)
            akhir = min(len(teks), m.end() + 35)
            snippet = teks[awal:akhir].replace("\n", " ").strip()
            bentuk_benar = f"di {kt}"
            temuan.append({
                "kategori": "kata_depan_di_digabung",
                "tingkat": "peringatan",
                "teks_salah": m.group(0),
                "rekomendasi": bentuk_benar,
                "alasan": f"Kata depan 'di' penunjuk tempat/arah harus ditulis terpisah ('{bentuk_benar}').",
                "cuplikan": f"… {snippet} …",
                "posisi": m.start(),
            })

    # 4. Cek Frasa Pleonasme / Pemborosan Kata
    for frasa_salah, frasa_baku in FRASA_PLEONASME.items():
        pola = re.compile(rf"\b{re.escape(frasa_salah)}\b", re.I)
        for m in pola.finditer(teks):
            awal = max(0, m.start() - 40)
            akhir = min(len(teks), m.end() + 40)
            snippet = teks[awal:akhir].replace("\n", " ").strip()
            temuan.append({
                "kategori": "pleonasme",
                "tingkat": "saran",
                "teks_salah": m.group(0),
                "rekomendasi": frasa_baku,
                "alasan": f"Pleonasme / pemborosan kata. Lebih efektif menggunakan '{frasa_baku}'.",
                "cuplikan": f"… {snippet} …",
                "posisi": m.start(),
            })

    # 5. Cek Penggunaan Kata Ganti Orang Pertama (POV Informal)
    # Catatan: Kata 'penulis' / 'peneliti' diperbolehkan sesekali, tapi 'saya', 'aku', 'kami' dilarang dalam skripsi formal.
    for pov in ["saya", "aku", "kami", "kita"]:
        pola = re.compile(rf"\b{pov}\b", re.I)
        for m in pola.finditer(teks):
            awal = max(0, m.start() - 35)
            akhir = min(len(teks), m.end() + 35)
            snippet = teks[awal:akhir].replace("\n", " ").strip()
            temuan.append({
                "kategori": "pov_informal",
                "tingkat": "saran",
                "teks_salah": m.group(0),
                "rekomendasi": "peneliti / bentuk pasif",
                "alasan": f"Kata ganti orang '{m.group(0)}' kurang lazim dalam ragam ilmiah baku. Gunakan konstruksi kalimat pasif atau sebut 'peneliti'.",
                "cuplikan": f"… {snippet} …",
                "posisi": m.start(),
            })

    # Urutkan temuan berdasarkan posisi dalam naskah
    temuan.sort(key=lambda x: x["posisi"])

    ringkasan_kategori: Dict[str, int] = {}
    for t in temuan:
        k = t["kategori"]
        ringkasan_kategori[k] = ringkasan_kategori.get(k, 0) + 1

    return {
        "total_temuan": len(temuan),
        "ringkasan_kategori": ringkasan_kategori,
        "daftar_temuan": temuan[:100],  # Batasi 100 temuan pertama agar respons cepat & tidak berat
    }


# =====================================================================
# 4. PEMERIKSAAN KETERBACAAN & STRUKTUR KALIMAT
# =====================================================================

def audit_keterbacaan(teks: str) -> Dict[str, Any]:
    """Memeriksa panjang kalimat, paragraf, dan statistik naskah."""
    paragraf_list = [p.strip() for p in teks.splitlines() if len(p.strip()) > 10]
    total_kata = len(teks.split())

    # Pisahkan kalimat
    kalimat_list = re.split(r"(?<=[.!?])\s+", teks)
    kalimat_list = [k.strip() for k in kalimat_list if len(k.strip()) > 5]

    kalimat_terlalu_panjang: List[Dict[str, Any]] = []
    for k in kalimat_list:
        kata = k.split()
        if len(kata) > 35:
            kalimat_terlalu_panjang.append({
                "panjang_kata": len(kata),
                "cuplikan": (k[:160] + "…") if len(k) > 160 else k,
                "saran": "Kalimat ini memiliki lebih dari 35 kata. Sebaiknya dipecah menjadi 2–3 kalimat agar alur penalaran lebih jernih dan mudah dipahami dosen penguji.",
            })

    # Paragraf yang hanya 1 kalimat (paragraf tunggal yang kurang elaboratif)
    paragraf_satu_kalimat: List[str] = []
    for p in paragraf_list:
        if 15 <= len(p.split()) <= 40 and p.count(".") == 1 and not p.startswith(("#", "-", "*", "1", "2")):
            paragraf_satu_kalimat.append(p[:120] + "…")

    rerata_kata_per_kalimat = round(total_kata / max(1, len(kalimat_list)), 1)
    estimasi_halaman = round(total_kata / 300, 1)  # Asumsi 300 kata per halaman A4 font 12 spasi 1.5

    return {
        "total_kata": total_kata,
        "total_kalimat": len(kalimat_list),
        "total_paragraf": len(paragraf_list),
        "estimasi_halaman": estimasi_halaman,
        "rerata_kata_per_kalimat": rerata_kata_per_kalimat,
        "jumlah_kalimat_panjang": len(kalimat_terlalu_panjang),
        "kalimat_terlalu_panjang": kalimat_terlalu_panjang[:15],
        "paragraf_satu_kalimat": paragraf_satu_kalimat[:5],
    }


# =====================================================================
# 5. PERHITUNGAN SKOR AKHIR & LAPORAN AUDIT LENGKAP
# =====================================================================

def periksa_skripsi_lengkap(teks: str, nama_berkas: str = "") -> Dict[str, Any]:
    """Menjalankan seluruh rangkaian audit skripsi non-AI."""
    if not teks or len(teks.strip()) < 50:
        raise ValueError("Teks naskah terlalu pendek untuk diperiksa (minimal 50 karakter).")

    audit_sit = audit_sitasi_dan_daftar_pustaka(teks)
    audit_bab = audit_struktur_bab(teks)
    audit_bah = audit_bahasa_dan_tata_tulis(teks)
    audit_ket = audit_keterbacaan(teks)

    # PERHITUNGAN SKOR KEPATUHAN (0 - 100)
    # Nilai dasar 100 dikurangi penalti:
    skor = 100.0

    # 1. Penalti Sitasi Hilang (kritis: -4 poin per sitasi hilang, maks -30)
    penalti_sitasi_hilang = min(30.0, audit_sit["jumlah_sitasi_hilang"] * 4.0)
    skor -= penalti_sitasi_hilang

    # 2. Penalti DP Tidak Dikutip (-2 poin per entri, maks -15)
    penalti_dp_kosong = min(15.0, audit_sit["jumlah_dp_tidak_dikutip"] * 2.0)
    skor -= penalti_dp_kosong

    # 3. Penalti Struktur Bab yang Hilang (-5 poin per bab wajib, maks -25)
    bab_kurang = sum(1 for b in audit_bab["daftar_bab"] if b["wajib"] and b["status"] != "lengkap")
    penalti_bab = min(25.0, bab_kurang * 5.0)
    skor -= penalti_bab

    # 4. Penalti EBI & Kata Baku (-0.5 poin per temuan, maks -20)
    penalti_bahasa = min(20.0, audit_bah["total_temuan"] * 0.5)
    skor -= penalti_bahasa

    # 5. Penalti Kalimat Terlalu Panjang (-1 poin per kalimat > 35 kata, maks -10)
    penalti_kalimat = min(10.0, audit_ket["jumlah_kalimat_panjang"] * 1.0)
    skor -= penalti_kalimat

    skor_akhir = max(10, min(100, round(skor)))

    # Kategori Predikat Skor
    if skor_akhir >= 85:
        predikat = "Sangat Baik (Siap Sidang)"
        warna_predikat = "emerald"
    elif skor_akhir >= 70:
        predikat = "Cukup Baik (Perlu Sedikit Perbaikan)"
        warna_predikat = "indigo"
    elif skor_akhir >= 50:
        predikat = "Perlu Revisi Menengah"
        warna_predikat = "amber"
    else:
        predikat = "Perlu Banyak Perbaikan"
        warna_predikat = "rose"

    return {
        "nama_berkas": nama_berkas or "Draf_Skripsi.txt",
        "skor": skor_akhir,
        "predikat": predikat,
        "warna_predikat": warna_predikat,
        "ringkasan_penalti": {
            "sitasi_hilang": penalti_sitasi_hilang,
            "dp_tidak_dikutip": penalti_dp_kosong,
            "bab_kurang": penalti_bab,
            "bahasa_dan_ebi": penalti_bahasa,
            "kalimat_panjang": penalti_kalimat,
        },
        "audit_sitasi": audit_sit,
        "audit_struktur": audit_bab,
        "audit_bahasa": audit_bah,
        "audit_keterbacaan": audit_ket,
    }


# =====================================================================
# 6. PEMBUATAN LAPORAN WORD (.DOCX) HASIL AUDIT SKRIPSI
# =====================================================================

def buat_laporan_audit_docx(hasil: Dict[str, Any]) -> bytes:
    """Menghasilkan berkas Word rapi berisi laporan lengkap audit skripsi."""
    doc = Document()

    # Margin 1 inch
    for s in doc.sections:
        s.top_margin = Inches(1)
        s.bottom_margin = Inches(1)
        s.left_margin = Inches(1)
        s.right_margin = Inches(1)

    # Header / Judul
    h1 = doc.add_heading(level=1)
    run_h1 = h1.add_run("Laporan Hasil Audit Kepatuhan Skripsi")
    run_h1.font.name = "Calibri"
    run_h1.font.size = Pt(20)
    run_h1.font.bold = True
    run_h1.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    sub = doc.add_paragraph()
    r_sub = sub.add_run(f"Naskah: {hasil.get('nama_berkas', 'Draf Skripsi')} | Dihasilkan secara otomatis oleh Referensia Skripsi Checker (100% Non-AI & Deterministik)")
    r_sub.font.size = Pt(9.5)
    r_sub.font.italic = True
    r_sub.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    # Kotak Skor
    p_skor = doc.add_paragraph()
    r_skor_lbl = p_skor.add_run("SKOR KELAYAKAN NASKAH: ")
    r_skor_lbl.font.bold = True
    r_skor_lbl.font.size = Pt(14)
    r_skor_val = p_skor.add_run(f"{hasil.get('skor', 0)} / 100 ({hasil.get('predikat', '')})\n")
    r_skor_val.font.bold = True
    r_skor_val.font.size = Pt(16)
    r_skor_val.font.color.rgb = RGBColor(0x05, 0x96, 0x69) if hasil.get('skor', 0) >= 70 else RGBColor(0xDC, 0x26, 0x26)

    ket = hasil.get("audit_keterbacaan", {})
    r_stat = p_skor.add_run(f"Total Kata: {ket.get('total_kata', 0)} · Estimasi Halaman: {ket.get('estimasi_halaman', 0)} hlm · Rata-rata Kata/Kalimat: {ket.get('rerata_kata_per_kalimat', 0)}")
    r_stat.font.size = Pt(10)
    r_stat.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

    doc.add_paragraph("—" * 45)

    # 1. BAGIAN SITASI VS DAFTAR PUSTAKA
    h2_sit = doc.add_heading(level=2)
    h2_sit.add_run("1. Audit Sitasi & Daftar Pustaka").font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    sit = hasil.get("audit_sitasi", {})
    p_sit_sum = doc.add_paragraph()
    p_sit_sum.add_run(f"• Total Sitasi dalam Teks: {sit.get('total_sitasi_unik', 0)} unik ({sit.get('total_sitasi_in_text', 0)} kemunculan)\n")
    p_sit_sum.add_run(f"• Total Entri di Daftar Pustaka: {sit.get('total_entri_daftar_pustaka', 0)} entri\n")
    p_sit_sum.add_run(f"• Sitasi Cocok: {sit.get('jumlah_sitasi_cocok', 0)}\n")

    r_sit_hilang = p_sit_sum.add_run(f"• Sitasi HILANG di Daftar Pustaka: {sit.get('jumlah_sitasi_hilang', 0)} (Kritis!)\n")
    if sit.get('jumlah_sitasi_hilang', 0) > 0:
        r_sit_hilang.font.bold = True
        r_sit_hilang.font.color.rgb = RGBColor(0xDC, 0x26, 0x26)

    r_dp_kosong = p_sit_sum.add_run(f"• Referensi Daftar Pustaka TIDAK PERNAH DIKUTIP: {sit.get('jumlah_dp_tidak_dikutip', 0)}\n")
    if sit.get('jumlah_dp_tidak_dikutip', 0) > 0:
        r_dp_kosong.font.color.rgb = RGBColor(0xD9, 0x77, 0x06)

    if sit.get("sitasi_hilang"):
        doc.add_paragraph().add_run("Daftar Sitasi yang belum tercantum di Daftar Pustaka:").font.bold = True
        for sh in sit["sitasi_hilang"][:15]:
            p_sh = doc.add_paragraph(style="List Bullet")
            p_sh.add_run(f"{sh['teks_asli']} ({sh['jumlah_kemunculan']}x dikutip)")

    # 2. BAGIAN STRUKTUR BAB
    doc.add_paragraph("—" * 45)
    h2_bab = doc.add_heading(level=2)
    h2_bab.add_run("2. Kelengkapan Struktur Bab Skripsi").font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    strk = hasil.get("audit_struktur", {})
    p_strk_sum = doc.add_paragraph()
    p_strk_sum.add_run(f"Kelengkapan Bab: {strk.get('persentase_kelengkapan', 0)}% ({strk.get('jumlah_ditemukan', 0)} dari {strk.get('total_bab_target', 0)} bagian ditemukan)")

    for b in strk.get("daftar_bab", []):
        p_b = doc.add_paragraph(style="List Bullet")
        r_b_status = p_b.add_run("[✓] " if b["status"] == "lengkap" else "[X] ")
        r_b_status.font.bold = True
        r_b_status.font.color.rgb = RGBColor(0x05, 0x96, 0x69) if b["status"] == "lengkap" else RGBColor(0xDC, 0x26, 0x26)
        p_b.add_run(b["nama"])

    # 3. BAGIAN TATA TULIS & EBI
    doc.add_paragraph("—" * 45)
    h2_bah = doc.add_heading(level=2)
    h2_bah.add_run("3. Kaidah Tata Bahasa, KBBI, & EBI").font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    bah = hasil.get("audit_bahasa", {})
    p_bah_sum = doc.add_paragraph()
    p_bah_sum.add_run(f"Total Temuan Kesalahan Bahasa: {bah.get('total_temuan', 0)} temuan\n")

    for t in bah.get("daftar_temuan", [])[:20]:
        p_t = doc.add_paragraph(style="List Bullet")
        r_salah = p_t.add_run(f"'{t['teks_salah']}' → Rekomendasi: '{t['rekomendasi']}'\n")
        r_salah.font.bold = True
        p_t.add_run(f"Alasan: {t['alasan']}\n")
        r_cn = p_t.add_run(f"Konteks: {t['cuplikan']}")
        r_cn.font.italic = True
        r_cn.font.size = Pt(9)

    # 4. BAGIAN KETERBACAAN
    if ket.get("kalimat_terlalu_panjang"):
        doc.add_paragraph("—" * 45)
        h2_ket = doc.add_heading(level=2)
        h2_ket.add_run("4. Kalimat yang Terlalu Panjang (> 35 Kata)").font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

        for kp in ket["kalimat_terlalu_panjang"][:8]:
            p_kp = doc.add_paragraph(style="List Bullet")
            p_kp.add_run(f"Panjang: {kp['panjang_kata']} kata\n").font.bold = True
            r_kc = p_kp.add_run(f'"{kp["cuplikan"]}"')
            r_kc.font.italic = True
            r_kc.font.size = Pt(9.5)

    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()
