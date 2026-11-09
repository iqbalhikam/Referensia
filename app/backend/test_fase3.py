"""Tes offline Fase 3 (ringkasan, metode, APA/IEEE) — tanpa jaringan."""
import unittest

from referensia import engine


class Ringkasan(unittest.TestCase):
    def test_kosong(self):
        self.assertEqual(engine.ringkas_abstrak("", ["media"]), "")

    def test_pendek_utuh(self):
        ab = "Satu kalimat pendek di sini. Dua kalimat lain di sana."
        self.assertEqual(engine.ringkas_abstrak(ab, ["x"]), ab)

    def test_pilih_relevan_urut_asli(self):
        k1 = "Media sosial menjadi bagian hidup mahasiswa."
        k2 = "Cuaca hari ini cerah sekali di kota besar."
        k3 = "Penelitian ini mengukur pengaruh media sosial terhadap prestasi belajar."
        k4 = "Hasil menunjukkan hubungan negatif antara durasi dan nilai."
        k5 = "Langit berwarna biru dan angin bertiup kencang."
        ab = " ".join([k1, k2, k3, k4, k5])
        out = engine.ringkas_abstrak(ab, ["media", "sosial", "prestasi", "belajar"], maks=3)
        self.assertIn(k3, out)
        self.assertNotIn(k2, out)
        self.assertNotIn(k5, out)
        self.assertLessEqual(len(out.split(". ")), 3)
        self.assertLess(out.find(k1), out.find(k3))  # urutan asli


class Metode(unittest.TestCase):
    def test_indonesia(self):
        ab = ("Penelitian kuantitatif dengan survei terhadap 120 responden menggunakan kuesioner. "
              "Data dianalisis dengan regresi linear berganda.")
        m = engine.ekstrak_metode(ab)
        self.assertEqual(m["pendekatan"], "Kuantitatif")
        self.assertIn("Survei", m["desain"])
        self.assertEqual(m["sampel"], "n = 120")
        self.assertIn("Regresi", m["analisis"])
        self.assertIn("Kuesioner", m["instrumen"])

    def test_inggris(self):
        m = engine.ekstrak_metode("A qualitative case study using interviews and thematic analysis.")
        self.assertEqual(m["pendekatan"], "Kualitatif")
        self.assertIn("Studi kasus", m["desain"])
        self.assertIn("Wawancara", m["instrumen"])
        self.assertIn("Analisis tematik", m["analisis"])

    def test_n_eq(self):
        m = engine.ekstrak_metode("The study employed a survey (n = 45) with regression analysis.")
        self.assertEqual(m["sampel"], "n = 45")

    def test_kosong(self):
        m = engine.ekstrak_metode("")
        self.assertEqual(m["pendekatan"], "")
        self.assertEqual(m["analisis"], [])
        self.assertEqual(engine.teks_metode(m), "-")

    def test_teks_metode(self):
        m = engine.ekstrak_metode("Kuantitatif survei 120 responden regresi kuesioner.")
        self.assertIn(" · ", engine.teks_metode(m))


class Apa(unittest.TestCase):
    def _r(self, **kw):
        d = dict(penulis=["Budi Santoso"], tahun=2020, judul="Pengaruh X.", sumber="Jurnal Pendidikan",
                 doi="10.1/x", jenis="article", penerbit="")
        d.update(kw)
        return d

    def test_satu_penulis(self):
        self.assertEqual(engine.buat_apa(self._r()),
                         "Santoso, B. (2020). Pengaruh X. Jurnal Pendidikan. https://doi.org/10.1/x")

    def test_dua_penulis(self):
        a = engine.buat_apa(self._r(penulis=["Budi Santoso", "Siti Aminah"]))
        self.assertIn("Santoso, B., & Aminah, S.", a)

    def test_tiga_penulis(self):
        a = engine.buat_apa(self._r(penulis=["Budi Santoso", "Siti Aminah", "Agus Wijaya"]))
        self.assertIn("Santoso, B., Aminah, S., & Wijaya, A.", a)

    def test_lebih_20_penulis(self):
        a = engine.buat_apa(self._r(penulis=[f"Nama{i} Belakang{i}" for i in range(25)]))
        self.assertIn("…", a)
        self.assertIn("Belakang24", a)

    def test_tanpa_tahun(self):
        self.assertIn("(t.t.)", engine.buat_apa(self._r(tahun=None)))

    def test_buku(self):
        a = engine.buat_apa(self._r(jenis="book", penerbit="Gramedia", sumber=""))
        self.assertIn("Gramedia.", a)

    def test_nama_dengan_koma(self):
        self.assertEqual(engine.nama_apa("Santoso, Budi"), "Santoso, B.")


class Ieee(unittest.TestCase):
    def test_satu_penulis(self):
        r = dict(penulis=["Budi Santoso"], tahun=2020, judul="Pengaruh X", sumber="Jurnal X", doi="10.1/x")
        self.assertEqual(engine.buat_ieee(r, 1), '[1] B. Santoso, "Pengaruh X," Jurnal X, 2020, doi: 10.1/x.')

    def test_et_al(self):
        r = dict(penulis=[f"N{i} B{i}" for i in range(7)], tahun=2021, judul="T", sumber="", doi="")
        self.assertIn("et al.", engine.buat_ieee(r, 3))
        self.assertTrue(engine.buat_ieee(r, 3).startswith("[3]"))

    def test_tanpa_penulis(self):
        r = dict(penulis=[], tahun=None, judul="T", sumber="", doi="")
        self.assertIn("Anon.", engine.buat_ieee(r, 1))
        self.assertIn("n.d.", engine.buat_ieee(r, 1))


class Laporan(unittest.TestCase):
    def test_memuat_analisis(self):
        r = dict(no=1, skor=80, judul="Tes judul", penulis=["Budi Santoso"], tahun=2024, jenis="article",
                 sumber="Jurnal Tes", doi="10.1/x", sitasi=3, pdf=None, kata_cocok=["tes"],
                 abstrak="Abstrak contoh yang panjang sekali.", ringkasan="Ringkasan contoh.",
                 metode=engine.ekstrak_metode("Kuantitatif survei regresi."),
                 apa="Santoso, B. (2024). Tes judul.", ieee="[1] B. Santoso, \"Tes judul.\"")
        ctx = engine.Konteks(topik="tes topik", topik_id="tes topik", topik_en="test topic")
        html = engine.laporan_html(ctx, {"Nasional": [r], "Internasional": []}, {}, {}, "ringkasan", [])
        self.assertIn("Ringkasan:", html)
        self.assertIn("Ringkasan contoh.", html)
        self.assertIn("Metode:", html)
        self.assertIn("Kuantitatif", html)
        self.assertIn("APA:", html)
        self.assertIn("IEEE:", html)


if __name__ == "__main__":
    unittest.main()