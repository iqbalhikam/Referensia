"""Pemeriksa rilis baru di GitHub dan pemasang pembaruan.

Keputusan "cek otomatis atau tidak" dipegang antarmuka (localStorage perangkat).
Modul ini hanya menyediakan mekanisme: baca rilis terbaru, unduh penginstal
.exe dari GitHub, lalu menjalankannya setelah aplikasi ditutup.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

REPO_DEFAULT = "iqbalhikam/Referensia"
NAMA_APLIKASI = "Referensia.exe"
# Hanya host artefak GitHub — tautan dari sumber lain ditolak.
HOST_SAH = {"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}
_POLASI = re.compile(r"[^A-Za-z0-9._-]+")


def versi_tuple(teks) -> tuple:
    """'v1.10.2' -> (1, 10, 2); tanpa angka -> (0,)."""
    return tuple(int(x) for x in re.findall(r"\d+", str(teks or ""))[:3]) or (0,)


def lebih_baru(terbaru, sekarang) -> bool:
    a, b = versi_tuple(terbaru), versi_tuple(sekarang)
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) > b + (0,) * (n - len(b))


def tautan_sah(url) -> bool:
    u = urlparse(str(url or ""))
    return u.scheme == "https" and u.hostname in HOST_SAH


def rilis_terbaru(repo: str | None = None, sesi=None, timeout: int = 25) -> dict:
    """Ambil rilis resmi terakhir; hanya aset .exe dari host GitHub yang dipakai."""
    repo = (repo or REPO_DEFAULT).strip().strip("/")
    sesi = sesi or requests.Session()
    r = sesi.get(f"https://api.github.com/repos/{repo}/releases/latest", timeout=timeout,
                 headers={"User-Agent": "Referensia", "Accept": "application/vnd.github+json"})
    if r.status_code == 404:
        raise ValueError(f"Belum ada rilis publik di {repo} (atau repositorinya privat).")
    if r.status_code == 403:
        raise ValueError("GitHub membatasi permintaan (rate limit) — coba lagi beberapa saat.")
    if r.status_code != 200:
        raise ValueError(f"GitHub membalas HTTP {r.status_code} saat memeriksa rilis.")
    d = r.json() or {}
    tag = str(d.get("tag_name") or "")
    aset = []
    for a in d.get("assets") or []:
        nama = _POLASI.sub("_", str(a.get("name") or "")).strip("_") or "Referensia-setup.exe"
        url = str(a.get("browser_download_url") or "")
        if not nama.lower().endswith(".exe") or not tautan_sah(url):
            continue
        aset.append({"nama": nama, "ukuran": int(a.get("size") or 0), "unduh": url})
    return {"versi": tag.lstrip("vV"), "tag": tag, "judul": str(d.get("name") or tag),
            "catatan": str(d.get("body") or "").strip(), "laman": str(d.get("html_url") or ""),
            "terbit": str(d.get("published_at") or "")[:10], "aset": aset}


def unduh_installer(url: str, folder, nama: str = "", sesi=None, batas_mb: int = 500) -> dict:
    """Unduh penginstal ke folder pembaruan; kembalikan lokasi & ukurannya."""
    if not tautan_sah(url):
        raise ValueError("Tautan unduhan bukan dari GitHub — permintaan ditolak.")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    bersih = _POLASI.sub("_", str(nama or urlparse(str(url)).path.rsplit("/", 1)[-1])).strip("_")
    if not bersih.lower().endswith(".exe"):
        bersih = (bersih or "Referensia-setup") + ".exe"
    sementara = folder / (bersih + ".part")
    sesi = sesi or requests.Session()
    try:
        with sesi.get(url, stream=True, timeout=180) as r:
            if r.status_code != 200:
                raise ValueError(f"GitHub menolak permintaan unduhan (HTTP {r.status_code}).")
            if not tautan_sah(r.url):        # redirect keluar dari GitHub -> hentikan
                raise ValueError("Unduhan dialihkan keluar dari GitHub — permintaan dihentikan.")
            ukuran = 0
            with open(sementara, "wb") as fh:
                for potong in r.iter_content(chunk_size=65536):
                    ukuran += len(potong)
                    if ukuran > batas_mb * 1024 * 1024:
                        raise ValueError("Berkas penginstal melebihi ukuran wajar — unduhan dibatalkan.")
                    fh.write(potong)
        tujuan = folder / bersih
        os.replace(sementara, tujuan)
    finally:
        if sementara.exists():
            sementara.unlink(missing_ok=True)
    for lama in folder.glob("*.exe"):        # simpan hanya penginstal terbaru
        if lama != tujuan:
            lama.unlink(missing_ok=True)
    return {"lokasi": str(tujuan), "nama": bersih, "ukuran": ukuran}


def aplikasi_berjalan(nama: str) -> bool:
    try:
        k = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {nama}", "/NH"],
                           capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return False
    return str(nama).lower() in (k.stdout or "").lower()


def _argv_watcher() -> list[str]:
    """Perintah untuk menjalankan ulang sisi backend sebagai pengawas terpisah."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, str(Path(__file__).resolve().parent.parent / "server.py")]


def jadwalkan_pasang(installer, aplikasi: str = NAMA_APLIKASI) -> bool:
    """Lepaskan proses pengawas: tunggu aplikasi tertutup, baru jalankan penginstal."""
    installer = Path(str(installer))
    if not installer.is_file() or installer.suffix.lower() != ".exe":
        raise ValueError("Berkas penginstal tidak ditemukan.")
    if os.name != "nt":
        raise ValueError("Pemasangan otomatis hanya tersedia di Windows.")
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen(
        _argv_watcher() + ["--pasang-setelah-tutup", str(installer), "--aplikasi", aplikasi],
        creationflags=flags, stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True


def pasang_setelah_tutup(installer, aplikasi: str = NAMA_APLIKASI, batas: int = 300) -> int:
    """Dijalankan proses pengawas (bukan server utama): tunggu, lalu pasang."""
    installer = Path(str(installer))
    if not installer.is_file():
        return 1
    akhir = time.time() + batas
    while time.time() < akhir and aplikasi_berjalan(aplikasi):
        time.sleep(1.5)
    try:
        subprocess.Popen([str(installer)])
    except OSError:
        return 1
    return 0
