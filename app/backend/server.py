"""Referensia Desktop — backend lokal (FastAPI).

Dijalankan oleh Tauri saat aplikasi dibuka, atau manual:
    python server.py [--port 8756] [--open]

Tanpa Tauri (mode browser — cukup Python + Node, tidak perlu MSVC):
    npm run build          # di folder app/, hasilkan app/dist
    python server.py --open    # lalu buka http://127.0.0.1:8756
"""
import argparse
import json
import os
import re
import sys
import tempfile
import threading
import time
import traceback
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path

import requests
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from referensia import jalankan_referensia
from referensia import pembaruan
from referensia.engine import (buat_docx, buat_laporan_docx, buat_matriks_docx, buat_matriks_xlsx,
                               buat_markdown, buat_ris, statistik_tren, zotero_item)

PORT_DEFAULT = 8756
PUSTAKA_FILE: Path | None = None
VERSI_APP = "1.0.3"        # samakan dengan app/tauri.conf.json dan tag release v<versi>
VERSI_API = "1.4"          # penanda build backend — untuk memastikan server tidak kedaluwarsa
REPO_RILIS = os.environ.get("REFERENSIA_REPO", pembaruan.REPO_DEFAULT)
UMUR_CACHE_RILIS = 6 * 3600

app = FastAPI(title="Referensia Desktop API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class SearchParams(BaseModel):
    judul_topik: str = ""
    jumlah_nasional: int = Field(10, ge=0, le=50)
    jumlah_internasional: int = Field(5, ge=0, le=50)
    jenis_referensi: str = "Semua"
    umur_maksimal: int = Field(0, ge=0)
    tahun_dari: int = Field(0, ge=0)
    tahun_sampai: int = Field(0, ge=0)
    wajib_ada_DOI: bool = True
    wajib_ada_PDF: bool = True
    longgarkan_jika_kurang: bool = True
    pakai_google_dorks: bool = True
    saring_predator: bool = True
    cek_indeks: bool = True
    pakai_snowball: bool = True
    judul_topik_inggris: str = ""
    email: str = ""
    openalex_api_key: str = ""


class Job:
    def __init__(self, params: SearchParams):
        self.id = uuid.uuid4().hex[:12]
        self.params = params
        self.status = "running"
        self.events: list[dict] = []
        self.result: dict | None = None
        self.error: str | None = None
        self.zip_path: str | None = None
        self.folder: str | None = None
        self.started = time.time()


JOBS: dict[str, Job] = {}
LOCK = threading.Lock()


def _ringkas_referensi(r: dict) -> dict:
    return {k: r.get(k) for k in (
        "uid", "id", "no", "skor", "kategori", "judul", "penulis", "tahun", "jenis", "sumber", "penerbit",
        "doi", "url", "sitasi", "pdf", "sumber_pdf", "kata_cocok", "asal", "abstrak",
        "doaj", "sinta", "ringkasan", "metode", "hasil_utama", "apa", "ieee", "duplikat")}


# ============================ pustaka lokal ============================
def _baca_pustaka() -> list[dict]:
    if not PUSTAKA_FILE or not PUSTAKA_FILE.is_file():
        return []
    try:
        return json.loads(PUSTAKA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _tulis_pustaka(entries: list[dict]):
    if not PUSTAKA_FILE:
        return
    tmp = PUSTAKA_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    tmp.replace(PUSTAKA_FILE)


def _norm_doi(doi):
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", (doi or "").strip().lower())


def _norm_judul(judul):
    return re.sub(r"[^a-z0-9]+", "", (judul or "").lower())


def _tandai_duplikat(job: Job, entries: list[dict]):
    """Tandai referensi yang sudah pernah diambil di pencarian sebelumnya."""
    indeks = {}
    for e in entries:
        info = {"topik": e.get("topik", ""), "tanggal": e.get("tanggal", "")}
        for r in _semua_refs(e["result"]):
            doi = _norm_doi(r.get("doi"))
            if doi:
                indeks.setdefault(f"doi:{doi}", info)
            judul = _norm_judul(r.get("judul"))
            if len(judul) > 20:
                indeks.setdefault(f"judul:{judul}", info)
    for r in _semua_refs(job.result):
        kunci = (f"doi:{_norm_doi(r.get('doi'))}" if r.get("doi") else None,
                 f"judul:{_norm_judul(r.get('judul'))}")
        r["duplikat"] = next((indeks[k] for k in kunci if k and k in indeks), None)


def _simpan_riwayat(job: Job):
    try:
        with LOCK:
            entries = [e for e in _baca_pustaka() if e.get("id") != job.id]
            _tandai_duplikat(job, entries)
            entries.insert(0, {
                "id": job.id,
                "tanggal": datetime.now().isoformat(timespec="seconds"),
                "topik": job.result["topik"],
                "result": job.result,
                "zip_path": job.zip_path,
                "folder": job.folder,
                "favorit": [],
                "catatan": {},
            })
            _tulis_pustaka(entries[:100])
    except Exception:
        traceback.print_exc()


def _entri(lib_id: str) -> dict:
    for e in _baca_pustaka():
        if e.get("id") == lib_id:
            return e
    raise HTTPException(404, "Entri pustaka tidak ditemukan")


def _refs_dari(src: str):
    """src = 'job:<id>' (sesi berjalan) atau 'lib:<id>' (riwayat tersimpan)."""
    jenis, _, idnya = src.partition(":")
    if jenis == "job":
        job = JOBS.get(idnya)
        if not job or job.status != "done" or not job.result:
            raise HTTPException(404, "Hasil pencarian tidak ditemukan")
        return _lengkapi_analisis(job.result), job.zip_path, job.folder, job.id
    if jenis == "lib":
        e = _entri(idnya)
        return _lengkapi_analisis(e["result"]), e.get("zip_path"), e.get("folder"), e["id"]
    raise HTTPException(400, "src harus 'job:<id>' atau 'lib:<id>'")


def _lengkapi_analisis(result):
    """Entri riwayat lama belum punya statistik — hitung ulang dari referensinya."""
    if not result.get("analisis"):
        result["analisis"] = statistik_tren(result)
    result.setdefault("prisma", None)
    return result


def _semua_refs(result: dict) -> list[dict]:
    return [r for kat in ("Nasional", "Internasional") for r in result["hasil"].get(kat, [])]


def _jalankan_job(job: Job):
    def progress(ev):
        job.events.append({**ev, "t": round(time.time() - job.started, 1)})

    try:
        hasil = jalankan_referensia(**job.params.model_dump(), progress=progress)
    except Exception as ex:
        job.status = "error"
        job.error = str(ex)
        job.events.append({"event": "error", "text": str(ex),
                           "detail": traceback.format_exc(limit=5)})
        return
    if not hasil:
        job.status = "empty"
        return
    job.zip_path = hasil["zip_path"]
    job.folder = hasil.get("folder")
    job.result = {
        "topik": hasil["topik"], "topik_id": hasil["topik_id"], "topik_en": hasil["topik_en"],
        "target": hasil["target"],
        "hasil": {kat: [_ringkas_referensi(r) for r in rows] for kat, rows in hasil["hasil"].items()},
        "catatan": hasil["catatan"], "kunci_kat": hasil["kunci_kat"], "tema_kat": hasil["tema_kat"],
        "jumlah_pdf": hasil["jumlah_pdf"], "total": hasil["total"],
        "prisma": hasil.get("prisma"), "analisis": hasil.get("analisis"),
        "durasi_detik": hasil["durasi_detik"],
        "zip_name": os.path.basename(hasil["zip_path"]),
    }
    job.status = "done"
    _simpan_riwayat(job)


@app.get("/api/health")
def health():
    return {"ok": True, "app": "Referensia Desktop", "versi": VERSI_APP, "api": VERSI_API}


@app.post("/api/search")
def mulai_search(params: SearchParams):
    if not params.judul_topik.strip():
        raise HTTPException(400, "judul_topik masih kosong")
    if params.jumlah_nasional + params.jumlah_internasional <= 0:
        raise HTTPException(400, "Isi minimal salah satu: jumlah_nasional atau jumlah_internasional")
    with LOCK:
        if any(j.status == "running" for j in JOBS.values()):
            raise HTTPException(409, "Masih ada pencarian yang berjalan. Tunggu selesai dulu.")
        job = Job(params)
        JOBS[job.id] = job
    threading.Thread(target=_jalankan_job, args=(job,), daemon=True).start()
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}")
def status_job(job_id: str, since: int = 0):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job tidak ditemukan")
    return {
        "id": job.id, "status": job.status, "error": job.error,
        "events": job.events[since:], "next": len(job.events),
        "result": job.result if job.status == "done" else None,
        "durasi": round(time.time() - job.started),
    }


@app.get("/api/jobs/{job_id}/download")
def unduh_zip(job_id: str):
    job = JOBS.get(job_id)
    if not job or job.status != "done" or not job.zip_path or not os.path.isfile(job.zip_path):
        raise HTTPException(404, "ZIP belum tersedia")
    return FileResponse(job.zip_path, media_type="application/zip",
                        filename=os.path.basename(job.zip_path))


# ============================ pustaka & riwayat ============================
@app.get("/api/library")
def daftar_pustaka():
    return [{
        "id": e["id"], "tanggal": e["tanggal"], "topik": e["topik"],
        "total": e["result"].get("total", 0), "jumlah_pdf": e["result"].get("jumlah_pdf", 0),
        "zip_name": e["result"].get("zip_name", ""),
        "zip_ada": bool(e.get("zip_path") and os.path.isfile(e["zip_path"])),
        "n_favorit": len(e.get("favorit", [])),
    } for e in _baca_pustaka()]


@app.get("/api/library/{lib_id}")
def detail_pustaka(lib_id: str):
    e = _entri(lib_id)
    return {"id": e["id"], "tanggal": e["tanggal"], "topik": e["topik"],
            "result": _lengkapi_analisis(e["result"]), "favorit": e.get("favorit", []),
            "catatan": e.get("catatan", {}),
            "zip_ada": bool(e.get("zip_path") and os.path.isfile(e["zip_path"]))}


@app.delete("/api/library/{lib_id}")
def hapus_pustaka(lib_id: str):
    with LOCK:
        entries = _baca_pustaka()
        baru = [e for e in entries if e.get("id") != lib_id]
        if len(baru) == len(entries):
            raise HTTPException(404, "Entri pustaka tidak ditemukan")
        _tulis_pustaka(baru)
    return {"ok": True}


@app.get("/api/library/{lib_id}/download")
def unduh_zip_pustaka(lib_id: str):
    e = _entri(lib_id)
    zp = e.get("zip_path")
    if not zp or not os.path.isfile(zp):
        raise HTTPException(404, "ZIP sudah tidak ada di disk (mungkin folder hasil dipindah/dihapus)")
    return FileResponse(zp, media_type="application/zip", filename=os.path.basename(zp))


class FavParams(BaseModel):
    lib_id: str
    uid: str
    on: bool


@app.post("/api/favorite")
def toggle_favorit(p: FavParams):
    with LOCK:
        entries = _baca_pustaka()
        for e in entries:
            if e.get("id") == p.lib_id:
                fav = e.setdefault("favorit", [])
                if p.on and p.uid not in fav:
                    fav.append(p.uid)
                if not p.on and p.uid in fav:
                    fav.remove(p.uid)
                _tulis_pustaka(entries)
                return {"ok": True, "favorit": fav}
    raise HTTPException(404, "Entri pustaka tidak ditemukan")


class NoteParams(BaseModel):
    lib_id: str
    uid: str
    teks: str = ""


@app.post("/api/note")
def simpan_catatan(p: NoteParams):
    with LOCK:
        entries = _baca_pustaka()
        for e in entries:
            if e.get("id") == p.lib_id:
                catatan = e.setdefault("catatan", {})
                if p.teks.strip():
                    catatan[p.uid] = p.teks.strip()
                else:
                    catatan.pop(p.uid, None)
                _tulis_pustaka(entries)
                return {"ok": True, "catatan": catatan}
    raise HTTPException(404, "Entri pustaka tidak ditemukan")


@app.get("/api/favorites")
def semua_favorit():
    out = []
    for e in _baca_pustaka():
        fav = set(e.get("favorit", []))
        if not fav:
            continue
        catatan = e.get("catatan", {})
        refs = [{**r, "catatan_pribadi": catatan.get(r.get("uid"), "")}
                for r in _semua_refs(e["result"]) if r.get("uid") in fav]
        if refs:
            out.append({"lib_id": e["id"], "topik": e["topik"], "tanggal": e["tanggal"], "refs": refs})
    return out


# ============================ ekspor ============================
@app.get("/api/export")
def ekspor(src: str, kind: str, background_tasks: BackgroundTasks):
    result, _, _, lib_id = _refs_dari(src)
    rows = _semua_refs(result)
    if not rows:
        raise HTTPException(404, "Tidak ada referensi untuk diekspor")
    catatan = next((e.get("catatan", {}) for e in _baca_pustaka() if e.get("id") == lib_id), {})
    nama_dasar = f"Referensia_{lib_id}"
    tmpdir = tempfile.mkdtemp(prefix="referensia_")
    if kind == "apa_docx":
        path = os.path.join(tmpdir, f"{nama_dasar}_APA.docx")
        buat_docx(rows, "apa", path)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif kind == "ieee_docx":
        path = os.path.join(tmpdir, f"{nama_dasar}_IEEE.docx")
        buat_docx(rows, "ieee", path)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif kind == "matriks_xlsx":
        path = os.path.join(tmpdir, f"{nama_dasar}_matriks.xlsx")
        buat_matriks_xlsx(rows, path, catatan)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif kind == "matriks_docx":
        path = os.path.join(tmpdir, f"{nama_dasar}_matriks.docx")
        buat_matriks_docx(result, catatan, path)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif kind == "laporan_docx":
        path = os.path.join(tmpdir, f"{nama_dasar}_laporan_tinjauan.docx")
        buat_laporan_docx(result, catatan, path)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif kind == "markdown":
        path = os.path.join(tmpdir, f"{nama_dasar}.md")
        Path(path).write_text(buat_markdown(result, catatan), encoding="utf-8")
        media = "text/markdown"
    elif kind == "apa_txt":
        path = os.path.join(tmpdir, f"{nama_dasar}_APA.txt")
        Path(path).write_text("\n\n".join(r.get("apa", "") for r in rows), encoding="utf-8")
        media = "text/plain"
    elif kind == "ieee_txt":
        path = os.path.join(tmpdir, f"{nama_dasar}_IEEE.txt")
        Path(path).write_text("\n\n".join(r.get("ieee", "") for r in rows), encoding="utf-8")
        media = "text/plain"
    elif kind == "ris":
        path = os.path.join(tmpdir, f"{nama_dasar}.ris")
        Path(path).write_text(buat_ris(rows, result["topik"]), encoding="utf-8")
        media = "application/x-research-info-systems"
    else:
        raise HTTPException(400, "kind tidak dikenal")
    background_tasks.add_task(os.remove, path)
    background_tasks.add_task(os.rmdir, tmpdir)
    return FileResponse(path, media_type=media, filename=os.path.basename(path))


# ============================ Zotero & Mendeley ============================
class SrcParams(BaseModel):
    src: str


NOTION_VER = "2022-06-28"


def _notion_page_id(teks):
    teks = (teks or "").strip()
    if not teks:
        return ""
    segmen = teks
    if "/" in teks:
        from urllib.parse import urlparse
        jalur = urlparse(teks if "://" in teks else "https://" + teks).path
        segmen = jalur.rstrip("/").split("/")[-1]
    kandidat = re.sub(r"[^0-9a-f]", "", segmen.lower())[-32:]
    return kandidat if len(kandidat) == 32 else ""


def _rt(teks):
    return [{"type": "text", "text": {"content": (teks or "")[:1900]}}]


def _baris_tabel(sel):
    return {"type": "table_row", "table_row": {"cells": [_rt(c) for c in sel]}}


def _tabel_notion(header, baris):
    return {"object": "block", "type": "table",
            "table": {"table_width": len(header), "has_column_header": True,
                      "children": [_baris_tabel(header)] + [_baris_tabel(b) for b in baris]}}


def notion_blocks(result, catatan=None):
    """Blok Notion: heading + tabel matriks (+ catatan pribadi) + daftar pustaka APA."""
    catatan = catatan or {}
    blok = []
    header = ["No", "Judul", "Tahun", "Metode", "Hasil utama", "Catatan"]
    for kat in ("Nasional", "Internasional"):
        rows = result["hasil"].get(kat) or []
        if not rows:
            continue
        blok.append({"object": "block", "type": "heading_2",
                     "heading_2": {"rich_text": _rt(f"{kat} ({len(rows)})")}})
        data = []
        for i, r in enumerate(rows, 1):
            m = r.get("metode") or {}
            metode = " · ".join(x for x in [m.get("pendekatan"), m.get("desain"), m.get("sampel"),
                                           ", ".join(m.get("analisis") or [])] if x)
            data.append([str(i), r.get("judul") or "", str(r.get("tahun") or ""), metode,
                         r.get("hasil_utama") or "", catatan.get(r.get("uid"), "")])
        for awal in range(0, len(data), 40):
            blok.append(_tabel_notion(header, data[awal:awal + 40]))
    blok.append({"object": "block", "type": "heading_2",
                 "heading_2": {"rich_text": _rt("Daftar Pustaka (APA)")}})
    for kat in ("Nasional", "Internasional"):
        for r in result["hasil"].get(kat) or []:
            if r.get("apa"):
                blok.append({"object": "block", "type": "paragraph",
                             "paragraph": {"rich_text": _rt(r["apa"])}})
    return blok


def _potong_blok(blok, maks=90):
    """Bagi blok per request Notion; blok tabel dihitung 1 + jumlah baris."""
    potongan, kini, berat = [], [], 0
    for b in blok:
        w = 1 + (len(b.get("table", {}).get("children", [])) if b.get("type") == "table" else 0)
        if kini and berat + w > maks:
            potongan.append(kini)
            kini, berat = [], 0
        kini.append(b)
        berat += w
    if kini:
        potongan.append(kini)
    return potongan


class NotionParams(BaseModel):
    src: str
    token: str
    page: str


class NotionTokenParams(BaseModel):
    token: str


def _notion_workspace(body):
    bot = (body or {}).get("bot") or {}
    return str(bot.get("workspace_name") or "")


def _daftar_halaman(body):
    """Ambil [{judul, url, terakhir}] dari hasil /v1/search (filter page)."""
    hasil = []
    for it in (body or {}).get("results") or []:
        if it.get("object") != "page" or it.get("archived"):
            continue
        judul = ""
        for prop in (it.get("properties") or {}).values():
            if prop.get("type") == "title":
                judul = "".join(t.get("plain_text", "") for t in prop.get("title") or []).strip()
                break
        url = it.get("url") or ""
        if url:
            hasil.append({"judul": judul or "Tanpa judul", "url": url,
                          "terakhir": (it.get("last_edited_time") or "")[:10]})
    return hasil


@app.post("/api/notion/verify")
def notion_verify(p: NotionTokenParams):
    """Cek token + tampilkan workspace dan halaman yang sudah dibagikan ke integration."""
    token = (p.token or "").strip()
    if not token:
        raise HTTPException(400, "Token integration Notion masih kosong")
    hdr = {"Authorization": f"Bearer {token}", "Notion-Version": NOTION_VER}
    sesi = requests.Session()
    halaman, catatan = [], ""
    try:
        r = sesi.get("https://api.notion.com/v1/users/me", headers=hdr, timeout=20)
        if r.status_code == 401:
            raise HTTPException(401, "Token Notion tidak valid — salin ulang dari notion.so/my-integrations")
        if r.status_code != 200:
            raise HTTPException(502, f"Notion menolak token (HTTP {r.status_code}): {r.text[:300]}")
        me = r.json()
        rs = sesi.post("https://api.notion.com/v1/search", headers=hdr, timeout=20,
                       json={"filter": {"value": "page", "property": "object"}, "page_size": 100,
                             "sort": {"direction": "descending", "timestamp": "last_edited_time"}})
        if rs.status_code == 200:
            halaman = _daftar_halaman(rs.json())
        else:
            catatan = ("Daftar halaman tidak bisa dibaca — aktifkan izin “Read content” di pengaturan "
                       "integration, atau tempel URL halaman secara manual.")
    except requests.RequestException as ex:
        raise HTTPException(502, f"Gagal menghubungi Notion: {ex}")
    return {"ok": True, "ruang": _notion_workspace(me), "bot": me.get("name") or "",
            "halaman": halaman, "catatan": catatan}


@app.post("/api/notion")
def kirim_notion(p: NotionParams):
    result, _, _, lib_id = _refs_dari(p.src)
    token = (p.token or "").strip()
    page_id = _notion_page_id(p.page)
    if not token:
        raise HTTPException(400, "Token integration Notion masih kosong")
    if not page_id:
        raise HTTPException(400, "URL/ID halaman Notion tidak dikenali")
    catatan = next((e.get("catatan", {}) for e in _baca_pustaka() if e.get("id") == lib_id), {})
    potongan = _potong_blok(notion_blocks(result, catatan))
    hdr = {"Authorization": f"Bearer {token}", "Notion-Version": NOTION_VER}
    sesi = requests.Session()
    try:
        r = sesi.post("https://api.notion.com/v1/pages", headers=hdr, timeout=30,
                      json={"parent": {"page_id": page_id},
                            "properties": {"title": {"title": _rt(f"Matriks Literatur — {result['topik']}")}},
                            "children": potongan[0]})
        if r.status_code == 401:
            raise HTTPException(401, "Token Notion tidak valid — salin ulang dari notion.so/my-integrations")
        if r.status_code == 404:
            raise HTTPException(404, "Halaman Notion tidak ditemukan — buka halaman tujuan → ⋯ → Connections "
                                     "→ hubungkan integration-mu, lalu coba lagi")
        if r.status_code != 200:
            raise HTTPException(502, f"Notion menolak permintaan (HTTP {r.status_code}): {r.text[:300]}")
        data = r.json()
        page_baru = data.get("id")
        for sisa in potongan[1:]:
            rr = sesi.post(f"https://api.notion.com/v1/blocks/{page_baru}/children",
                           headers=hdr, timeout=30, json={"children": sisa})
            if rr.status_code != 200:
                raise HTTPException(502, "Halaman Notion sudah dibuat, tetapi sebagian isi gagal ditambahkan "
                                         f"(HTTP {rr.status_code}). Coba lagi untuk melengkapi.")
    except requests.RequestException as ex:
        raise HTTPException(502, f"Gagal menghubungi Notion: {ex}")
    return {"ok": True, "url": data.get("url", "")}


@app.post("/api/zotero")
def kirim_zotero(p: SrcParams):
    result, _, _, _ = _refs_dari(p.src)
    items = [zotero_item(r) for r in _semua_refs(result)]
    if not items:
        raise HTTPException(404, "Tidak ada referensi untuk dikirim")
    try:
        requests.get("http://127.0.0.1:23119/connector/ping", timeout=3)
    except requests.RequestException:
        raise HTTPException(503, "Zotero tidak terdeteksi. Buka aplikasi Zotero desktop dulu "
                                 "(pastikan Zotero berjalan di komputer ini), lalu coba lagi.")
    try:
        res = requests.post("http://127.0.0.1:23119/connector/saveItems",
                            json={"items": items, "uri": "referensia://desktop"}, timeout=30)
    except requests.RequestException as ex:
        raise HTTPException(502, f"Gagal menghubungi Zotero: {ex}")
    if res.status_code not in (200, 201):
        raise HTTPException(502, f"Zotero menolak simpanan (HTTP {res.status_code})")
    return {"ok": True, "jumlah": len(items)}


@app.post("/api/open-folder")
def buka_folder(p: SrcParams):
    _, zip_path, folder, _ = _refs_dari(p.src)
    target = folder if folder and os.path.isdir(folder) else (
        os.path.dirname(zip_path) if zip_path else None)
    if not target or not os.path.isdir(target):
        raise HTTPException(404, "Folder hasil tidak ditemukan di disk")
    if os.name != "nt":
        raise HTTPException(400, "Buka folder hanya didukung di Windows")
    os.startfile(target)  # noqa: S606 — path berasal dari hasil kita sendiri
    return {"ok": True, "folder": target}


# ============================ jaringan sitasi ============================
POLA_W = re.compile(r"^W\d+$")


def _oa_works(sesi, filter_value, kolom="id,title,doi,cited_by_count,referenced_works,publication_year"):
    r = sesi.get("https://api.openalex.org/works", timeout=40,
                 params={"filter": filter_value, "per-page": 50, "select": kolom})
    if r.status_code != 200:
        raise HTTPException(502, f"OpenAlex menolak permintaan jaringan sitasi (HTTP {r.status_code}). "
                                 f"Coba lagi beberapa saat.")
    return r.json().get("results") or []


def _potong(lst, n=40):
    return [lst[i:i + n] for i in range(0, len(lst), n)]


def bangun_jaringan(result):
    """Bangun graf sitasi antar referensi terpilih + karya luar yang banyak dikutip bersama."""
    refs = _semua_refs(result)
    if len(refs) < 2:
        raise HTTPException(400, "Jaringan sitasi butuh minimal 2 referensi")
    wid_langsung, doi_cari = [], []
    for r in refs:
        wid = (r.get("id") or "").strip()
        if POLA_W.match(wid):
            wid_langsung.append(wid)
        elif _norm_doi(r.get("doi")):
            doi_cari.append(_norm_doi(r.get("doi")))
    sesi = requests.Session()
    meta, doi_ke_w = {}, {}
    try:
        for bagian in _potong(sorted(set(wid_langsung))):
            for w in _oa_works(sesi, "openalex:" + "|".join(bagian)):
                meta[w["id"].rsplit("/", 1)[-1]] = w
        for bagian in _potong(sorted(set(doi_cari))):
            for w in _oa_works(sesi, "doi:" + "|".join(bagian)):
                wid = w["id"].rsplit("/", 1)[-1]
                meta[wid] = w
                if w.get("doi"):
                    doi_ke_w[_norm_doi(w["doi"])] = wid
    except requests.RequestException as ex:
        raise HTTPException(502, f"Gagal menghubungi OpenAlex: {ex}")

    uid_ke_w = {}
    for r in refs:
        wid = (r.get("id") or "").strip()
        if POLA_W.match(wid):
            uid_ke_w[r["uid"]] = wid
        else:
            uid_ke_w[r["uid"]] = doi_ke_w.get(_norm_doi(r.get("doi")))
    dikenali = {w for w in uid_ke_w.values() if w and w in meta}
    nodes = [{"id": w, "label": next(r["judul"] for r in refs if uid_ke_w.get(r["uid"]) == w),
              "tahun": meta[w].get("publication_year"), "sitasi": meta[w].get("cited_by_count") or 0,
              "kategori": next(r.get("kategori") for r in refs if uid_ke_w.get(r["uid"]) == w),
              "luar": False} for w in dikenali]
    edges, sudah = [], set()
    luar_hitung = {}
    for w in dikenali:
        for url in meta[w].get("referenced_works") or []:
            tgt = url.rsplit("/", 1)[-1]
            if tgt in dikenali:
                kunci = (w, tgt)
                if kunci not in sudah:
                    sudah.add(kunci)
                    edges.append({"source": w, "target": tgt})
            else:
                luar_hitung[tgt] = luar_hitung.get(tgt, 0) + 1
    luar = [w for w, n in sorted(luar_hitung.items(), key=lambda x: -x[1])[:12] if n >= 2]
    if luar:
        try:
            for bagian in _potong(luar):
                for w in _oa_works(sesi, "openalex:" + "|".join(bagian), "id,title,cited_by_count,publication_year"):
                    wid = w["id"].rsplit("/", 1)[-1]
                    meta[wid] = w
        except (requests.RequestException, HTTPException):
            pass
        ditambah = set()
        for wid in luar:
            if wid not in meta:
                continue
            nodes.append({"id": wid, "label": meta[wid].get("title") or "(tanpa judul)",
                          "tahun": meta[wid].get("publication_year"),
                          "sitasi": meta[wid].get("cited_by_count") or 0,
                          "kategori": "", "luar": True})
            ditambah.add(wid)
        for w in dikenali:
            for url in meta[w].get("referenced_works") or []:
                tgt = url.rsplit("/", 1)[-1]
                if tgt in ditambah:
                    kunci = (w, tgt)
                    if kunci not in sudah:
                        sudah.add(kunci)
                        edges.append({"source": w, "target": tgt})
    catatan = ""
    if not dikenali:
        catatan = ("OpenAlex tidak mengenali referensi ini (mungkin DOI belum terdaftar). "
                   "Jaringan sitasi tidak bisa dibangun, tetapi matriks dan laporan tetap lengkap.")
    elif len(nodes) < len(refs):
        catatan = (f"{len(refs) - len(dikenali)} referensi tidak dikenali OpenAlex; "
                   f"graf hanya memuat {len(dikenali)} referensi yang dikenali.")
    teratas = sorted([n for n in nodes if not n["luar"]], key=lambda n: -(n.get("sitasi") or 0))[:5]
    return {"ok": True, "nodes": nodes, "edges": edges, "catatan": catatan,
            "teratas": teratas,
            "jumlah": {"masuk": len(refs), "dikenali": len(dikenali),
                       "luar": sum(1 for n in nodes if n["luar"]), "koneksi": len(edges)}}


@app.get("/api/network")
def jaringan_sitasi(src: str):
    result, _, _, _ = _refs_dari(src)
    return bangun_jaringan(result)


# ============================ asisten AI ============================
TUGAS_AI = {
    "sintesis": "Susun sintesis tinjauan pustaka per tema: kesepakatan antar studi, perbedaan temuan, "
                "metode yang dominan, dan celah penelitian. Gunakan bahasa akademik Indonesia yang padat. "
                "Sebutkan (Penulis, tahun) saat merujuk suatu studi; jangan mengarang sitasi baru.",
    "bandingkan": "Buat tabel perbandingan Markdown dengan kolom: Studi (penulis, tahun), Metode/desain, "
                  "Sampel, Teknik analisis, Temuan utama, Keterbatasan. Isi hanya berdasarkan abstrak yang "
                  "diberikan; tulis 'tidak disebutkan' bila informasi tidak ada.",
    "rumusan": "Rumuskan 3–5 peluang penelitian (research gap) yang benar-benar didukung referensi di bawah, "
               "lalu usulkan rumusan masalah dan judul penelitian yang lebih spesifik. Tandai dasar tiap gap "
               "dengan (Penulis, tahun).",
}


def konteks_ai(result, maks_karakter=16000, abstrak_maks=700):
    """Ringkas referensi menjadi konteks prompt; abstrak dipotong agar hemat token."""
    keping, total = [], 0
    for i, r in enumerate(_semua_refs(result), 1):
        m = r.get("metode") or {}
        baris = (f"{i}. {r.get('judul', '')} ({r.get('tahun') or '—'}; {r.get('sumber') or '-'}; "
                 f"{r.get('kategori', '')})\n"
                 f"   Metode: {' · '.join(x for x in [m.get('pendekatan'), m.get('desain'), m.get('sampel'),
                                                    ', '.join(m.get('analisis') or [])] if x) or '-'}\n"
                 f"   Hasil utama: {r.get('hasil_utama') or '-'}\n"
                 f"   Abstrak: {(r.get('abstrak') or '-')[:abstrak_maks]}\n")
        if total + len(baris) > maks_karakter:
            keping.append(f"(Sisa {len(_semua_refs(result)) - i + 1} referensi tidak disertakan karena batas panjang.)")
            break
        keping.append(baris)
        total += len(baris)
    return "\n".join(keping)


