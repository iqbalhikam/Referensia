"""Tes offline Fase 7: PRISMA, tren & gap, laporan tinjauan."""
import os
import tempfile
import unittest

from docx import Document

import server
from referensia import engine
from test_fase4 import ref


def konteks(**kw):
    dasar = {"topik": "tes", "topik_id": "tes", "topik_en": "test", "topik_en_skor": "test",
             "jenis": "Semua", "saring_predator": True}
    dasar.update(kw)
    ctx = engine.Konteks(**dasar)
    ctx.kat_kini = "Nasional"
    return ctx


class TestPrisma(unittest.TestCase):
    def test_hitung_tahap(self):
        ctx = konteks()
        recs = [
            ref(1, uid="a"),
            ref(1, uid="a"),  # uid sama -> duplikat
            ref(1, uid="b", judul="Judul penelitian nomor 1"),  # judul sama -> duplikat
            ref(2, uid="c", penerbit="Academic Journals Inc"),  # predator
            ref(3, uid="d", judul="Pendek"),  # judul terlalu pendek, tidak dihitung duplikat
        ]
        pool = {}
        engine.tambah_ke_pool(pool, recs, ctx)
        self.assertEqual(len(pool), 1)
        self.assertEqual(ctx.stat["ditarik"]["Nasional"], 5)
        self.assertEqual(ctx.stat["duplikat"]["Nasional"], 2)
        self.assertEqual(ctx.stat["predator"]["Nasional"], 1)

        hasil = {"Nasional": [ref(1), ref(2)], "Internasional": []}
        ctx.stat["dinilai"]["Nasional"] = {"a", "b"}
        prisma = engine.buat_prisma(hasil, {"Nasional": {"a": 1, "b": 1, "c": 1}}, ctx.stat)
        n = prisma["per_kategori"]["Nasional"]
        self.assertEqual((n["kandidat"], n["dinilai"], n["masuk"], n["ditolak"]), (3, 2, 2, 0))
        self.assertEqual(n["tanpa_pdf"], 2)
        self.assertEqual(prisma["ditarik"], 5)
        self.assertEqual(prisma["masuk"], 2)

    def test_tabel_prisma_tujuh_baris(self):
        prisma = {"per_kategori": {"Nasional": {"ditarik": 9, "duplikat": 3, "predator": 1,
                                                "kandidat": 5, "dinilai": 4, "ditolak": 1, "masuk": 3},
                                   "Internasional": {}},
                  "ditarik": 9, "duplikat": 3, "predator": 1, "kandidat": 5,
                  "dinilai": 4, "ditolak": 1, "masuk": 3}
        baris = engine._tabel_prisma({"prisma": prisma})
        self.assertEqual(len(baris), 7)
        self.assertEqual(baris[-1], ("Referensi dimasukkan", 3, 0, 3))


class TestTrenGap(unittest.TestCase):
    def _refs(self):
        return [
            ref(1, tahun=2021, sumber="Jurnal A", abstrak="Penelitian terdahulu membahas literasi digital. "
                 "Namun masih sedikit penelitian yang menguji dampaknya di sekolah menengah."),
            ref(2, tahun=2022, sumber="Jurnal A", abstrak="Studi ini menguji dampak literasi digital. "
                 "Lack of research on rural schools remains a problem."),
            ref(3, tahun=2022, sumber="Jurnal B", abstrak="Pembahasan umum tentang literasi digital."),
            ref(4, tahun=2023, sumber="Jurnal C", abstrak="Kajian literasi digital di kampus negeri."),
            ref(5, tahun=2023, sumber="Jurnal C", abstrak="Analisis kebijakan literasi digital daerah."),
            ref(6, tahun=2023, sumber="Jurnal D", abstrak="Evaluasi program literasi digital kota."),
        ]

    def test_tren_tahun_dan_sumber(self):
        refs = self._refs()
        for r in refs:
            r["kata_cocok"] = ["literasi", "digital"]
        hasil = {"hasil": {"Nasional": refs, "Internasional": []}, "kunci_kat": {"Nasional": ["literasi"]}}
        d = engine.statistik_tren(hasil)
        self.assertEqual([t["tahun"] for t in d["tahun"]], [2021, 2022, 2023])
        self.assertEqual(d["tahun"][1]["Nasional"], 2)
        self.assertEqual(d["sumber"][0], {"nama": "Jurnal A", "jumlah": 2})
        self.assertEqual(d["pendekatan"]["Kuantitatif"], 6)
        self.assertEqual(d["indeks"]["Tidak terdeteksi"], 6)

    def test_gap_dari_abstrak(self):
        hasil = {"hasil": {"Nasional": self._refs(), "Internasional": []}}
        gap = engine.statistik_tren(hasil)["gap"]
        self.assertEqual(len(gap), 2)
        self.assertIn("Namun masih sedikit", gap[0]["teks"])
        self.assertIn("Lack of research", gap[1]["teks"])

    def test_klaster_label(self):
        hasil = {"hasil": {"Nasional": self._refs(), "Internasional": []},
                 "kunci_kat": {"Nasional": ["literasi"]}}
        klaster = engine.statistik_tren(hasil)["klaster"]
        self.assertGreaterEqual(len(klaster), 2)
        self.assertEqual(sum(k["jumlah"] for k in klaster), 6)


