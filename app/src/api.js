// Dev (Vite :5173) & mode browser (halaman disajikan FastAPI di :8756) pakai origin yang sama.
// Shell Tauri (tauri://localhost) tak punya /api → menunjuk langsung ke backend lokal.
const disajikanBackend = typeof window !== "undefined" && window.location.port === "8756";
const BASE = import.meta.env.DEV || disajikanBackend ? "/api" : "http://127.0.0.1:8756/api";

async function cek(res) {
  if (!res.ok) {
    let pesan = `HTTP ${res.status}`;
    try {
      const d = await res.json();
      pesan = d.detail || pesan;
    } catch {}
    throw new Error(pesan);
  }
  return res.json();
}

export async function startSearch(params) {
  return cek(
    await fetch(`${BASE}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    })
  );
}

export async function getJob(id, since = 0) {
  return cek(await fetch(`${BASE}/jobs/${id}?since=${since}`));
}

export async function health() {
  return cek(await fetch(`${BASE}/health`));
}

export const downloadUrl = (id) => `${BASE}/jobs/${id}/download`;

export async function library() {
  return cek(await fetch(`${BASE}/library`));
}

export async function libraryEntry(id) {
  return cek(await fetch(`${BASE}/library/${id}`));
}

export async function hapusLibrary(id) {
  return cek(await fetch(`${BASE}/library/${id}`, { method: "DELETE" }));
}

export const libraryDownloadUrl = (id) => `${BASE}/library/${id}/download`;

export async function toggleFavorit(libId, uid, on) {
  return cek(
    await fetch(`${BASE}/favorite`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lib_id: libId, uid, on }),
    })
  );
}

export async function favorites() {
  return cek(await fetch(`${BASE}/favorites`));
}

export const exportUrl = (src, kind) => `${BASE}/export?src=${encodeURIComponent(src)}&kind=${kind}`;

async function postJson(path, body) {
  return cek(
    await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
  );
}

export const kirimZotero = (src) => postJson("/zotero", { src });
export const bukaFolder = (src) => postJson("/open-folder", { src });
export const simpanNote = (libId, uid, teks) => postJson("/note", { lib_id: libId, uid, teks });
export const kirimNotion = (src, token, page) => postJson("/notion", { src, token, page });
export const verifikasiNotion = (token) => postJson("/notion/verify", { token });

export async function jaringanSitasi(src) {
  return cek(await fetch(`${BASE}/network?src=${encodeURIComponent(src)}`));
}

export const asistenAI = (data) => postJson("/ai", data);

export async function cekUpdate(paksa = false) {
  return cek(await fetch(`${BASE}/update/check${paksa ? "?paksa=1" : ""}`));
}
export const unduhPembaruan = (url) => postJson("/update/download", { url });
export const pasangPembaruan = (lokasi) => postJson("/update/install", { lokasi });

// ============================ Pencari Halaman Sitasi ============================
export const parseRis = (teks_ris) => postJson("/citation-page/parse-ris", { teks_ris });
export const searchCitationPageSingle = (item, query_kutipan = "") =>
  postJson("/citation-page/search-single", { item, query_kutipan });
export const searchCitationPageBatch = (items, query_kutipan = "") =>
  postJson("/citation-page/search-batch", { items, query_kutipan });
export const scanPdfCitation = (pdf_base64, query_kutipan, start_page_jurnal = "") =>
  postJson("/citation-page/scan-pdf", { pdf_base64, query_kutipan, start_page_jurnal });

export async function unduhBlobRis(items) {
  const res = await fetch(`${BASE}/citation-page/export-ris`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });
  if (!res.ok) throw new Error("Gagal mengunduh berkas RIS");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "Referensia_Sitasi_Lengkap.ris";
  a.click();
  URL.revokeObjectURL(url);
}

export async function unduhBlobDocx(items, query_kutipan = "") {
  const res = await fetch(`${BASE}/citation-page/export-docx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items, query_kutipan }),
  });
  if (!res.ok) throw new Error("Gagal mengunduh berkas DOCX");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "Referensia_Rekap_Halaman.docx";
  a.click();
  URL.revokeObjectURL(url);
}