def prompt_ai(result, tugas, instruksi=""):
    aturan = TUGAS_AI.get(tugas, TUGAS_AI["sintesis"])
    pengantar = f"Topik tinjauan: {result.get('topik', '')}.\n\nKonteks referensi:\n{konteks_ai(result)}"
    if instruksi.strip():
        pengantar += f"\nInstruksi tambahan dari pengguna: {instruksi.strip()}"
    return [{"role": "system", "content": "Anda asisten penulisan tinjauan pustaka akademik. "
                                          "Jawab ringkas, terstruktur, dan hanya berdasarkan konteks yang diberikan."},
            {"role": "user", "content": f"{aturan}\n\n{pengantar}"}]


class AIParams(BaseModel):
    src: str
    key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    tugas: str = "sintesis"
    instruksi: str = ""


@app.post("/api/ai")
def asisten_ai(p: AIParams):
    result, _, _, _ = _refs_dari(p.src)
    key = (p.key or "").strip()
    base = (p.base_url or "").strip().rstrip("/")
    if base.endswith("/chat/completions"):
        base = base[: -len("/chat/completions")]
    if not key:
        raise HTTPException(400, "API key masih kosong")
    if not base.startswith("https://"):
        raise HTTPException(400, "URL API harus diawali https://")
    if not (p.model or "").strip():
        raise HTTPException(400, "Nama model masih kosong")
    try:
        r = requests.post(f"{base}/chat/completions", timeout=120,
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                          json={"model": p.model.strip(), "temperature": 0.3,
                                "messages": prompt_ai(result, p.tugas, p.instruksi)})
    except requests.RequestException as ex:
        raise HTTPException(502, f"Gagal menghubungi penyedia AI: {ex}")
    if r.status_code == 401:
        raise HTTPException(401, "API key ditolak penyedia — periksa kembali key dan penyedianya")
    if r.status_code == 404:
        raise HTTPException(404, "Model atau URL API tidak ditemukan — periksa nama model dan base URL")
    if r.status_code != 200:
        raise HTTPException(502, f"Penyedia AI menolak permintaan (HTTP {r.status_code}): {r.text[:300]}")
    try:
        teks = r.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError):
        raise HTTPException(502, "Balasan penyedia AI tidak dikenali")
    return {"ok": True, "teks": teks, "model": p.model.strip()}


