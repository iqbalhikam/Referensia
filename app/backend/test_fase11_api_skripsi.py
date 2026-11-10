"""Pengujian endpoint API skripsi checker."""

import unittest
from fastapi import BackgroundTasks
import server
from test_fase11_skripsi_checker import SAMPLE_SKRIPSI


class TestSkripsiCheckerApi(unittest.TestCase):
    def test_check_text_endpoint(self):
        p = server.CheckTextParams(teks=SAMPLE_SKRIPSI, nama_berkas="Sample.txt")
        res = server.endpoint_check_text(p)
        self.assertTrue(res.get("ok"))
        hasil = res.get("hasil", {})
        self.assertIn("skor", hasil)
        self.assertIn("audit_sitasi", hasil)
        self.assertIn("audit_bahasa", hasil)
        self.assertIn("audit_struktur", hasil)

    def test_export_report_endpoint(self):
        p_check = server.CheckTextParams(teks=SAMPLE_SKRIPSI, nama_berkas="Sample.txt")
        res_check = server.endpoint_check_text(p_check)
        hasil = res_check["hasil"]

        bg = BackgroundTasks()
        p_exp = server.ExportReportParams(hasil=hasil)
        res_exp = server.endpoint_export_audit_docx(p_exp, bg)
        self.assertEqual(res_exp.status_code, 200)
        self.assertEqual(
            res_exp.media_type,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


if __name__ == "__main__":
    unittest.main()
