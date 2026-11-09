"""Tes offline Fase 4: matriks/Word/Excel, snowballing, Zotero, pustaka lokal."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from referensia import engine
import server


def ref(no=1, **kw):
    dasar = {
        "uid": f"u{no}", "no": no, "skor": 70, "kategori": "Nasional",
        "judul": f"Judul penelitian nomor {no}", "penulis": ["Budi Santoso", "Siti Aminah"],
        "tahun": 2023, "jenis": "article", "sumber": "Jurnal Pendidikan Indonesia",
        "penerbit": "Universitas Contoh", "doi": f"10.1234/tes.{no}", "abstrak": "",
        "apa": f"Santoso, B., & Aminah, S. (2023). Judul penelitian nomor {no}. Jurnal Pendidikan Indonesia.",
        "ieee": f"[{no}] B. Santoso and S. Aminah, \"Judul penelitian nomor {no},\" Jurnal Pendidikan Indonesia, 2023.",
        "hasil_utama": "Hasil menunjukkan peningkatan signifikan.",
        "metode": {"pendekatan": "Kuantitatif", "desain": "Survei", "sampel": "100 mahasiswa",
                   "analisis": ["regresi"], "instrumen": ["kuesioner"]},
    }
    dasar.update(kw)
    return dasar


class TestHasilUtama(unittest.TestCase):
    def test_kosong(self):
        self.assertEqual(engine.hasil_utama(""), "")
        self.assertEqual(engine.hasil_utama(None), "")

    def test_pilih_kalimat_hasil(self):
        ab = ("Media sosial dipakai luas oleh mahasiswa di berbagai kampus. "
              "Hasil penelitian menunjukkan pengaruh signifikan terhadap prestasi belajar. "
              "Data dikumpulkan selama satu semester penuh.")
        self.assertIn("Hasil penelitian menunjukkan", engine.hasil_utama(ab))

    def test_tanpa_kata_kunci(self):
        ab = "Ini kalimat pembuka yang panjang sekali tentang latar belakang masalah penelitian ini."
        self.assertEqual(engine.hasil_utama(ab), "")


class TestDocx(unittest.TestCase):
    def test_apa_hanging_indent(self):
        from docx import Document
        from docx.shared import Cm
        rows = [ref(1), ref(2)]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "apa.docx")
            engine.buat_docx(rows, "apa", p)
            doc = Document(p)
            self.assertEqual(len(doc.paragraphs), 2)
            self.assertEqual(doc.paragraphs[0].text, rows[0]["apa"])
            pf = doc.paragraphs[0].paragraph_format
            self.assertEqual(pf.left_indent, Cm(1.27))
            self.assertEqual(pf.first_line_indent, Cm(-1.27))
            self.assertEqual(doc.styles["Normal"].font.name, "Times New Roman")

    def test_ieee(self):
        from docx import Document
        rows = [ref(1)]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "ieee.docx")
            engine.buat_docx(rows, "ieee", p)
            self.assertEqual(Document(p).paragraphs[0].text, rows[0]["ieee"])


class TestMatriksXlsx(unittest.TestCase):
    def test_isi_dan_header(self):
        from openpyxl import load_workbook
        rows = [ref(1), ref(2, kategori="Internasional")]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "matriks.xlsx")
            engine.buat_matriks_xlsx(rows, p)
            wb = load_workbook(p)
            ws = wb["Matriks Literatur"]
            header = [c.value for c in ws[1]]
            for kolom in ("No", "Kategori", "Pendekatan", "Desain", "Sampel",
                          "Teknik Analisis", "Instrumen", "Hasil Utama", "Sitasi APA"):
                self.assertIn(kolom, header)
            self.assertEqual(ws.max_row, 3)
            self.assertEqual(ws.cell(row=2, column=header.index("Hasil Utama") + 1).value,
                             rows[0]["hasil_utama"])
            self.assertEqual(ws.cell(row=3, column=header.index("Kategori") + 1).value, "Internasional")


class TestZoteroItem(unittest.TestCase):
    def test_struktur(self):
        it = engine.zotero_item(ref(1))
        self.assertEqual(it["itemType"], "journalArticle")
        self.assertEqual(it["title"], "Judul penelitian nomor 1")
        self.assertEqual(it["DOI"], "10.1234/tes.1")
        self.assertEqual(it["creators"][0], {"creatorType": "author", "lastName": "Santoso", "firstName": "Budi"})
        tags = [t["tag"] for t in it["tags"]]
        self.assertIn("Nasional", tags)
        self.assertIn("Referensia", tags)

    def test_jenis_buku(self):
        self.assertEqual(engine.zotero_item(ref(1, jenis="book"))["itemType"], "book")
        self.assertEqual(engine.zotero_item(ref(1, jenis="dissertation"))["itemType"], "thesis")


class FakeResp:
    status_code = 200

    def json(self):
        return {"results": [{"id": "W999"}]}


class TestSnowball(unittest.TestCase):
    def _ctx(self):
        return engine.Konteks(topik="tes", topik_id="tes", topik_en="test", api_key="", email="",
                              jenis="Semua", tahun_dari=0, tahun_sampai=0, wajib_doi=False)

    def test_tarik_tetangga(self):
        ctx = self._ctx()
        pool = {"a": {"id": "W1", "skor": 90}, "b": {"id": "W2", "skor": 80}}
        with mock.patch.object(engine, "SESI") as sesi, \
             mock.patch.object(engine, "rapikan_openalex", side_effect=lambda w: {"uid": w["id"], "judul": "x"}):
            sesi.get.return_value = FakeResp()
            hasil = engine.snowball_tarik(ctx, pool)
        self.assertEqual(len(hasil), 4)  # 2 seed x (cites + cited_by)
        filter_dipakai = [c.kwargs["params"]["filter"] for c in sesi.get.call_args_list]
        self.assertTrue(any(f.startswith("cites:W1,") for f in filter_dipakai))
        self.assertTrue(any(f.startswith("cited_by:W2,") for f in filter_dipakai))

    def test_seed_bukan_openalex_dilewati(self):
        ctx = self._ctx()
        pool = {"a": {"id": "doi:10.1/x", "skor": 90}}
        with mock.patch.object(engine, "SESI") as sesi:
            hasil = engine.snowball_tarik(ctx, pool)
        self.assertEqual(hasil, [])
        sesi.get.assert_not_called()

    def test_openalex_mati(self):
        ctx = self._ctx()
        ctx.openalex_mati = True
        with mock.patch.object(engine, "SESI") as sesi:
            self.assertEqual(engine.snowball_tarik(ctx, {"a": {"id": "W1", "skor": 90}}), [])
        sesi.get.assert_not_called()


class TestPustakaServer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        server.PUSTAKA_FILE = Path(self.tmp.name) / "pustaka.json"
        server.JOBS.clear()

    def tearDown(self):
        server.PUSTAKA_FILE = None

    def _job(self, jid="abc123"):
        job = server.Job(server.SearchParams(judul_topik="tes topik"))
        job.id = jid
        job.status = "done"
        job.zip_path = os.path.join(self.tmp.name, "hasil.zip")
        job.folder = self.tmp.name
        job.result = {
            "topik": "tes topik", "topik_id": "tes topik", "topik_en": "test topic",
            "target": {"Nasional": 1, "Internasional": 0},
            "hasil": {"Nasional": [server._ringkas_referensi(ref(1))], "Internasional": []},
            "catatan": [], "kunci_kat": {}, "tema_kat": {},
            "jumlah_pdf": 1, "total": 1, "durasi_detik": 10, "zip_name": "hasil.zip",
        }
        return job

    def test_simpan_dan_baca(self):
        job = self._job()
        server._simpan_riwayat(job)
        entries = server._baca_pustaka()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["id"], "abc123")
        self.assertEqual(entries[0]["result"]["total"], 1)
        e = server._entri("abc123")
        self.assertEqual(e["topik"], "tes topik")

    def test_simpan_dua_kali_tidak_duplikat(self):
        job = self._job()
        server._simpan_riwayat(job)
        server._simpan_riwayat(job)
        self.assertEqual(len(server._baca_pustaka()), 1)

    def test_ringkas_bawa_uid_kategori_hasil(self):
        r = server._ringkas_referensi(ref(1))
        self.assertEqual(r["uid"], "u1")
        self.assertEqual(r["kategori"], "Nasional")
        self.assertEqual(r["hasil_utama"], "Hasil menunjukkan peningkatan signifikan.")

    def test_favorit_toggle(self):
        server._simpan_riwayat(self._job())
        server.toggle_favorit(server.FavParams(lib_id="abc123", uid="u1", on=True))
        self.assertEqual(server._entri("abc123")["favorit"], ["u1"])
        server.toggle_favorit(server.FavParams(lib_id="abc123", uid="u1", on=True))
        self.assertEqual(server._entri("abc123")["favorit"], ["u1"])
        server.toggle_favorit(server.FavParams(lib_id="abc123", uid="u1", on=False))
        self.assertEqual(server._entri("abc123")["favorit"], [])

    def test_refs_dari_lib(self):
        server._simpan_riwayat(self._job())
        result, zp, folder, lib_id = server._refs_dari("lib:abc123")
        self.assertEqual(lib_id, "abc123")
        self.assertEqual(len(server._semua_refs(result)), 1)
        self.assertEqual(folder, self.tmp.name)

    def test_refs_dari_job(self):
        job = self._job("job999")
        server.JOBS[job.id] = job
        result, _, _, lib_id = server._refs_dari("job:job999")
        self.assertEqual(lib_id, "job999")
        self.assertEqual(result["topik"], "tes topik")

    def test_hapus(self):
        server._simpan_riwayat(self._job())
        server.hapus_pustaka("abc123")
        self.assertEqual(server._baca_pustaka(), [])

    def test_favorit_global(self):
        server._simpan_riwayat(self._job())
        server.toggle_favorit(server.FavParams(lib_id="abc123", uid="u1", on=True))
        fav = server.semua_favorit()
        self.assertEqual(len(fav), 1)
        self.assertEqual(fav[0]["refs"][0]["uid"], "u1")


if __name__ == "__main__":
    unittest.main()