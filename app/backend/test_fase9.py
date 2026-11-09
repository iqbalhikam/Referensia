"""Tes offline Fase 9: pemeriksa rilis GitHub & jalur pasang pembaruan."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

import server
from referensia import pembaruan

TAUTAN = "https://github.com/iqbalhikam/Referensia/releases/download/v1.9.0/Referensia_1.9.0_x64-setup.exe"


class _Resp:
    def __init__(self, payload=None, status=200, url=TAUTAN, potong=b"MZ\x90installer"):
        self._p = payload if payload is not None else {}
        self.status_code = status
        self.url = url
        self._potong = potong

    def json(self):
        return self._p

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def iter_content(self, chunk_size=1):
        return iter([self._potong])


class _Sesi:
    def __init__(self, resp):
        self.resp = resp
        self.permintaan = []

    def get(self, url, **kw):
        self.permintaan.append(url)
        return self.resp


RILIS = {
        "tag_name": "v1.9.0",
        "name": "Referensia 1.9.0",
        "body": "  - perbaikan  \n",
        "html_url": "https://github.com/iqbalhikam/Referensia/releases/tag/v1.9.0",
        "published_at": "2026-11-09T10:00:00Z",
        "assets": [
            {"name": "Referensia_1.9.0_x64-setup.exe", "size": 7340032, "browser_download_url": TAUTAN},
            {"name": "sumber.zip", "size": 100, "browser_download_url": "https://github.com/x/sumber.zip"},
            {"name": "palsu.exe", "size": 100, "browser_download_url": "https://evil.example/palsu.exe"},
        ],
    }


class TestVersi(unittest.TestCase):
    def test_tuple(self):
        self.assertEqual(pembaruan.versi_tuple("v1.10.2"), (1, 10, 2))
        self.assertEqual(pembaruan.versi_tuple(" bezebras "), (0,))

    def test_perbandingan(self):
        self.assertTrue(pembaruan.lebih_baru("1.1.0", "1.0.9"))
        self.assertTrue(pembaruan.lebih_baru("1.10", "1.9"))
        self.assertFalse(pembaruan.lebih_baru("1.0.0", "1.0.0"))
        self.assertFalse(pembaruan.lebih_baru("1.9", "1.10"))
        self.assertFalse(pembaruan.lebih_baru("", "1.0.0"))


class TestRilis(unittest.TestCase):
    def test_hanya_aset_exe_dari_github(self):
        d = pembaruan.rilis_terbaru("a/b", _Sesi(_Resp(RILIS)))
        self.assertEqual(d["versi"], "1.9.0")
        self.assertEqual(d["catatan"], "- perbaikan")
        self.assertEqual(d["terbit"], "2026-11-09")
        self.assertEqual([a["nama"] for a in d["aset"]], ["Referensia_1.9.0_x64-setup.exe"])

    def test_belum_ada_rilis(self):
        with self.assertRaises(ValueError) as c:
            pembaruan.rilis_terbaru("a/b", _Sesi(_Resp({}, status=404)))
        self.assertIn("Belum ada rilis", str(c.exception))

    def test_rate_limit(self):
        with self.assertRaises(ValueError) as c:
            pembaruan.rilis_terbaru("a/b", _Sesi(_Resp({}, status=403)))
        self.assertIn("rate limit", str(c.exception))

    def test_tautan_sah(self):
        self.assertTrue(pembaruan.tautan_sah(TAUTAN))
        self.assertTrue(pembaruan.tautan_sah("https://objects.githubusercontent.com/x/a.exe"))
        self.assertFalse(pembaruan.tautan_sah("http://github.com/x/a.exe"))
        self.assertFalse(pembaruan.tautan_sah("https://gith evil.com/a.exe"))


class TestUnduh(unittest.TestCase):
    def test_menolak_host_asing(self):
        with self.assertRaises(ValueError):
            pembaruan.unduh_installer("https://evil.example/a.exe", tempfile.gettempdir())

    def test_simpan_dan_rapikan(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "lama.exe").write_bytes(b"x")
            d = pembaruan.unduh_installer(TAUTAN, tmp, "Referensia_1.9.0_x64-setup.exe",
                                          sesi=_Sesi(_Resp()))
            self.assertEqual(d["nama"], "Referensia_1.9.0_x64-setup.exe")
            self.assertEqual(Path(d["lokasi"]).read_bytes(), b"MZ\x90installer")
            self.assertFalse((Path(tmp) / "lama.exe").exists())
            self.assertEqual(list(Path(tmp).iterdir()), [Path(d["lokasi"])])

    def test_redirect_keluar_ditolak(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError) as c:
                pembaruan.unduh_installer(TAUTAN, tmp, "a.exe",
                                          sesi=_Sesi(_Resp(url="https://evil.example/a.exe")))
            self.assertIn("dialihkan", str(c.exception))


class TestPengawas(unittest.TestCase):
    def test_jadwalkan_butuh_berkas(self):
        with self.assertRaises(ValueError):
            pembaruan.jadwalkan_pasang(Path(tempfile.gettempdir()) / "tidak-ada.exe")

    def test_jadwalkan_mengeluarkan_flag_internal(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "setup.exe"
            exe.write_bytes(b"MZ")
            with mock.patch.object(pembaruan.os, "name", "nt"), \
                 mock.patch.object(pembaruan.subprocess, "Popen") as p:
                pembaruan.jadwalkan_pasang(exe)
            args = p.call_args[0][0]
            self.assertIn("--pasang-setelah-tutup", args)
            self.assertEqual(args[args.index("--pasang-setelah-tutup") + 1], str(exe))
            self.assertIn("--aplikasi", args)

    def test_pasang_setelah_tutup(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "setup.exe"
            exe.write_bytes(b"MZ")
            with mock.patch.object(pembaruan, "aplikasi_berjalan", side_effect=[True, True, False]), \
                 mock.patch.object(pembaruan.time, "sleep"), \
                 mock.patch.object(pembaruan.subprocess, "Popen") as p:
                self.assertEqual(pembaruan.pasang_setelah_tutup(exe), 0)
            self.assertEqual(p.call_args[0][0], [str(exe)])

    def test_berkas_hilang_ditangani(self):
        self.assertEqual(pembaruan.pasang_setelah_tutup(Path(tempfile.gettempdir()) / "raib.exe"), 1)


class TestEndpoint(unittest.TestCase):
    def setUp(self):
        self.awal = dict(server._CACHE_RILIS)
        server._CACHE_RILIS.update({"data": None, "kapan": 0.0, "galat": ""})

    def tearDown(self):
        server._CACHE_RILIS.update(self.awal)

    def test_cek_update(self):
        with mock.patch.object(pembaruan, "rilis_terbaru", return_value=pembaruan.rilis_terbaru("a/b", _Sesi(_Resp(RILIS)))):
            d = server.cek_update(True)
        self.assertTrue(d["ada_baru"])
        self.assertEqual(d["versi_sekarang"], server.VERSI_APP)
        self.assertEqual(d["rilis"]["aset"][0]["nama"], "Referensia_1.9.0_x64-setup.exe")

    def test_cache_dipakai_tanpa_paksa(self):
        with mock.patch.object(pembaruan, "rilis_terbaru", return_value={"versi": "1.0.0", "aset": []}) as r:
            server.cek_update(True)
            server.cek_update()
            server.cek_update()
        self.assertEqual(r.call_count, 1)

    def test_galat_dibungkus(self):
        with mock.patch.object(pembaruan, "rilis_terbaru", side_effect=ValueError("rate limit nih")):
            with self.assertRaises(HTTPException) as c:
                server.cek_update(True)
        self.assertEqual(c.exception.status_code, 502)
        self.assertIn("rate limit", c.exception.detail)

    def test_unduh_hanya_aset_rilis(self):
        d = pembaruan.rilis_terbaru("a/b", _Sesi(_Resp(RILIS)))
        server._CACHE_RILIS["data"] = d
        with self.assertRaises(HTTPException) as c:
            server.unduh_pembaruan(server.UnduhPembaruanParams(url="https://evil.example/a.exe"))
        self.assertEqual(c.exception.status_code, 400)

    def test_unduh_meneruskan_nama_aset(self):
        d = pembaruan.rilis_terbaru("a/b", _Sesi(_Resp(RILIS)))
        server._CACHE_RILIS["data"] = d
        with mock.patch.object(pembaruan, "unduh_installer", return_value={"lokasi": "x", "nama": "y", "ukuran": 1}) as u:
            server.unduh_pembaruan(server.UnduhPembaruanParams(url=TAUTAN))
        self.assertEqual(u.call_args[0][2], "Referensia_1.9.0_x64-setup.exe")

    def test_pasang_tolak_luar_folder(self):
        with self.assertRaises(HTTPException) as c:
            server.pasang_pembaruan(server.PasangPembaruanParams(lokasi=str(Path.home() / "licik.exe")))
        self.assertEqual(c.exception.status_code, 400)

    def test_pasang_menyerahkan_ke_pengawas(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            folder = Path(tmp) / "pembaruan"
            folder.mkdir()
            exe = folder / "setup.exe"
            exe.write_bytes(b"MZ")
            try:
                with mock.patch.object(pembaruan, "jadwalkan_pasang", return_value=True) as j:
                    d = server.pasang_pembaruan(server.PasangPembaruanParams(lokasi=str(exe)))
                self.assertTrue(d["ok"])
                self.assertEqual(j.call_args[0][0], exe)
            finally:
                os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
