"""Tes offline Fase 2 (DOAJ / SINTA / predator / dedup) — semua HTTP di-mock."""
import unittest
from unittest.mock import patch

from referensia import engine


class Resp:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text

    def json(self):
        return self._json


class FakeSesi:
    def __init__(self, router):
        self.router = router
        self.calls = []

    def get(self, url, params=None, **kw):
        self.calls.append((url, params or {}))
        return self.router(url, params or {})


def rec(uid="1", judul="Judul artikel contoh yang cukup panjang", penerbit="", sumber="",
        issn="", negara=None, bahasa="", skor=50.0):
    return dict(uid=uid, judul=judul, penerbit=penerbit, sumber=sumber, issn=issn,
                negara=negara, bahasa=bahasa, skor=skor, pdf_urls=[], halaman_oa=[], halaman="")


def router_doaj_sinta(url, params):
    if "doaj.org" in url:
        return Resp(200, {"total": 1 if "1234-5678" in url else 0})
    if "sinta." in url:
        return Resp(200, text='<a href="/journals/profile/9">Jurnal Pendidikan Indonesia</a>'
                              '<span class="badge">S2</span>')
    raise AssertionError(f"URL tak terduga: {url}")


class Predator(unittest.TestCase):
    def test_deteksi(self):
        self.assertTrue(engine.terindikasi_predator(rec(penerbit="OMICS International")))
        self.assertTrue(engine.terindikasi_predator(rec(sumber="Global Journals of X")))
        self.assertTrue(engine.terindikasi_predator(rec(penerbit="Scientific Research Publishing")))

    def test_tidak_salah_tangkap(self):
        self.assertFalse(engine.terindikasi_predator(rec(penerbit="Genomics Press")))
        self.assertFalse(engine.terindikasi_predator(rec(penerbit="Elsevier")))
        self.assertFalse(engine.terindikasi_predator(rec(penerbit="MDPI")))


class Pool(unittest.TestCase):
    def test_dedup_uid_dan_judul(self):
        pool = {}
        a = rec(uid="x1", judul="Pengaruh media sosial terhadap prestasi belajar")
        b = rec(uid="x1", judul="Judul lain sama sekali beda")
        c = rec(uid="x2", judul="Pengaruh Media Sosial terhadap Prestasi Belajar!")
        baru = engine.tambah_ke_pool(pool, [a, b, c])
        self.assertEqual(baru, 1)
        self.assertEqual(list(pool), ["x1"])

    def test_filter_predator(self):
        ctx = engine.Konteks(saring_predator=True)
        pool = {}
        bersih = rec(uid="a")
        kotor = rec(uid="b", penerbit="WASET")
        baru = engine.tambah_ke_pool(pool, [bersih, kotor], ctx)
        self.assertEqual(baru, 1)
        self.assertEqual(ctx.predator_disaring, 1)
        self.assertNotIn("b", pool)

    def test_predator_lolos_bila_dimatikan(self):
        ctx = engine.Konteks(saring_predator=False)
        pool = {}
        baru = engine.tambah_ke_pool(pool, [rec(uid="b", penerbit="WASET")], ctx)
        self.assertEqual(baru, 1)
        self.assertEqual(ctx.predator_disaring, 0)


class Doaj(unittest.TestCase):
    def test_cek_dan_cache(self):
        fake = FakeSesi(router_doaj_sinta)
        ctx = engine.Konteks(cek_indeks=True)
        recs = [rec(uid="a", issn="1234-5678"), rec(uid="b", issn="9999-0000"), rec(uid="c")]
        with patch.object(engine, "SESI", fake):
            engine.cek_doaj(ctx, recs)
            self.assertEqual(len(fake.calls), 2)
            engine.cek_doaj(ctx, recs)  # semua sudah di cache
            self.assertEqual(len(fake.calls), 2)
        self.assertTrue(recs[0]["doaj"])
        self.assertFalse(recs[1]["doaj"])
        self.assertFalse(recs[2]["doaj"])