class TestLaporan(unittest.TestCase):
    def test_docx_berisi_bagian_penting(self):
        prisma = engine.buat_prisma({"Nasional": [ref(1)], "Internasional": []},
                                    {"Nasional": {"u1": 1}}, konteks().stat)
        result = {"topik": "Literasi Digital", "total": 1,
                  "hasil": {"Nasional": [ref(1)], "Internasional": []},
                  "tema_kat": {"Nasional": ["literasi digital"]},
                  "prisma": prisma, "analisis": {"gap": []}}
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "laporan.docx")
            engine.buat_laporan_docx(result, {"u1": "catatan saya"}, p)
            doc = Document(p)
            teks = "\n".join(x.text for x in doc.paragraphs)
            tabel = "\n".join(c.text for t in doc.tables for row in t.rows for c in row.cells)
        self.assertIn("Laporan Tinjauan Literatur", teks)
        self.assertIn("PRISMA", teks)
        self.assertIn("Referensi dimasukkan", tabel)
        self.assertIn("catatan saya", tabel)
        self.assertIn("Daftar pustaka", teks)

    def test_ringkas_referensi_menyertakan_id_openalex(self):
        d = server._ringkas_referensi(ref(1, id="W123"))
        self.assertEqual(d["id"], "W123")


def _resp(body, status=200):
    from unittest.mock import Mock
    r = Mock(status_code=status)
    r.json.return_value = body
    r.text = "galat"
    return r