# ============================ pembaruan aplikasi ============================
_LOCK_RILIS = threading.Lock()
_CACHE_RILIS: dict = {"data": None, "kapan": 0.0, "galat": ""}


def _ambil_rilis(paksa: bool = False):
    """Rilis terbaru dari GitHub, dicache enam jam supaya tidak kena rate limit."""
    with _LOCK_RILIS:
        daluwarsa = time.time() - _CACHE_RILIS["kapan"] > UMUR_CACHE_RILIS
        if paksa or _CACHE_RILIS["data"] is None or daluwarsa:
            try:
                _CACHE_RILIS["data"] = pembaruan.rilis_terbaru(REPO_RILIS)
                _CACHE_RILIS["galat"] = ""
            except (ValueError, requests.RequestException) as ex:
                _CACHE_RILIS["galat"] = str(ex)
            _CACHE_RILIS["kapan"] = time.time()
        return _CACHE_RILIS["data"]


@app.get("/api/update/check")
def cek_update(paksa: bool = False):
    r = _ambil_rilis(paksa)
    if r is None:
        raise HTTPException(502, _CACHE_RILIS["galat"] or "Gagal memeriksa rilis.")
    return {"ok": True, "repo": REPO_RILIS, "versi_sekarang": VERSI_APP,
            "ada_baru": pembaruan.lebih_baru(r["versi"], VERSI_APP), "rilis": r,
            "galat": _CACHE_RILIS["galat"], "diperiksa_pada": _CACHE_RILIS["kapan"]}


