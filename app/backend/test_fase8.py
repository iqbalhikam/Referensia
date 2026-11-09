"""Tes offline Fase 8: mode browser — backend menyajikan hasil npm run build."""
import os
import tempfile
import unittest
from pathlib import Path

import server


class TestCariDirUI(unittest.TestCase):
    def test_folder_dari_argumen(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "index.html").write_text("<html></html>", encoding="utf-8")
            self.assertEqual(server._cari_dir_ui(tmp), Path(tmp).resolve())

    def test_bukan_folder_ui_dilewati(self):
        with tempfile.TemporaryDirectory() as tmp:
            hasil = server._cari_dir_ui(tmp)
        # bukan index.html → bukan pakai argumen; kalaupun ada, paling fallback app/dist
        self.assertNotEqual(hasil, Path(tmp).resolve())

    def test_variabel_lingkungan(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "index.html").write_text("<html></html>", encoding="utf-8")
            lama = os.environ.get("REFERENSIA_UI")
            os.environ["REFERENSIA_UI"] = tmp
            try:
                self.assertEqual(server._cari_dir_ui(""), Path(tmp).resolve())
            finally:
                if lama is None:
                    os.environ.pop("REFERENSIA_UI", None)
                else:
                    os.environ["REFERENSIA_UI"] = lama


class TestPasangUI(unittest.TestCase):
    def test_mount_terakhir_sehingga_api_menang(self):
        from starlette.routing import Mount
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "index.html").write_text("<html></html>", encoding="utf-8")
            server.pasang_ui(Path(tmp))
        terakhir = server.app.routes[-1]
        self.assertIsInstance(terakhir, Mount)
        self.assertEqual(terakhir.name, "ui")
        jalur_api = [getattr(r, "path", "") for r in server.app.routes[:-1]]
        self.assertIn("/api/health", jalur_api)


if __name__ == "__main__":
    unittest.main()