class TestJaringan(unittest.TestCase):
    def _hasil(self):
        return {"hasil": {"Nasional": [
            ref(1, id="W1", doi="10.1/a"),
            ref(2, id="W2", doi="10.1/b"),
            ref(3, id="", doi="10.1234/tes.3"),
        ], "Internasional": []}}

    def _sesi(self):
        from unittest.mock import Mock

        def jawab(url, **kw):
            filt = kw["params"]["filter"]
            if filt == "openalex:W1|W2":
                return _resp({"results": [
                    {"id": "https://openalex.org/W1", "title": "A", "doi": "https://doi.org/10.1/a",
                     "cited_by_count": 5, "referenced_works": ["https://openalex.org/W2", "https://openalex.org/W9"]},
                    {"id": "https://openalex.org/W2", "title": "B", "doi": "https://doi.org/10.1/b",
                     "cited_by_count": 9, "referenced_works": ["https://openalex.org/W9"]},
                ]})
            if filt.startswith("doi:"):
                return _resp({"results": [
                    {"id": "https://openalex.org/W3", "title": "C", "doi": "https://doi.org/10.1234/tes.3",
                     "cited_by_count": 1, "referenced_works": ["https://openalex.org/W2"]},
                ]})
            if filt == "openalex:W9":
                return _resp({"results": [{"id": "https://openalex.org/W9", "title": "Karya Luar",
                                           "cited_by_count": 300, "publication_year": 2015}]})
            return _resp({"results": []})

        sesi = Mock()
        sesi.get.side_effect = jawab
        return sesi

    def test_graf_terbentuk(self):
        from unittest import mock
        with mock.patch.object(server.requests, "Session", return_value=self._sesi()):
            d = server.bangun_jaringan(self._hasil())
        self.assertTrue(d["ok"])
        self.assertEqual(len(d["nodes"]), 4)
        ids = {n["id"] for n in d["nodes"]}
        self.assertIn("W9", ids)
        self.assertIn({"source": "W1", "target": "W2"}, d["edges"])
        self.assertIn({"source": "W3", "target": "W2"}, d["edges"])
        self.assertEqual(d["jumlah"]["koneksi"], 4)
        self.assertEqual(d["teratas"][0]["id"], "W2")

    def test_openalex_tidak_mengenali(self):
        from unittest import mock
        hasil = {"hasil": {"Nasional": [ref(1, id="", doi=""), ref(2, id="", doi="")], "Internasional": []}}
        with mock.patch.object(server.requests, "Session", return_value=self._sesi()):
            d = server.bangun_jaringan(hasil)
        self.assertEqual(d["nodes"], [])
        self.assertIn("tidak mengenali", d["catatan"])

    def test_minimal_dua_referensi(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as c:
            server.bangun_jaringan({"hasil": {"Nasional": [ref(1)], "Internasional": []}})
        self.assertEqual(c.exception.status_code, 400)


class TestAI(unittest.TestCase):
    def setUp(self):
        job = server.Job(server.SearchParams(judul_topik="Literasi digital"))
        job.id = "j7"
        job.status = "done"
        job.result = {"topik": "Literasi digital",
                      "hasil": {"Nasional": [ref(1, abstrak="Abstrak pertama yang cukup panjang."),
                                             ref(2, abstrak="Abstrak kedua.")],
                                "Internasional": []}}
        server.JOBS[job.id] = job
        server.PUSTAKA_FILE = None

    def tearDown(self):
        server.JOBS.clear()

    def test_prompt_memuat_tugas_dan_konteks(self):
        msgs = server.prompt_ai(server.JOBS["j7"].result, "bandingkan", "fokus metode")
        teks = msgs[-1]["content"]
        self.assertIn("tabel perbandingan", teks)
        self.assertIn("Literasi digital", teks)
        self.assertIn("Abstrak pertama", teks)
        self.assertIn("fokus metode", teks)

    def test_konteks_dipotong(self):
        teks = server.konteks_ai(server.JOBS["j7"].result, maks_karakter=120)
        self.assertIn("tidak disertakan", teks)

    def test_sukses(self):
        from unittest import mock
        r = _resp({"choices": [{"message": {"content": "Sintesis siap."}}]})
        with mock.patch.object(server.requests, "post", return_value=r) as panggil:
            d = server.asisten_ai(server.AIParams(src="job:j7", key="sk-x", model="gpt-4o-mini"))
        self.assertEqual(d["teks"], "Sintesis siap.")
        self.assertEqual(panggil.call_args.args[0], "https://api.openai.com/v1/chat/completions")

    def test_base_url_lengkap_dinormalkan(self):
        from unittest import mock
        r = _resp({"choices": [{"message": {"content": "ok"}}]})
        with mock.patch.object(server.requests, "post", return_value=r) as panggil:
            server.asisten_ai(server.AIParams(
                src="job:j7", key="sk-x", base_url="https://api.openai.com/v1/chat/completions"))
        self.assertEqual(panggil.call_args.args[0], "https://api.openai.com/v1/chat/completions")

    def test_key_kosong(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as c:
            server.asisten_ai(server.AIParams(src="job:j7", key=" "))
        self.assertEqual(c.exception.status_code, 400)

    def test_base_url_harus_https(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as c:
            server.asisten_ai(server.AIParams(src="job:j7", key="x", base_url="http://localhost:1234/v1"))
        self.assertEqual(c.exception.status_code, 400)

    def test_key_ditolak(self):
        from unittest import mock
        from fastapi import HTTPException
        with mock.patch.object(server.requests, "post", return_value=_resp({}, status=401)):
            with self.assertRaises(HTTPException) as c:
                server.asisten_ai(server.AIParams(src="job:j7", key="salah"))
        self.assertEqual(c.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
