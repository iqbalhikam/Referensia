# Referensia

Aplikasi desktop untuk mencari & menata referensi ilmiah otomatis (OpenAlex + Crossref +
Semantic Scholar + Garuda/SINTA), lengkap dengan saringan penerbit predator, deteksi duplikat,
ekspor APA/IEEE, matriks literatur Word/Excel, laporan tinjauan + PRISMA, jaringan sitasi,
peta tren & research gap, dan asisten AI (API key milik sendiri).

Dibangun dari nol tanpa sisa kode/nama notebook sumber lama.

## Dua cara menjalankan

| Cara | Butuh install apa? | Dapat apa |
|---|---|---|
| **Mode browser** (default, paling gampang) | Python 3.12 + Node.js saja — **tidak** perlu Visual Studio C++ Build Tools | Semua fitur, dibuka di browser lewat `http://127.0.0.1:8756` |
| **Installer Tauri** (`.exe`) | Tidak apa-apa di laptopmu — dibangun oleh **GitHub Actions** | Jendela aplikasi native + installer NSIS |

## 1. Mode browser (tanpa MSVC)

```bash
cd app
npm ci
npm run build
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt   # sekali saja, atau pakai venv sendiri
backend/.venv/Scripts/python.exe backend/server.py --open
```

Kalo belum punya virtualenv, cukup:

```bash
cd app && npm ci && npm run build
python backend/server.py --open
```

Backend otomatis menyajikan hasil `npm run build`, jadi satu alamat itu saja yang perlu dibuka.
Flag lain: `--port 8756` (default), `--output "C:\\path\\lain"` (folder hasil), `--no-ui` (API saja).

## 2. Installer Windows lewat GitHub Actions

MSVC Build Tools sudah terpasang di runner `windows-latest`, jadi compile-nya di cloud:

```bash
# dari repo ini, setelah kode masuk GitHub:
git tag v1.0.0
git push origin v1.0.0
```

atau manual: tab **Actions → Build Windows installer → Run workflow**.
Hasilnya: artifact `Referensia-Setup` (dan Release bila di-trigger lewat tag) berupa
`Referensia_1.0.0_x64-setup.exe` — double-click, selesai.

Build lokal (kalo memang mau): perlu Rust + Visual Studio C++ Build Tools + WebView2, lalu
`cd app && npx tauri build --bundles nsis`.

> Rilis harus **publish** (repositori publik atau rilis ditandai publik) supaya
> `api.github.com/repos/.../releases/latest` bisa dibaca tanpa token. Selama repository privat,
> pemeriksaan pembaruan balasannya “belum ada rilis publik” — fitur lain tetap jalan.

## 3. Pembaruan otomatis

- Pertama kali aplikasi dibuka, pengguna ditanya: **aktifkan atau nonaktifkan** pemeriksaan
  pembaruan. Pilihannya disimpan di `localStorage` perangkat dan bisa diubah lewat tombol ⚙️.
- Kalau aktif: satu permintaan ke `api.github.com` tiap aplikasi dibuka (cache 6 jam di backend,
  tanpa identitas, tanpa data penelitian). Bila versi rilis > `VERSI_APP`, muncul spanduk.
- Penginstal **tidak pernah dipasang diam-diam**: user menekan *Unduh penginstal* →
  *Pasang & tutup Referensia*; proses pengawas terpisah menunggu `Referensia.exe` tertutup lalu
  menjalankan penginstal. Berkas hanya diterima dari host GitHub dan harus anggota aset rilis.
- Ganti sumber rilis untuk fork: set env `REFERENSIA_REPO="namauser/repo"`.
- Saat menaikkan versi, samakan tiga tempat: `app/src-tauri/tauri.conf.json`, `app/package.json`,
  dan `VERSI_APP` di `app/backend/server.py` — lalu buat tag `v<versi>`.

## 4. Pengembangan

```bash
cd app
npm run dev           # Vite di :5173, proxy /api ke backend
# terminal lain:
python backend/server.py

# uji offline (tidak menyentuh jaringan):
cd backend && python -m unittest discover -p "test_*.py"
```

## Catatan penting

- **Hasil pencarian** (folder `Referensia_hasil`, ZIP, `pustaka.json`) disimpan di
  `~/Documents/Referensia` — bisa dipindah lewat `--output` atau env `REFERENSIA_OUTPUT`.
- **Key & token tidak pernah ke server Referensia.** Token Notion dan API key AI disimpan di
  `localStorage` perangkat dan dikirim langsung ke `api.notion.com` / penyedia AI pilihanmu
  (OpenAI, DeepSeek, Gemini, OpenRouter).
- **Notion** memakai internal integration, jadi tiap akun Notion perlu tempel token sendiri
  (sekali saja; wizard-nya menampilkan workspace & daftar halaman setelah token dipasang).
- **Jaringan sitasi** pakai OpenAlex; referensi yang DOI-nya tidak dikenali akan dilaporkan lewat
  catatan, bukan dibuat-buat simpulnya.
- Angka **PRISMA** dihitung dari counter pipeline yang sebenarnya, dan **research gap** berupa
  kutipan mentah dari abstrak — periksa manual sebelum masuk skripsi.

## Struktur

```
app/
  backend/            FastAPI + mesin pencarian (referensia/engine.py) + uji offline
  src/                React 19 + Tailwind 4 + Framer Motion
  src-tauri/          shell Tauri v2 (sidecar binaries/referensia-server-*.exe)
  scripts/            build-server-exe.bat (PyInstaller untuk build lokal)
.github/workflows/    build.yml (installer Windows di cloud)
```