class UnduhPembaruanParams(BaseModel):
    url: str


@app.post("/api/update/download")
def unduh_pembaruan(p: UnduhPembaruanParams):
    # Hanya terima tautan yang memang terdaftar di rilis terakhir — bukan URL sembarang.
    aset = next((a for a in ((_CACHE_RILIS["data"] or {}).get("aset") or []) if a["unduh"] == p.url), None)
    if aset is None:
        raise HTTPException(400, "Tautan unduhan tidak dikenali sebagai aset rilis Referensia.")
    try:
        info = pembaruan.unduh_installer(aset["unduh"], Path.cwd() / "pembaruan", aset["nama"])
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    except requests.RequestException as ex:
        raise HTTPException(502, f"Unduhan gagal: {ex}")
    return {"ok": True, **info}


class PasangPembaruanParams(BaseModel):
    lokasi: str


@app.post("/api/update/install")
def pasang_pembaruan(p: PasangPembaruanParams):
    folder = (Path.cwd() / "pembaruan").resolve()
    lokasi = Path(p.lokasi)
    if lokasi.parent.resolve() != folder:
        raise HTTPException(400, "Penginstal harus berada di folder pembaruan Referensia.")
    try:
        pembaruan.jadwalkan_pasang(lokasi)
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    return {"ok": True, "pesan": "Penginstal berjalan otomatis begitu Referensia ditutup."}


