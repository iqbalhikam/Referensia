"""Unit test untuk fitur Skripsi Checker (100% Non-AI & Rule-Based)."""

import unittest
from referensia.skripsi_checker import (
    ekstrak_sitasi_in_text,
    ekstrak_entri_daftar_pustaka,
    audit_sitasi_dan_daftar_pustaka,
    audit_struktur_bab,
    audit_bahasa_dan_tata_tulis,
    audit_keterbacaan,
    periksa_skripsi_lengkap,
    buat_laporan_audit_docx,
)

SAMPLE_SKRIPSI = """
SKRIPSI MAHASISWA
PENGARUH MODEL PEMBELAJARAN TERHADAP HASIL BELAJAR

ABSTRAK
Penelitian ini bertujuan untuk menganalisis efektivitas model pembelajaran berbasis masalah pada siswa sekolah menengah. Metode yang digunakan adalah kuantitatif deskriptif. Hasil penelitian menunjukkan bahwa terdapat pengaruh yang signifikan antara model pembelajaran dengan hasil belajar.
Kata Kunci: pembelajaran, hasil belajar, siswa.

BAB I PENDAHULUAN
Latar Belakang masalah dalam penelitian ini adalah rendahnya prestasi belajar. Rumusan Masalah dirumuskan untuk mengkaji dampak perlakuan. Tujuan Penelitian adalah mengetahui peningkatan skor. Manfaat Penelitian diharapkan berguna bagi praktisi.

BAB II TINJAUAN PUSTAKA
Menurut Sugiyono (2020), metode penelitian merupakan cara ilmiah untuk mendapatkan data. Pembelajaran berbasis masalah dapat meningkatkan kemampuan siswa (Hidayat & Rahayu, 2021). Penelitian terdahulu oleh Pratama (2019) juga menunjukkan hal serupa. Namun, Widodo (2018) belum tercatat di daftar pustaka.

BAB III METODE PENELITIAN
Jenis Penelitian yang di gunakan adalah eksperimen semu. Populasi dan sampel mencakup 60 siswa. Analisis Data memakai uji statistik regresi.

BAB IV HASIL DAN PEMBAHASAN
Hasil penelitian menunjukkan bahwa hipotesa terbukti. Analisa data di lakukan secara teliti didalam kelas. Banyak siswa yang antusias karena adalah merupakan metode baru. Saya merasa bahwa metode ini sangat cocok diterapkan.

BAB V KESIMPULAN DAN SARAN
Kesimpulan penelitian ini adalah model ini efektif.

DAFTAR PUSTAKA
Hidayat, T., & Rahayu, S. (2021). Pembelajaran Abad 21. Jurnal Pendidikan, 10(2), 45-56.
Pratama, B. (2019). Model Pembelajaran Inovatif. Bandung: Alfabeta.
Sugiyono. (2020). Metode Penelitian Kuantitatif. Bandung: Alfabeta.
Yusuf, A. (2022). Buku Statistik Pendidikan. Jakarta: Kencana.
"""


class TestSkripsiChecker(unittest.TestCase):
    def test_ekstrak_sitasi_in_text(self):
        sitasis = ekstrak_sitasi_in_text(SAMPLE_SKRIPSI)
        self.assertGreaterEqual(len(sitasis), 3)
        nama_list = [s["nama_kunci"] for s in sitasis]
        self.assertIn("sugiyono", nama_list)
        self.assertIn("hidayat", nama_list)
        self.assertIn("pratama", nama_list)
        self.assertIn("widodo", nama_list)

    def test_audit_sitasi_dan_daftar_pustaka(self):
        res = audit_sitasi_dan_daftar_pustaka(SAMPLE_SKRIPSI)
        self.assertTrue(res["ada_bagian_daftar_pustaka"])
        self.assertEqual(res["total_entri_daftar_pustaka"], 4)

        # Widodo (2018) ada di teks tapi tidak ada di Daftar Pustaka -> harus terdeteksi hilang
        nama_hilang = [s["nama_kunci"] for s in res["sitasi_hilang"]]
        self.assertIn("widodo", nama_hilang)

        # Yusuf (2022) ada di Daftar Pustaka tapi tidak pernah dikutip -> harus terdeteksi
        nama_kosong = [d["nama_kunci"] for d in res["dp_tidak_dikutip"]]
        self.assertIn("yusuf", nama_kosong)

    def test_audit_struktur_bab(self):
        res = audit_struktur_bab(SAMPLE_SKRIPSI)
        self.assertGreaterEqual(res["persentase_kelengkapan"], 80)
        status_map = {b["id"]: b["status"] for b in res["daftar_bab"]}
        self.assertEqual(status_map["bab1"], "lengkap")
        self.assertEqual(status_map["bab2"], "lengkap")
        self.assertEqual(status_map["bab3"], "lengkap")
        self.assertEqual(status_map["bab4"], "lengkap")
        self.assertEqual(status_map["bab5"], "lengkap")
        self.assertEqual(status_map["daftar_pustaka"], "lengkap")

    def test_audit_bahasa_dan_tata_tulis(self):
        res = audit_bahasa_dan_tata_tulis(SAMPLE_SKRIPSI)
        self.assertGreater(res["total_temuan"], 0)

        teks_salah = [t["teks_salah"].lower() for t in res["daftar_temuan"]]
        # Cek kata tidak baku: 'analisa' -> 'analisis', 'hipotesa' -> 'hipotesis'
        self.assertIn("analisa", teks_salah)
        self.assertIn("hipotesa", teks_salah)
        # Cek imbuhan 'di ' terpisah: 'di gunakan', 'di lakukan'
        self.assertTrue(any("di gunakan" in s or "di lakukan" in s for s in teks_salah))
        # Cek kata depan 'di' digabung: 'didalam'
        self.assertIn("didalam", teks_salah)
        # Cek pleonasme: 'adalah merupakan'
        self.assertIn("adalah merupakan", teks_salah)
        # Cek POV informal: 'saya'
        self.assertIn("saya", teks_salah)

    def test_periksa_skripsi_lengkap_dan_docx(self):
        hasil = periksa_skripsi_lengkap(SAMPLE_SKRIPSI, "Uji_Skripsi.docx")
        self.assertIn("skor", hasil)
        self.assertGreater(hasil["skor"], 0)
        self.assertLessEqual(hasil["skor"], 100)
        self.assertIn("predikat", hasil)

        # Uji generate laporan Word (.docx)
        docx_bytes = buat_laporan_audit_docx(hasil)
        self.assertTrue(docx_bytes.startswith(b"PK"))
        self.assertGreater(len(docx_bytes), 2000)


if __name__ == "__main__":
    unittest.main()
