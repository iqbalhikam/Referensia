"""Tes offline Fase 6: kirim langsung ke Notion (tanpa memanggil jaringan)."""
import unittest
from unittest import mock
from unittest.mock import Mock

from fastapi import HTTPException

import server
from test_fase4 import ref


class TestPageId(unittest.TestCase):
    def test_dari_url(self):
        url = "https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef?pvs=4"
        self.assertEqual(server._notion_page_id(url), "1234567890abcdef1234567890abcdef")

    def test_dari_id_berdash(self):
        self.assertEqual(server._notion_page_id("12345678-90ab-cdef-1234-567890abcdef"),
                         "1234567890abcdef1234567890abcdef")

    def test_tidak_dikenal(self):
        self.assertEqual(server._notion_page_id("https://www.notion.so/bukan-halaman"), "")
        self.assertEqual(server._notion_page_id(""), "")


def hasil(baris_nasional, baris_internasional=0):
    return {
        "topik": "tes topik", "topik_id": "", "topik_en": "", "target": {},
        "hasil": {
            "Nasional": [server._ringkas_referensi(ref(i + 1)) for i in range(baris_nasional)],
            "Internasional": [server._ringkas_referensi(ref(i + 1)) for i in range(baris_internasional)],
        },
    }


class TestBlok(unittest.TestCase):
    def test_struktur(self):
        blok = server.notion_blocks(hasil(2, 1), {"u1": "catatan penting"})
        jenis = [b["type"] for b in blok]
        self.assertEqual(jenis.count("table"), 2)
        self.assertIn("heading_2", jenis)
        tabel = next(b for b in blok if b["type"] == "table")
        self.assertEqual(tabel["table"]["table_width"], 6)
        self.assertTrue(tabel["table"]["has_column_header"])
        baris = tabel["table"]["children"]
        self.assertEqual(len(baris), 3)  # header + 2 baris
        self.assertEqual(baris[0]["table_row"]["cells"][0][0]["text"]["content"], "No")
        self.assertEqual(baris[1]["table_row"]["cells"][5][0]["text"]["content"], "catatan penting")
        apa = [b for b in blok if b["type"] == "paragraph"]
        self.assertEqual(len(apa), 3)

    def test_pecah_tabel_lebih_40_baris(self):
        blok = server.notion_blocks(hasil(45))
        tabel = [b for b in blok if b["type"] == "table"]
        self.assertEqual(len(tabel), 2)
        self.assertEqual(len(tabel[0]["table"]["children"]), 41)
        self.assertEqual(len(tabel[1]["table"]["children"]), 6)

    def test_potong_blok(self):
        blok = server.notion_blocks(hasil(45))
        potongan = server._potong_blok(blok, maks=90)
        self.assertGreaterEqual(len(potongan), 2)
        for p in potongan:
            berat = sum(1 + (len(b.get("table", {}).get("children", [])) if b["type"] == "table" else 0) for b in p)
            self.assertLessEqual(berat, 90)