def _cari_dir_ui(hibah: str) -> Path | None:
    """Cari hasil `npm run build` (index.html) — urutan: --ui, env, app/dist."""
    for calon in (hibah, os.environ.get("REFERENSIA_UI", ""),
                  str(Path(__file__).resolve().parent.parent / "dist")):
        if calon and (Path(calon) / "index.html").is_file():
            return Path(calon).resolve()
    return None


def pasang_ui(dir_ui: Path):
    """Sajikan antarmuka web dari backend (mode browser, tanpa Tauri/MSVC).

    Montase harus dipasang setelah semua rute /api — Starlette mencocokkan rute
    berurutan, jadi kalau "/" terdaftar duluan, API-nya tertimpa index.html.
    """
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(dir_ui), html=True), name="ui")


_LOG_BERKAS: Path | None = None


def _tulis_log(teks: str):
    """Jejak startup/galat di Documents/Referensia/backend.log — sidecar tanpa jendela."""
    if _LOG_BERKAS is None:
        return
    try:
        with open(_LOG_BERKAS, "a", encoding="utf-8") as fh:
            fh.write(str(teks).rstrip() + "\n")
    except OSError:
        pass


def _catat_except(jenis, nilai, tb):
    _tulis_log("".join(traceback.format_exception(jenis, nilai, tb)))


