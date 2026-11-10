"""Pengujian fitur Pencari Halaman Sitasi (Citation Page Finder)."""

import unittest
from referensia.halaman_sitasi import (
    parse_ris_text,
    _norm_teks_pencarian,
    pindai_halaman_kutipan_pdf,
    format_sitasi_halaman,
    buat_ris_terupdate,
    buat_rekap_halaman_docx,
)


SAMPLE_RIS = """
TY  - JOUR
TI  - Efektivitas Pembelajaran Berbasis Masalah terhadap Keterampilan Abad 21
AU  - Hidayat, Taufik
AU  - Rahayu, Sri
PY  - 2023
JO  - Jurnal Inovasi Pendidikan
VL  - 11
IS  - 1
SP  - 45
EP  - 58
DO  - 10.23887/jip.v11i1.500
UR  - https://ejournal.undiksha.ac.id/index.php/JIP/article/view/500
ER  - 

TY  - JOUR
TI  - Artificial Intelligence in Higher Education: A Systematic Review
AU  - Johnson, Mark
AU  - Davis, Karen
PY  - 2021
JO  - International Journal of Educational Technology
VL  - 8
IS  - 2
DO  - 10.1186/s41239-021-00260-1
ER  - 
"""


class TestHalamanSitasi(unittest.TestCase):
    def test_parse_ris_multiple_records(self):
        items = parse_ris_text(SAMPLE_RIS)
        self.assertEqual(len(items), 2)

        it1 = items[0]
        self.assertEqual(it1["judul"], "Efektivitas Pembelajaran Berbasis Masalah terhadap Keterampilan Abad 21")
        self.assertEqual(it1["tahun"], "2023")
        self.assertEqual(it1["volume"], "11")
        self.assertEqual(it1["issue"], "1")
        self.assertEqual(it1["sp"], "45")
        self.assertEqual(it1["ep"], "58")
        self.assertEqual(it1["halaman_ada"], "45–58")
        self.assertEqual(it1["status_halaman"], "lengkap")

        it2 = items[1]
        self.assertEqual(it2["judul"], "Artificial Intelligence in Higher Education: A Systematic Review")
        self.assertEqual(it2["tahun"], "2021")
        self.assertEqual(it2["sp"], "")
        self.assertEqual(it2["ep"], "")
        self.assertEqual(it2["status_halaman"], "belum_ada")

    def test_norm_teks_pencarian(self):
        teks = "Model Pem- belajaran Berbasis MASALAH (PBL)!"
        norm = _norm_teks_pencarian(teks)
        self.assertIn("pembelajaran", norm)
        self.assertIn("masalah", norm)
        self.assertNotIn("!", norm)

    def test_format_sitasi_halaman(self):
        items = parse_ris_text(SAMPLE_RIS)
        sitasi1 = format_sitasi_halaman(items[0], halaman_jurnal="52")
        self.assertIn("Hidayat & Rahayu", sitasi1["intext_apa"])
        self.assertIn("hlm. 52", sitasi1["intext_apa"])
        self.assertIn("[1, p. 52]", sitasi1["intext_ieee"])
        self.assertIn("Jurnal Inovasi Pendidikan", sitasi1["daftar_pustaka_apa"])

    def test_buat_ris_terupdate(self):
        items = parse_ris_text(SAMPLE_RIS)
        # Update record 2 dengan halaman baru
        items[1]["sp"] = "110"
        items[1]["ep"] = "125"
        teks_ris = buat_ris_terupdate(items)
        self.assertIn("SP  - 110", teks_ris)
        self.assertIn("EP  - 125", teks_ris)
        self.assertIn("ER  -", teks_ris)

    def test_buat_rekap_halaman_docx(self):
        items = parse_ris_text(SAMPLE_RIS)
        docx_bytes = buat_rekap_halaman_docx(items, query_kutipan="pembelajaran abad 21")
        self.assertGreater(len(docx_bytes), 1000)
        self.assertTrue(docx_bytes.startswith(b"PK"))  # Format zip DOCX


if __name__ == "__main__":
    unittest.main()
