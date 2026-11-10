"""Tes offline Fase 5: duplikat lintas riwayat, anotasi, ekspor Markdown."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import Mock

from referensia import engine
import server
from test_fase4 import ref


class TestMetodeDariJudul(unittest.TestCase):
    """Jurnal data-mining sering tanpa abstrak — metode tetap terdeteksi dari judul."""

    def test_knn_dari_judul(self):
        m = engine.ekstrak_metode("", "Penerapan Data Mining untuk Memprediksi Stok Obat "
                                      "Menggunakan Algoritma K-Nearest Neighbors")
        self.assertIn("Data mining/prediktif", m["desain"])
        self.assertIn("KNN", m["analisis"])

    def test_fp_growth_dari_judul(self):
        m = engine.ekstrak_metode("", "Implementasi Data Mining dalam Perencanaan Persediaan Obat "
                                      "Menggunakan Algoritma Frequent Pattern Growth")
        self.assertIn("FP-Growth", m["analisis"])

    def test_regresi_linear_dari_judul(self):
        m = engine.ekstrak_metode("", "Prediksi Penjualan Handphone Menggunakan Algoritma Regresi Linear")
        self.assertIn("Regresi linear", m["analisis"])

    def test_naive_bayes_dari_judul(self):
        m = engine.ekstrak_metode("", "Prediksi Kualitas Air Menggunakan Naive Bayes dan Random Forest")
        self.assertIn("Naive Bayes", m["analisis"])
        self.assertIn("Random Forest", m["analisis"])

    def test_abstrak_tetap_dipakai(self):
        m = engine.ekstrak_metode("Penelitian kuantitatif dengan survei terhadap 120 responden.",
                                  "Judul penelitian lain")
        self.assertEqual(m["pendekatan"], "Kuantitatif")
        self.assertEqual(m["sampel"], "n = 120")

    def test_sampel_transaksi_dataset(self):
        m = engine.ekstrak_metode("Penelitian ini menggunakan dataset sebanyak 540 transaksi.")
        self.assertEqual(m["sampel"], "n = 540")
        self.assertIn("Dataset", m["instrumen"])


class TestLengkapiAbstrak(unittest.TestCase):
    def test_lengkapi_dari_s2(self):
        kosong = ref(1, abstrak="", doi="10.1111/abc")
        ada = ref(2, abstrak="sudah ada", doi="10.2222/def")
        resp = Mock(status_code=200)
        resp.json.return_value = [{"abstract": "Abstrak baru dari S2."}]
        with mock.patch.object(engine, "SESI") as sesi:
            sesi.post.return_value = resp
            n = engine.lengkapi_abstrak_s2([kosong, ada])
        self.assertEqual(n, 1)
        self.assertEqual(kosong["abstrak"], "Abstrak baru dari S2.")
        self.assertEqual(ada["abstrak"], "sudah ada")
        kiriman = sesi.post.call_args.kwargs["json"]["ids"]
        self.assertEqual(kiriman, ["DOI:10.1111/abc"])

    def test_tanpa_doi_tidak_dipanggil(self):
        with mock.patch.object(engine, "SESI") as sesi:
            n = engine.lengkapi_abstrak_s2([ref(1, abstrak="", doi="")])
        self.assertEqual(n, 0)
        sesi.post.assert_not_called()

    def test_gagal_jaringan_aman(self):
        with mock.patch.object(engine, "SESI") as sesi:
            sesi.post.side_effect = RuntimeError("offline")
            n = engine.lengkapi_abstrak_s2([ref(1, abstrak="", doi="10.1/x")])
        self.assertEqual(n, 0)


class TestMatriksDocx(unittest.TestCase):
    def test_tabel_dan_catatan(self):
        from docx import Document
        result = {
            "topik": "tes topik",
            "hasil": {"Nasional": [ref(1)], "Internasional": [ref(2, kategori="Internasional")]},
        }
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "m.docx")
            engine.buat_matriks_docx(result, {"u1": "catatan penting"}, p)
            doc = Document(p)
        self.assertEqual(len(doc.tables), 2)
        t = doc.tables[0]
        self.assertEqual([c.text for c in t.rows[0].cells],
                         ["No", "Judul", "Tahun", "Metode", "Hasil utama", "Catatan"])
        self.assertEqual(t.rows[1].cells[1].text, ref(1)["judul"])
        self.assertEqual(t.rows[1].cells[5].text, "catatan penting")
        self.assertIn("Kuantitatif", t.rows[1].cells[3].text)
        judul = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
        self.assertIn("Matriks Literatur — tes topik", judul)
        self.assertIn("Daftar Pustaka (APA)", judul)


class TestMatriksNomorUrut(unittest.TestCase):
    def test_nomor_berlanjut_lintas_kategori(self):
        from openpyxl import load_workbook
        rows = [ref(1), ref(2), ref(1, kategori="Internasional"), ref(2, kategori="Internasional")]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "m.xlsx")
            engine.buat_matriks_xlsx(rows, p)
            ws = load_workbook(p)["Matriks Literatur"]
            nomor = [ws.cell(row=i, column=1).value for i in range(2, 6)]
        self.assertEqual(nomor, [1, 2, 3, 4])


class TestMarkdown(unittest.TestCase):
    def _result(self):
        return {
            "topik": "tes topik", "topik_id": "tes topik", "topik_en": "test topic",
            "total": 2, "jumlah_pdf": 2,
            "hasil": {"Nasional": [ref(1)], "Internasional": [ref(2, kategori="Internasional")]},
        }

    def test_struktur_dan_tabel(self):
        md = engine.buat_markdown(self._result())
        self.assertIn("# Referensia — tes topik", md)
        self.assertIn("## Nasional (1)", md)
        self.assertIn("## Internasional (1)", md)
        self.assertIn("| No | Judul | Tahun | Metode | Hasil utama | Catatan | DOI |", md)
        self.assertIn("[10.1234/tes.1](https://doi.org/10.1234/tes.1)", md)
        self.assertIn("### Sitasi APA — Nasional", md)
        self.assertIn(ref(1)["apa"], md)

    def test_pipe_di_escape(self):
        r = ref(1, judul="Judul dengan | pipa")
        md = engine.buat_markdown({"topik": "t", "hasil": {"Nasional": [r], "Internasional": []}})
        self.assertIn("Judul dengan \\| pipa", md)

    def test_catatan_masuk(self):
        md = engine.buat_markdown(self._result(), {"u1": "dipakai di bab 2"})
        self.assertIn("dipakai di bab 2", md)

    def test_kolom_kosong_jadi_strip(self):
        r = ref(1, hasil_utama="", metode={})
        md = engine.buat_markdown({"topik": "t", "hasil": {"Nasional": [r], "Internasional": []}})
        self.assertIn("| — |", md)


class TestMatriksCatatan(unittest.TestCase):
    def test_kolom_catatan(self):
        from openpyxl import load_workbook
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "m.xlsx")
            engine.buat_matriks_xlsx([ref(1)], p, {"u1": "catatan penting"})
            ws = load_workbook(p)["Matriks Literatur"]
            header = [c.value for c in ws[1]]
            self.assertIn("Catatan", header)
            self.assertEqual(ws.cell(row=2, column=header.index("Catatan") + 1).value, "catatan penting")


class TestDuplikat(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        server.PUSTAKA_FILE = Path(self.tmp.name) / "pustaka.json"

    def tearDown(self):
        server.PUSTAKA_FILE = None

    def _job(self, jid, refs):
        job = server.Job(server.SearchParams(judul_topik=f"topik {jid}"))
        job.id = jid
        job.status = "done"
        job.result = {
            "topik": f"topik {jid}", "topik_id": "", "topik_en": "",
            "target": {}, "hasil": {"Nasional": [server._ringkas_referensi(r) for r in refs],
                                    "Internasional": []},
            "catatan": [], "kunci_kat": {}, "tema_kat": {},
            "jumlah_pdf": len(refs), "total": len(refs), "durasi_detik": 1, "zip_name": "x.zip",
        }
        return job

    def test_doi_sama_ditandai(self):
        server._simpan_riwayat(self._job("lama", [ref(1, doi="10.1234/ABC")]))
        job_baru = self._job("baru", [ref(9, doi="https://doi.org/10.1234/abc")])
        server._simpan_riwayat(job_baru)
        dup = job_baru.result["hasil"]["Nasional"][0]["duplikat"]
        self.assertIsNotNone(dup)
        self.assertEqual(dup["topik"], "topik lama")

    def test_judul_sama_beda_doi_ditandai(self):
        server._simpan_riwayat(self._job("lama", [ref(1)]))
        job_baru = self._job("baru", [ref(9, doi="10.9999/beda", judul=ref(1)["judul"])])
        server._simpan_riwayat(job_baru)
        self.assertIsNotNone(job_baru.result["hasil"]["Nasional"][0]["duplikat"])

    def test_beda_semua_tidak_ditandai(self):
        server._simpan_riwayat(self._job("lama", [ref(1)]))
        job_baru = self._job("baru", [ref(9, doi="10.9999/beda", judul="Topik yang sama sekali berbeda di sini")])
        server._simpan_riwayat(job_baru)
        self.assertIsNone(job_baru.result["hasil"]["Nasional"][0]["duplikat"])

    def test_pencarian_pertama_bebas_duplikat(self):
        job = self._job("pertama", [ref(1)])
        server._simpan_riwayat(job)
        self.assertIsNone(job.result["hasil"]["Nasional"][0]["duplikat"])

    def test_entri_sendiri_tidak_menandai_ulang(self):
        job = self._job("sama", [ref(1)])
        server._simpan_riwayat(job)
        server._simpan_riwayat(job)
        self.assertIsNone(job.result["hasil"]["Nasional"][0]["duplikat"])


class TestCatatanServer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        server.PUSTAKA_FILE = Path(self.tmp.name) / "pustaka.json"
        job = server.Job(server.SearchParams(judul_topik="tes"))
        job.id = "lib1"
        job.status = "done"
        job.result = {
            "topik": "tes", "topik_id": "", "topik_en": "", "target": {},
            "hasil": {"Nasional": [server._ringkas_referensi(ref(1))], "Internasional": []},
            "catatan": [], "kunci_kat": {}, "tema_kat": {},
            "jumlah_pdf": 1, "total": 1, "durasi_detik": 1, "zip_name": "x.zip",
        }
        server._simpan_riwayat(job)

    def tearDown(self):
        server.PUSTAKA_FILE = None

    def test_simpan_dan_hapus(self):
        server.simpan_catatan(server.NoteParams(lib_id="lib1", uid="u1", teks="dipakai bab 2"))
        self.assertEqual(server._entri("lib1")["catatan"]["u1"], "dipakai bab 2")
        self.assertEqual(server.detail_pustaka("lib1")["catatan"]["u1"], "dipakai bab 2")
        server.simpan_catatan(server.NoteParams(lib_id="lib1", uid="u1", teks="  "))
        self.assertNotIn("u1", server._entri("lib1")["catatan"])

    def test_catatan_di_favorit(self):
        server.toggle_favorit(server.FavParams(lib_id="lib1", uid="u1", on=True))
        server.simpan_catatan(server.NoteParams(lib_id="lib1", uid="u1", teks="keren"))
        fav = server.semua_favorit()
        self.assertEqual(fav[0]["refs"][0]["catatan_pribadi"], "keren")


if __name__ == "__main__":
    unittest.main()