class Sinta(unittest.TestCase):
    def test_hanya_nasional_dan_parse_rank(self):
        fake = FakeSesi(router_doaj_sinta)
        ctx = engine.Konteks(cek_indeks=True)
        recs = [rec(uid="a", sumber="Jurnal Pendidikan Indonesia", negara="ID"),
                rec(uid="b", sumber="Some International Journal", negara="US", bahasa="en")]
        with patch.object(engine, "SESI", fake):
            engine.cek_sinta(ctx, recs)
        self.assertEqual(recs[0]["sinta"], "S2")
        self.assertEqual(recs[1]["sinta"], "")
        self.assertEqual(len(fake.calls), 1)

    def test_gagal_total_jadi_kosong(self):
        fake = FakeSesi(lambda url, params: Resp(500))
        ctx = engine.Konteks(cek_indeks=True)
        recs = [rec(uid="a", sumber="Jurnal X", bahasa="id")]
        with patch.object(engine, "SESI", fake):
            engine.cek_sinta(ctx, recs)
        self.assertEqual(recs[0]["sinta"], "")


class Kualitas(unittest.TestCase):
    def test_bonus_dan_cap(self):
        fake = FakeSesi(router_doaj_sinta)
        ctx = engine.Konteks(cek_indeks=True)
        recs = [rec(uid="a", issn="1234-5678", sumber="Jurnal Pendidikan Indonesia", negara="ID", skor=50.0),
                rec(uid="b", skor=98.0)]
        with patch.object(engine, "SESI", fake):
            engine.cek_kualitas(ctx, recs)
        self.assertEqual(recs[0]["skor"], 58.0)  # +4 DOAJ +4 SINTA
        self.assertEqual(recs[1]["skor"], 98.0)

    def test_cap_100(self):
        fake = FakeSesi(router_doaj_sinta)
        ctx = engine.Konteks(cek_indeks=True)
        recs = [rec(uid="a", issn="1234-5678", sumber="Jurnal Pendidikan Indonesia", negara="ID", skor=97.0)]
        with patch.object(engine, "SESI", fake):
            engine.cek_kualitas(ctx, recs)
        self.assertEqual(recs[0]["skor"], 100.0)

    def test_dimatikan_tanpa_http(self):
        fake = FakeSesi(router_doaj_sinta)
        ctx = engine.Konteks(cek_indeks=False)
        recs = [rec(uid="a", issn="1234-5678")]
        with patch.object(engine, "SESI", fake):
            engine.cek_kualitas(ctx, recs)
        self.assertEqual(len(fake.calls), 0)
        self.assertFalse(recs[0]["doaj"])
        self.assertEqual(recs[0]["sinta"], "")


class Issn(unittest.TestCase):
    def test_rapikan_openalex(self):
        w = {"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1/x", "title": "Tes",
             "primary_location": {"source": {"id": "https://openalex.org/S1", "display_name": "Jurnal Tes",
                                             "issn_l": "1234-5678", "issn": ["1234-5678", "8765-4321"]}}}
        r = engine.rapikan_openalex(w)
        self.assertEqual(r["issn"], "1234-5678")

    def test_rapikan_crossref(self):
        it = {"DOI": "10.1/x", "title": ["Tes"], "ISSN": ["2222-3333"], "type": "journal-article"}
        r = engine.rapikan_crossref(it)
        self.assertEqual(r["issn"], "2222-3333")


class Laporan(unittest.TestCase):
    def test_kolom_indeks(self):
        rows = [dict(no=1, skor=80, judul="Tes", penulis=["A"], sumber="J", tahun=2024,
                     jenis="article", doi="10.1/x", pdf="a.pdf", doaj=True, sinta="S2")]
        html = engine.tabel_html(rows, "#818CF8")
        self.assertIn("Indeks", html)
        self.assertIn("DOAJ", html)
        self.assertIn("SINTA S2", html)


if __name__ == "__main__":
    unittest.main()