class TestEndpoint(unittest.TestCase):
    def setUp(self):
        job = server.Job(server.SearchParams(judul_topik="tes topik"))
        job.id = "j1"
        job.status = "done"
        job.result = hasil(2, 1)
        server.JOBS[job.id] = job
        server.PUSTAKA_FILE = None

    def tearDown(self):
        server.JOBS.clear()

    def _sesi(self, status=200, body=None):
        resp = Mock(status_code=status)
        resp.json.return_value = body or {"id": "page123", "url": "https://notion.so/page123"}
        resp.text = "detail galat"
        sesi = Mock()
        sesi.post.return_value = resp
        return sesi

    def test_kirim_sukses(self):
        sesi = self._sesi()
        with mock.patch.object(server.requests, "Session", return_value=sesi):
            d = server.kirim_notion(server.NotionParams(
                src="job:j1", token="secret_x",
                page="https://www.notion.so/Tes-1234567890abcdef1234567890abcdef"))
        self.assertTrue(d["ok"])
        self.assertEqual(d["url"], "https://notion.so/page123")
        kiriman = sesi.post.call_args.kwargs["json"]
        self.assertEqual(kiriman["parent"], {"page_id": "1234567890abcdef1234567890abcdef"})
        self.assertIn("Matriks Literatur", kiriman["properties"]["title"]["title"][0]["text"]["content"])
        self.assertTrue(kiriman["children"])

    def test_token_kosong(self):
        with self.assertRaises(HTTPException) as c:
            server.kirim_notion(server.NotionParams(src="job:j1", token=" ", page="x"))
        self.assertEqual(c.exception.status_code, 400)

    def test_url_tidak_dikenal(self):
        with self.assertRaises(HTTPException) as c:
            server.kirim_notion(server.NotionParams(src="job:j1", token="s", page="bukan url"))
        self.assertEqual(c.exception.status_code, 400)

    def test_token_ditolak(self):
        sesi = self._sesi(status=401)
        with mock.patch.object(server.requests, "Session", return_value=sesi):
            with self.assertRaises(HTTPException) as c:
                server.kirim_notion(server.NotionParams(
                    src="job:j1", token="salah", page="1234567890abcdef1234567890abcdef"))
        self.assertEqual(c.exception.status_code, 401)

    def test_halaman_belum_dibagikan(self):
        sesi = self._sesi(status=404)
        with mock.patch.object(server.requests, "Session", return_value=sesi):
            with self.assertRaises(HTTPException) as c:
                server.kirim_notion(server.NotionParams(
                    src="job:j1", token="x", page="1234567890abcdef1234567890abcdef"))
        self.assertEqual(c.exception.status_code, 404)

    def test_job_tidak_ada(self):
        with self.assertRaises(HTTPException):
            server.kirim_notion(server.NotionParams(
                src="job:tidakada", token="x", page="1234567890abcdef1234567890abcdef"))


def _sesi_verif(status_me=200, status_cari=200):
    resp_me = Mock(status_code=status_me)
    resp_me.json.return_value = {"object": "user", "name": "Referensia Bot",
                                 "bot": {"workspace_name": "Ruang Riset"}}
    resp_me.text = "detail galat"
    resp_cari = Mock(status_code=status_cari)
    resp_cari.json.return_value = {"results": [
        {"object": "page", "archived": False, "url": "https://notion.so/Halaman-A",
         "last_edited_time": "2026-11-01T09:00:00.000Z",
         "properties": {"title": {"type": "title", "title": [{"plain_text": "Halaman A"}]}}},
        {"object": "page", "archived": True, "url": "https://notion.so/Arsip",
         "properties": {}},
        {"object": "database", "url": "https://notion.so/Database"},
    ]}
    resp_cari.text = "galat pencarian"
    sesi = Mock()
    sesi.get.return_value = resp_me
    sesi.post.return_value = resp_cari
    return sesi


class TestVerifikasi(unittest.TestCase):
    def test_sukses_dan_daftar_halaman(self):
        with mock.patch.object(server.requests, "Session", return_value=_sesi_verif()):
            d = server.notion_verify(server.NotionTokenParams(token="secret_x"))
        self.assertTrue(d["ok"])
        self.assertEqual(d["ruang"], "Ruang Riset")
        self.assertEqual(d["bot"], "Referensia Bot")
        self.assertEqual(d["halaman"], [{"judul": "Halaman A", "url": "https://notion.so/Halaman-A",
                                        "terakhir": "2026-11-01"}])
        self.assertEqual(d["catatan"], "")

    def test_token_kosong(self):
        with self.assertRaises(HTTPException) as c:
            server.notion_verify(server.NotionTokenParams(token="  "))
        self.assertEqual(c.exception.status_code, 400)

    def test_token_ditolak(self):
        with mock.patch.object(server.requests, "Session", return_value=_sesi_verif(status_me=401)):
            with self.assertRaises(HTTPException) as c:
                server.notion_verify(server.NotionTokenParams(token="salah"))
        self.assertEqual(c.exception.status_code, 401)

    def test_tanpa_izin_baca(self):
        with mock.patch.object(server.requests, "Session", return_value=_sesi_verif(status_cari=403)):
            d = server.notion_verify(server.NotionTokenParams(token="secret_x"))
        self.assertEqual(d["halaman"], [])
        self.assertIn("Read content", d["catatan"])

    def test_gangguan_jaringan(self):
        sesi = Mock()
        sesi.get.side_effect = server.requests.ConnectionError("putus")
        with mock.patch.object(server.requests, "Session", return_value=sesi):
            with self.assertRaises(HTTPException) as c:
                server.notion_verify(server.NotionTokenParams(token="secret_x"))
        self.assertEqual(c.exception.status_code, 502)


if __name__ == "__main__":
    unittest.main()