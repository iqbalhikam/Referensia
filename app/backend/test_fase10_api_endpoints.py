"""Pengujian handler endpoint /api/citation-page/*."""

import unittest
from fastapi import BackgroundTasks
import server


SAMPLE_RIS = """TY  - JOUR
TI  - Analisis Model Pembelajaran Abad 21
AU  - Santoso, Joko
PY  - 2022
JO  - Jurnal Ilmu Pendidikan
VL  - 12
IS  - 2
SP  - 101
EP  - 115
DO  - 10.1234/jip.2022.101
ER  - 
"""


class TestCitationPageHandlers(unittest.TestCase):
    def test_parse_ris_handler(self):
        p = server.ParseRisParams(teks_ris=SAMPLE_RIS)
        res = server.endpoint_parse_ris(p)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("total"), 1)
        item = res["items"][0]
        self.assertEqual(item["judul"], "Analisis Model Pembelajaran Abad 21")
        self.assertEqual(item["sp"], "101")
        self.assertEqual(item["ep"], "115")

    def test_export_ris_handler(self):
        item = {
            "judul": "Judul Baru",
            "penulis": ["Santoso, Joko"],
            "tahun": "2023",
            "sp": "200",
            "ep": "215",
            "sumber": "Jurnal Sains",
            "doi": "10.1111/xyz",
        }
        bg = BackgroundTasks()
        p = server.ExportHalamanRisParams(items=[item])
        res = server.endpoint_ekspor_ris(p, bg)
        # FileResponse mengarah ke berkas yang valid
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.media_type, "application/x-research-info-systems")

    def test_export_docx_handler(self):
        item = {
            "judul": "Judul Baru",
            "penulis": ["Santoso, Joko"],
            "tahun": "2023",
            "sp": "200",
            "ep": "215",
            "sumber": "Jurnal Sains",
            "doi": "10.1111/xyz",
            "halaman_rentang": "200–215",
        }
        bg = BackgroundTasks()
        p = server.ExportHalamanDocxParams(items=[item], query_kutipan="uji")
        res = server.endpoint_ekspor_rekap_docx(p, bg)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.media_type,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


if __name__ == "__main__":
    unittest.main()