def main():
    global PUSTAKA_FILE, _LOG_BERKAS
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.environ.get("REFERENSIA_PORT", PORT_DEFAULT)))
    parser.add_argument("--output", default=os.environ.get("REFERENSIA_OUTPUT", ""))
    parser.add_argument("--ui", default="", help="folder hasil npm run build (default: deteksi otomatis app/dist)")
    parser.add_argument("--no-ui", action="store_true", help="hanya sediakan API, tanpa halaman web")
    parser.add_argument("--open", action="store_true", help="buka browser setelah server siap")
    parser.add_argument("--pasang-setelah-tutup", default="",
                        help="(internal) tunggu aplikasi tertutup lalu jalankan penginstal ini")
    parser.add_argument("--aplikasi", default=pembaruan.NAMA_APLIKASI,
                        help="(internal) nama proses yang ditunggu pengawas pembaruan")
    args = parser.parse_args()

    if args.pasang_setelah_tutup:   # proses pengawas — jangan mulai server
        raise SystemExit(pembaruan.pasang_setelah_tutup(args.pasang_setelah_tutup, args.aplikasi))

    # Hasil (folder Referensia_hasil + ZIP) ditulis relatif terhadap cwd mesin.
    dasar = Path(args.output) if args.output else Path.home() / "Documents" / "Referensia"
    dasar.mkdir(parents=True, exist_ok=True)
    os.chdir(dasar)
    PUSTAKA_FILE = dasar / "pustaka.json"
    _LOG_BERKAS = dasar / "backend.log"
    sys.excepthook = _catat_except
    _tulis_log(f"=== {datetime.now():%Y-%m-%d %H:%M:%S} mulai Referensia {VERSI_APP} (api {VERSI_API}) port {args.port}")
    print(f"[Referensia] hasil disimpan di: {dasar}", flush=True)

    url = f"http://127.0.0.1:{args.port}"
    dir_ui = None if args.no_ui else _cari_dir_ui(args.ui)
    if dir_ui:
        pasang_ui(dir_ui)
        print(f"[Referensia] antarmuka web: {url}", flush=True)
    else:
        print("[Referensia] mode API saja (npm run build belum dijalankan / --no-ui)", flush=True)

    if args.open:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    import uvicorn
    try:
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    except SystemExit:
        _tulis_log("server berhenti (SystemExit) — biasanya port sudah dipakai proses lain")
        raise
    except Exception:
        _tulis_log(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()