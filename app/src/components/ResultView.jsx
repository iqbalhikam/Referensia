import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, SectionTitle, Chip, ScoreBadge, Label, SalinBtn, Field, inputCls } from "./ui.jsx";
import {
  Ikon, ArrowRight, BookOpen, Check, CheckCircle2, ChevronDown, Download, FileArchive,
  FileCode2, FileSpreadsheet, FileText, Flag, FolderOpen, Globe2, Link2, NotebookPen,
  RotateCcw, Search, Star, StickyNote, TrendingUp, TriangleAlert, Zap,
} from "./icons.jsx";
import { toggleFavorit, exportUrl, kirimZotero, bukaFolder, simpanNote, kirimNotion, verifikasiNotion } from "../api.js";

const NAMA_JENIS = {
  article: "Artikel", review: "Artikel Review", book: "Buku", "book-chapter": "Bab Buku",
  dissertation: "Skripsi/Tesis/Disertasi", preprint: "Preprint", report: "Laporan",
};

function penulisSingkat(p) {
  if (!p || !p.length) return "-";
  if (p.length === 1) return p[0];
  if (p.length === 2) return `${p[0]} & ${p[1]}`;
  return `${p[0]} dkk.`;
}

function teksMetode(m) {
  if (!m) return "-";
  const b = [m.pendekatan, m.desain, m.sampel, (m.analisis || []).join(", "), (m.instrumen || []).join(", ")].filter(Boolean);
  return b.length ? b.join(" · ") : "-";
}

function JudulBagian({ ikon, children, color = "text-indigo" }) {
  return (
    <SectionTitle color={color}>
      <span className="inline-flex items-center gap-2">
        <Ikon as={ikon} size={15} />
        {children}
      </span>
    </SectionTitle>
  );
}

function CatatanBox({ uid, note, warna, onNote }) {
  const [draft, setDraft] = useState(note || "");
  const [status, setStatus] = useState("");
  async function simpan() {
    setStatus("menyimpan…");
    try {
      await onNote(uid, draft);
      setStatus("Tersimpan");
      setTimeout(() => setStatus(""), 1500);
    } catch (e) {
      setStatus(`gagal: ${e.message}`);
    }
  }
  return (
    <div className="pt-1" onClick={(e) => e.stopPropagation()}>
      <span className={`font-bold ${warna}`}>Catatan pribadi: </span>
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="mis. dipakai di bab 2, metode cocok untuk penelitianku…"
        className="w-full mt-1.5 bg-bg/60 border border-line rounded-xl px-3 py-2 text-[12.5px] text-teks placeholder:text-abu/50 outline-none focus:border-indigo/60 min-h-16 resize-y"
      />
      <div className="flex items-center gap-2 mt-1">
        <button
          type="button"
          onClick={simpan}
          className="text-[11px] font-bold border border-line rounded-lg px-2.5 py-1 text-abu hover:text-indigo hover:border-indigo/50 transition-colors"
        >
          Simpan catatan
        </button>
        <span className="text-[11px] text-abu inline-flex items-center gap-1">
          {status === "Tersimpan" && <Ikon as={Check} size={12} className="text-emerald-400" />}
          {status || "Ikut terbawa ke ekspor Excel & Markdown"}
        </span>
      </div>
    </div>
  );
}

function BarisReferensi({ r, warna, fav, onFav, note, onNote }) {
  const [buka, setBuka] = useState(false);
  return (
    <>
      <tr
        onClick={() => setBuka(!buka)}
        className="border-b border-line cursor-pointer hover:bg-panel2/60 transition-colors align-top"
      >
        <td className="px-3 py-3 text-abu whitespace-nowrap">
          <button
            type="button"
            title={fav ? "Hapus dari favorit" : "Tandai favorit"}
            onClick={(e) => { e.stopPropagation(); onFav(r.uid, !fav); }}
            className={`mr-1.5 transition-colors ${fav ? "text-amber" : "text-abu/40 hover:text-amber"}`}
          >
            <Ikon as={Star} size={16} className={fav ? "fill-current" : ""} />
          </button>
          {r.no}
        </td>
        <td className="px-3 py-3"><ScoreBadge skor={r.skor} /></td>
        <td className="px-3 py-3 min-w-64">
          <div className="font-bold text-[13.5px] leading-snug">
            {note && <Ikon as={StickyNote} size={13} className="text-amber mr-1" title="Ada catatan pribadi" />}
            {r.judul}
          </div>
          <div className="text-abu text-[12px] mt-1">
            {penulisSingkat(r.penulis)}{r.sumber ? ` — ${r.sumber}` : ""}
          </div>
          {(r.doaj || r.sinta || r.duplikat) && (
            <div className="flex gap-1.5 mt-1.5 flex-wrap">
              {r.doaj && (
                <span className="text-[10px] font-bold uppercase tracking-wider border border-emerald-500/40 bg-emerald-500/10 text-emerald-400 rounded-full px-2 py-0.5">
                  DOAJ
                </span>
              )}
              {r.sinta && (
                <span className="text-[10px] font-bold uppercase tracking-wider border border-indigo/40 bg-indigo/10 text-indigo rounded-full px-2 py-0.5">
                  SINTA {r.sinta}
                </span>
              )}
              {r.duplikat && (
                <span
                  title={`Sudah pernah diambil di pencarian: ${r.duplikat.topik}`}
                  className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider border border-amber/50 bg-amber/10 text-amber rounded-full px-2 py-0.5"
                >
                  <Ikon as={RotateCcw} size={10} />
                  pernah diambil
                </span>
              )}
            </div>
          )}
        </td>
        <td className="px-3 py-3 text-[13px]">{r.tahun || "-"}</td>
        <td className="px-3 py-3 text-[13px] whitespace-nowrap">{NAMA_JENIS[r.jenis] || r.jenis}</td>
        <td className="px-3 py-3 text-[12px] max-w-40">
          {r.doi ? (
            <a
              href={`https://doi.org/${r.doi}`} target="_blank" rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-indigo hover:underline break-all"
            >
              {r.doi}
            </a>
          ) : "-"}
        </td>
        <td className="px-3 py-3 text-center">
          {r.pdf ? <Ikon as={Check} size={15} className="text-emerald-500" /> : "—"}
        </td>
        <td className="px-2 py-3 text-abu">
          <motion.span animate={{ rotate: buka ? 180 : 0 }} className="inline-block">
            <Ikon as={ChevronDown} size={14} />
          </motion.span>
        </td>
      </tr>
      <AnimatePresence>
        {buka && (
          <tr>
            <td colSpan={8} className="px-4 pb-4 bg-panel2/40">
              <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="text-[13px] leading-relaxed space-y-2 pt-2"
              >
                <div>
                  <span className={`font-bold ${warna}`}>Penulis lengkap: </span>
                  {r.penulis?.join(", ") || "-"}
                </div>
                {r.penerbit && <div><span className={`font-bold ${warna}`}>Penerbit: </span>{r.penerbit}</div>}
                <div>
                  <span className={`font-bold ${warna}`}>Kata kunci cocok: </span>
                  {r.kata_cocok?.length ? r.kata_cocok.map((k) => <Chip key={k}>{k}</Chip>) : "-"}
                </div>
                <div>
                  <span className={`font-bold ${warna}`}>Ditemukan via: </span>{r.asal}
                  {r.pdf ? ` · PDF via ${r.sumber_pdf || "Open Access"}` : ""}
                  {` · Sitasi: ${r.sitasi ?? 0}`}
                </div>
                <div>
                  <span className={`font-bold ${warna}`}>Indeks kualitas: </span>
                  {r.doaj || r.sinta
                    ? [r.doaj && "DOAJ", r.sinta && `SINTA ${r.sinta}`].filter(Boolean).join(" · ")
                    : "tidak terdeteksi (bukan berarti buruk)"}
                </div>
                {r.duplikat && (
                  <div className="inline-flex items-center gap-1.5 text-amber">
                    <Ikon as={RotateCcw} size={13} />
                    Sudah pernah diambil di pencarian: <b>{r.duplikat.topik}</b>
                  </div>
                )}
                {r.ringkasan && (
                  <div><span className={`font-bold ${warna}`}>Ringkasan: </span>{r.ringkasan}</div>
                )}
                {teksMetode(r.metode) !== "-" && (
                  <div><span className={`font-bold ${warna}`}>Metode: </span>{teksMetode(r.metode)}</div>
                )}
                {r.hasil_utama && (
                  <div><span className={`font-bold ${warna}`}>Hasil utama: </span>{r.hasil_utama}</div>
                )}
                {r.apa && (
                  <div className="space-y-1.5 pt-1">
                    <div className="flex items-start gap-2">
                      <span className="text-abu text-[12px] flex-1">{r.apa}</span>
                      <SalinBtn teks={r.apa}>APA</SalinBtn>
                    </div>
                    {r.ieee && (
                      <div className="flex items-start gap-2">
                        <span className="text-abu text-[12px] flex-1">{r.ieee}</span>
                        <SalinBtn teks={r.ieee}>IEEE</SalinBtn>
                      </div>
                    )}
                  </div>
                )}
                <div className="text-abu">{r.abstrak || "Abstrak tidak tersedia."}</div>
                <CatatanBox uid={r.uid} note={note} warna={warna} onNote={onNote} />
              </motion.div>
            </td>
          </tr>
        )}
      </AnimatePresence>
    </>
  );
}

function PanduanImpor() {
  const [tab, setTab] = useState("mendeley");
  return (
    <Card className="mt-8">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-3">
        <JudulBagian ikon={BookOpen}>Cara Masuk ke Reference Manager</JudulBagian>
        <div className="inline-flex rounded-xl bg-bg/60 border border-line/60 p-1">
          {[["mendeley", "Mendeley"], ["zotero", "Zotero"]].map(([val, label]) => (
            <button
              key={val}
              type="button"
              onClick={() => setTab(val)}
              className={`px-4 py-1.5 text-[13px] font-medium rounded-lg transition-colors ${
                tab === val ? "bg-indigodeep/25 border border-indigo/40 text-teks" : "text-abu hover:text-teks/80"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {tab === "mendeley" ? (
        <div className="text-sm text-abu space-y-2 leading-relaxed">
          <p>
            <b className="text-teks">Cara cepat:</b> klik <b className="text-teks">“Buka folder hasil”</b> di atas →
            seret PDF dari folder <b className="text-teks">PDF/</b> ke jendela Mendeley Reference Manager.
          </p>
          <p>
            <b className="text-teks">Impor metadata:</b> ekstrak ZIP → Mendeley Reference Manager →{" "}
            <i>File → Import library → RIS (.ris)</i> → pilih{" "}
            <b className="text-teks">01_IMPOR_REFERENSI.ris</b>, lalu seret PDF agar full-text menempel.
            Tag <b className="text-indigo">Nasional</b> / <b className="text-amber">Internasional</b> ikut terbawa.
          </p>
          <p>
            <b className="text-teks">Tanpa file:</b> salin isi <b className="text-teks">daftar_DOI.txt</b> →
            Mendeley → <b className="text-teks">Add new</b> → tambah lewat DOI.
          </p>
        </div>
      ) : (
        <div className="text-sm text-abu space-y-2 leading-relaxed">
          <p>
            <b className="text-teks">Cara cepat:</b> buka aplikasi Zotero desktop, lalu klik{" "}
            <b className="text-teks">“Kirim ke Zotero”</b> di atas — semua referensi langsung masuk
            beserta tag kategori.
          </p>
          <p>
            <b className="text-teks">Lewat file:</b> ekstrak ZIP → Zotero → <i>File → Import</i> → pilih{" "}
            <b className="text-teks">01_IMPOR_REFERENSI.ris</b> → centang{" "}
            <i>“Copy files to the Zotero storage folder”</i> agar PDF ikut tersimpan.
          </p>
        </div>
      )}
      <p className="text-[12px] text-abu mt-3 border-t border-line/60 pt-3">
        Isi ZIP: PDF per kategori, RIS, BibTeX, daftar DOI, daftar pustaka APA/IEEE (txt & Word),
        matriks literatur Excel, CSV, laporan HTML, dan BACA_DULU.txt.
      </p>
    </Card>
  );
}

export default function ResultView({ result, src, libId, initialFav = [], initialNotes = {}, zipHref, onReset, onAnalisis }) {
  const [fav, setFav] = useState(() => new Set(initialFav));
  const [notes, setNotes] = useState(initialNotes);
  const [pesan, setPesan] = useState("");
  const [zoteroSibuk, setZoteroSibuk] = useState(false);
  const [notionBuka, setNotionBuka] = useState(false);
  const [notionToken, setNotionToken] = useState(() => localStorage.getItem("referensia-notion-token") || "");
  const [notionPage, setNotionPage] = useState(() => localStorage.getItem("referensia-notion-page") || "");
  const [notionSibuk, setNotionSibuk] = useState(false);
  const [notionUrl, setNotionUrl] = useState("");
  const [notionCek, setNotionCek] = useState(null);
  const [notionVerifSibuk, setNotionVerifSibuk] = useState(false);
  const kats = ["Nasional", "Internasional"].filter((k) => result.hasil[k]?.length);
  const semua = kats.flatMap((k) => result.hasil[k]);
  const rataSkor = semua.length
    ? (semua.reduce((a, r) => a + r.skor, 0) / semua.length).toFixed(1)
    : 0;
  const semuaPas = Object.entries(result.target).every(
    ([kat, t]) => t <= 0 || (result.hasil[kat]?.length || 0) === t
  );
  const tahunAda = semua.map((r) => r.tahun).filter(Boolean);
  const rentang = tahunAda.length ? `${Math.min(...tahunAda)}–${Math.max(...tahunAda)}` : "-";
  const tanpaAbstrak = semua.filter((r) => !(r.abstrak || "").trim()).length;

  async function ubahFav(uid, on) {
    setFav((prev) => {
      const baru = new Set(prev);
      if (on) baru.add(uid); else baru.delete(uid);
      return baru;
    });
    try {
      await toggleFavorit(libId, uid, on);
    } catch (e) {
      setPesan(`Favorit gagal disimpan: ${e.message}`);
    }
  }

  async function ubahNote(uid, teks) {
    await simpanNote(libId, uid, teks);
    setNotes((prev) => {
      const baru = { ...prev };
      if (teks.trim()) baru[uid] = teks.trim(); else delete baru[uid];
      return baru;
    });
  }

  async function unduhEkspor(kind, nama) {
    setPesan("");
    try {
      const res = await fetch(exportUrl(src, kind));
      if (!res.ok) {
        let detail = `HTTP ${res.status}`;
        try {
          detail = (await res.json()).detail || detail;
        } catch {}
        if (res.status === 404 && detail === "Not Found") {
          detail = "Fitur ini belum ada di server yang berjalan — restart server Python (server.py) lalu coba lagi.";
        }
        throw new Error(detail);
      }
      const blob = await res.blob();
      const m = (res.headers.get("content-disposition") || "").match(/filename="?([^";]+)"?/);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = m ? m[1] : nama;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setPesan(`Ekspor gagal: ${e.message}`);
    }
  }

  async function hubungkanNotion() {
    setPesan("");
    setNotionCek(null);
    setNotionVerifSibuk(true);
    try {
      const d = await verifikasiNotion(notionToken.trim());
      setNotionCek(d);
      localStorage.setItem("referensia-notion-token", notionToken.trim());
      if (d.halaman?.length === 1 && !notionPage.trim()) setNotionPage(d.halaman[0].url);
    } catch (e) {
      const m = e.message === "Not Found"
        ? "Fitur ini belum ada di server yang berjalan — restart server Python (server.py) lalu coba lagi."
        : e.message;
      setPesan(m);
    } finally {
      setNotionVerifSibuk(false);
    }
  }

  async function keNotion() {
    setPesan("");
    setNotionUrl("");
    setNotionSibuk(true);
    try {
      const d = await kirimNotion(src, notionToken.trim(), notionPage.trim());
      localStorage.setItem("referensia-notion-token", notionToken.trim());
      localStorage.setItem("referensia-notion-page", notionPage.trim());
      setNotionUrl(d.url || "");
      setPesan("Halaman Notion dibuat berisi matriks literatur + daftar pustaka APA.");
    } catch (e) {
      setPesan(e.message);
    } finally {
      setNotionSibuk(false);
    }
  }

  async function keZotero() {
    setZoteroSibuk(true);
    setPesan("");
    try {
      const d = await kirimZotero(src);
      setPesan(`${d.jumlah} referensi terkirim ke Zotero. Cek aplikasi Zotero-mu.`);
    } catch (e) {
      setPesan(e.message);
    } finally {
      setZoteroSibuk(false);
    }
  }

  async function keFolder() {
    setPesan("");
    try {
      await bukaFolder(src);
      setPesan("Folder hasil dibuka di Explorer — seret PDF ke Mendeley, atau impor file RIS.");
    } catch (e) {
      setPesan(e.message);
    }
  }

  const btnCls =
    "rounded-xl border border-line px-4 py-2.5 text-[13px] font-bold text-abu hover:text-teks hover:border-indigo/60 transition-colors text-center";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      className="max-w-5xl mx-auto px-5 py-10"
    >
      <div className="mb-8">
        <Label>Hasil pencarian</Label>
        <h1 className="font-display text-3xl font-semibold text-teks mt-2 leading-snug">
          {result.topik}
        </h1>
        <p className="text-sm text-abu mt-2 inline-flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="inline-flex items-center gap-1.5"><Ikon as={Flag} size={13} />{result.topik_id}</span>
          <span className="inline-flex items-center gap-1.5"><Ikon as={Globe2} size={13} />{result.topik_en}</span>
        </p>
      </div>

      <div
        className={`rounded-2xl border-2 p-6 text-center ${
          semuaPas ? "border-emerald-500/60 bg-emerald-500/5" : "border-amber-500/60 bg-amber-500/5"
        }`}
      >
        <div className="inline-flex items-center gap-2 text-xl font-black mb-4">
          {semuaPas ? (
            <><Ikon as={CheckCircle2} size={22} className="text-emerald-500" />JUMLAH REFERENSI PAS SESUAI PERMINTAAN</>
          ) : (
            <><Ikon as={TriangleAlert} size={22} className="text-amber-500" />ADA KATEGORI YANG BELUM PAS — LIHAT CATATAN</>
          )}
        </div>
        <div className="flex gap-4 justify-center flex-wrap">
          {Object.entries(result.target).filter(([, t]) => t > 0).map(([kat, t]) => {
            const n = result.hasil[kat]?.length || 0;
            const warna = kat === "Nasional" ? "text-indigo border-indigo" : "text-amber border-amber";
            return (
              <div key={kat} className={`bg-panel border-2 rounded-2xl px-8 py-4 ${warna.split(" ")[1]}`}>
                <div className="inline-flex items-center gap-1.5 text-sm text-abu">
                  <Ikon as={kat === "Nasional" ? Flag : Globe2} size={13} />
                  {kat.toUpperCase()}
                </div>
                <div className={`text-4xl font-black ${warna.split(" ")[0]}`}>{n}/{t}</div>
                <div className="inline-flex items-center gap-1.5 text-sm">
                  {n === t ? (
                    <><Ikon as={CheckCircle2} size={14} className="text-emerald-500" />PAS</>
                  ) : (
                    <><Ikon as={TriangleAlert} size={14} className="text-amber-500" />KURANG</>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-5">
        {[
          ["Total referensi", result.total],
          ["PDF legal", `${result.jumlah_pdf}/${result.total}`],
          ["Rata-rata skor", `${rataSkor}/100`],
          ["Waktu", `${Math.floor(result.durasi_detik / 60)}m ${result.durasi_detik % 60}s`],
        ].map(([label, nilai]) => (
          <Card key={label} className="text-center py-4">
            <div className="text-2xl font-black gradient-text">{nilai}</div>
            <div className="text-[12px] text-abu mt-1">{label}</div>
          </Card>
        ))}
      </div>

      {result.prisma && (
        <Card className="mt-5">
          <div className="flex items-start justify-between gap-3 flex-wrap mb-4">
            <JudulBagian ikon={Search}>Alur seleksi literatur (PRISMA)</JudulBagian>
            <button
              onClick={() => unduhEkspor("laporan_docx", "Referensia_laporan_tinjauan.docx")}
              className={`${btnCls} inline-flex items-center justify-center gap-2`}
            >
              <Ikon as={FileText} size={14} />
              Laporan tinjauan (Word)
            </button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            {[
              ["Ditemukan", result.prisma.ditarik, "OpenAlex · Crossref · dork · snowball"],
              ["Duplikat dihapus", result.prisma.duplikat, "DOI / judul sama"],
              ["Predator disaring", result.prisma.predator, "penerbit terindikasi"],
              ["Dinilai kelayakan", result.prisma.dinilai, "relevansi & PDF legal"],
              ["Dimasukkan", result.prisma.masuk, "masuk matriks"],
            ].map(([label, nilai, ket], i) => (
              <div key={label} className="rounded-xl border border-line bg-bg/40 px-3 py-3">
                <div className="text-[11px] font-bold uppercase tracking-wider text-abu">
                  {i + 1}. {label}
                </div>
                <div className={`text-2xl font-black mt-1 ${i === 4 ? "text-emerald-500" : "text-teks"}`}>
                  {nilai ?? 0}
                </div>
                <div className="text-[11px] text-abu mt-0.5">{ket}</div>
              </div>
            ))}
          </div>
          <p className="text-[12px] text-abu mt-3">
            Nasional {result.prisma.per_kategori?.Nasional?.masuk ?? 0} · Internasional{" "}
            {result.prisma.per_kategori?.Internasional?.masuk ?? 0} ·{" "}
            {result.prisma.tanpa_pdf} referensi tanpa PDF legal. Angka dihitung dari tahap pencarian
            yang benar-benar dijalankan, bukan perkiraan.
          </p>
        </Card>
      )}

      <div className="mt-6 flex flex-col sm:flex-row gap-3">
        <a
          href={zipHref}
          className="gradient-btn flex-1 inline-flex items-center justify-center gap-2.5 text-center rounded-2xl py-4 text-lg font-black text-white shadow-lg shadow-indigo/20"
        >
          <Ikon as={Download} size={20} />
          Unduh ZIP (siap Mendeley & Zotero)
        </a>
        <button
          onClick={onReset}
          className="sm:w-56 inline-flex items-center justify-center gap-2 rounded-2xl py-4 font-bold border border-line text-abu hover:text-teks hover:border-indigo transition-colors"
        >
          <Ikon as={Search} size={17} />
          Cari Topik Lain
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-3">
        <button onClick={keZotero} disabled={zoteroSibuk} className={`${btnCls} inline-flex items-center justify-center gap-2 disabled:opacity-50`}>
          {!zoteroSibuk && <Ikon as={Zap} size={14} />}
          {zoteroSibuk ? "Mengirim…" : "Kirim ke Zotero"}
        </button>
        <button onClick={() => setNotionBuka(!notionBuka)} className={`${btnCls} inline-flex items-center justify-center gap-2`}>
          <Ikon as={Link2} size={14} />
          Kirim ke Notion
        </button>
        <button onClick={onAnalisis} className={`${btnCls} inline-flex items-center justify-center gap-2`}>
          <Ikon as={TrendingUp} size={14} />
          Analisis lanjut (tren · sitasi · AI)
        </button>
        <button onClick={keFolder} className={`${btnCls} inline-flex items-center justify-center gap-2`}>
          <Ikon as={FolderOpen} size={14} />
          Buka folder hasil
        </button>
        <button onClick={() => unduhEkspor("matriks_xlsx", "Referensia_matriks.xlsx")} className={`${btnCls} inline-flex items-center justify-center gap-2`}>
          <Ikon as={FileSpreadsheet} size={14} />
          Matriks literatur (Excel)
        </button>
        <button onClick={() => unduhEkspor("matriks_docx", "Referensia_matriks.docx")} className={`${btnCls} inline-flex items-center justify-center gap-2`}>
          <Ikon as={FileText} size={14} />
          Matriks literatur (Word · Notion)
        </button>
        <button onClick={() => unduhEkspor("laporan_docx", "Referensia_laporan_tinjauan.docx")} className={`${btnCls} inline-flex items-center justify-center gap-2`}>
          <Ikon as={FileText} size={14} />
          Laporan tinjauan (Word · Bab 2)
        </button>
        <button onClick={() => unduhEkspor("markdown", "Referensia.md")} className={`${btnCls} inline-flex items-center justify-center gap-2`}>
          <Ikon as={FileCode2} size={14} />
          Markdown (Obsidian)
        </button>
        <button onClick={() => unduhEkspor("apa_docx", "Referensia_APA.docx")} className={`${btnCls} inline-flex items-center justify-center gap-2`}>
          <Ikon as={FileText} size={14} />
          Daftar pustaka APA (Word)
        </button>
        <button onClick={() => unduhEkspor("ieee_docx", "Referensia_IEEE.docx")} className={`${btnCls} inline-flex items-center justify-center gap-2`}>
          <Ikon as={FileText} size={14} />
          Daftar pustaka IEEE (Word)
        </button>
        <button onClick={() => unduhEkspor("ris", "Referensia.ris")} className={`${btnCls} inline-flex items-center justify-center gap-2`}>
          <Ikon as={FileArchive} size={14} />
          File RIS saja
        </button>
      </div>

      {notionBuka && (
        <Card className="mt-3">
          <SectionTitle color="text-indigo">
            <span className="inline-flex items-center gap-2">
              <Ikon as={Link2} size={15} />
              Kirim langsung ke Notion
            </span>
          </SectionTitle>
          <p className="text-[12.5px] text-abu mb-3 leading-relaxed">
            Sekali saja per akun Notion: buat integration → hubungkan → pilih halaman. Token dan halaman
            tersimpan di perangkat ini, jadi pencarian berikutnya tinggal klik{" "}
            <b className="text-teks">Kirim ke Notion</b>.
          </p>
          <details className="mb-4 text-[12.5px] text-abu">
            <summary className="cursor-pointer font-semibold text-teks/80">Cara membuat token (sekitar 2 menit)</summary>
            <ol className="list-decimal pl-5 space-y-1.5 mt-2 leading-relaxed">
              <li>
                Buat integration di{" "}
                <a href="https://www.notion.so/my-integrations" target="_blank" rel="noreferrer" className="text-indigo hover:underline">
                  notion.so/my-integrations
                </a>{" "}
                → <i>New integration</i> → salin <b className="text-teks">Internal Integration Secret</b>.
              </li>
              <li>
                Buka halaman Notion tujuan → <b className="text-teks">⋯</b> (kanan atas) →{" "}
                <b className="text-teks">Connections</b> → hubungkan integration tadi.
              </li>
              <li>Tempel token di bawah → klik <b className="text-teks">Hubungkan</b> → pilih halaman dari daftar.</li>
            </ol>
          </details>
          <div className="grid sm:grid-cols-[1fr_auto] gap-2 items-end">
            <Field label="Langkah 1 · Token integration">
              <input
                type="password" className={inputCls} value={notionToken}
                onChange={(e) => { setNotionToken(e.target.value); setNotionCek(null); }}
                placeholder="secret_… atau ntn_…"
              />
            </Field>
            <button
              onClick={hubungkanNotion} disabled={notionVerifSibuk || !notionToken.trim()}
              className="rounded-xl px-4 py-[11px] text-[13px] font-bold border border-line text-teks hover:border-indigo hover:text-indigo transition-colors disabled:opacity-50"
            >
              {notionVerifSibuk ? "Mengecek…" : "Hubungkan"}
            </button>
          </div>
          {notionCek && (
            <div className="mt-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-2.5 text-[12.5px] leading-relaxed">
              <span className="inline-flex items-center gap-1.5 font-bold text-emerald-500">
                <Ikon as={CheckCircle2} size={14} />
                Terhubung
              </span>{" "}
              ke workspace{" "}
              <b className="text-teks">{notionCek.ruang || "(tanpa nama)"}</b>
              {notionCek.bot ? <> sebagai <b className="text-teks">{notionCek.bot}</b></> : null}
              {" · "}{notionCek.halaman.length} halaman sudah dibagikan.
              {notionCek.catatan && <span className="block mt-1 text-amber">{notionCek.catatan}</span>}
            </div>
          )}
          <div className="mt-3">
            <Field label="Langkah 2 · Halaman tujuan">
              <input
                list="notion-halaman" className={inputCls} value={notionPage}
                onChange={(e) => setNotionPage(e.target.value)}
                placeholder="Pilih dari daftar, atau tempel URL halaman Notion"
              />
              <datalist id="notion-halaman">
                {(notionCek?.halaman || []).map((h) => (
                  <option key={h.url} value={h.url}>
                    {h.judul}{h.terakhir ? ` · ${h.terakhir}` : ""}
                  </option>
                ))}
              </datalist>
            </Field>
          </div>
          <div className="flex items-center gap-3 mt-3 flex-wrap">
            <button
              onClick={keNotion} disabled={notionSibuk || !notionToken.trim() || !notionPage.trim()}
              className="gradient-btn rounded-xl px-5 py-2.5 text-[13px] font-bold text-white disabled:opacity-50"
            >
              {notionSibuk ? "Mengirim…" : "Langkah 3 · Kirim ke Notion"}
            </button>
            {notionUrl && (
              <a href={notionUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[12.5px] font-bold text-indigo hover:underline">
                Buka halaman Notion
                <Ikon as={ArrowRight} size={13} />
              </a>
            )}
            <span className="text-[11.5px] text-abu">
              Token disimpan hanya di perangkat ini dan dipakai langsung ke api.notion.com.
            </span>
          </div>
        </Card>
      )}

      <div className="flex gap-3 mt-3 justify-center">
        <SalinBtn teks={semua.map((r) => r.apa).filter(Boolean).join("\n\n")}>semua APA</SalinBtn>
        <SalinBtn teks={semua.map((r) => r.ieee).filter(Boolean).join("\n")}>semua IEEE</SalinBtn>
      </div>
      <p className="text-center text-[12px] text-abu mt-2 inline-flex w-full items-center justify-center gap-1.5">
        Rentang tahun hasil: {rentang} ·
        <Ikon as={Star} size={12} className="fill-current text-amber" />
        = favorit ({fav.size})
      </p>
      {pesan && (
        <div className="mt-3 border border-indigo/40 bg-indigo/10 text-teks/90 rounded-xl px-4 py-3 text-sm text-center">
          {pesan}
        </div>
      )}

      {result.catatan?.length > 0 && (
        <Card className="mt-6 border-amber-500/40">
          <JudulBagian ikon={NotebookPen} color="text-amber-400">Catatan</JudulBagian>
          <ul className="text-sm text-abu space-y-1 list-disc pl-5">
            {result.catatan.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </Card>
      )}

      {kats.map((kat) => {
        const warna = kat === "Nasional" ? "text-indigo" : "text-amber";
        const border = kat === "Nasional" ? "border-indigo/40" : "border-amber/40";
        const rows = result.hasil[kat];
        const teratas = [...rows].sort((a, b) => (b.sitasi || 0) - (a.sitasi || 0)).slice(0, 3);
        return (
          <div key={kat} className="mt-8">
            <h2 className={`text-xl font-black mb-3 ${warna} inline-flex items-center gap-2`}>
              <Ikon as={kat === "Nasional" ? Flag : Globe2} size={18} />
              Referensi {kat} ({rows.length})
            </h2>

            <Card className={`mb-4 ${border}`}>
              <div className="text-sm space-y-2">
                <div>
                  <span className="font-bold text-abu">Kata kunci: </span>
                  {(result.kunci_kat[kat] || []).map((k) => <Chip key={k}>{k}</Chip>)}
                </div>
                <div>
                  <span className="font-bold text-abu">Tema yang sering muncul: </span>
                  {(result.tema_kat[kat] || []).length
                    ? result.tema_kat[kat].map((t) => <Chip key={t}>{t}</Chip>)
                    : "-"}
                </div>
                <div>
                  <span className="font-bold text-abu">Paling banyak disitasi:</span>
                  <ul className="list-disc pl-5 text-abu mt-1">
                    {teratas.map((r) => (
                      <li key={r.no}>{r.judul} ({r.tahun || "-"}) — {r.sitasi} sitasi</li>
                    ))}
                  </ul>
                </div>
              </div>
            </Card>

            <Card className="p-0 overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-line">
                    {["No", "Skor", "Judul & Penulis", "Tahun", "Jenis", "DOI", "PDF", ""].map((h, i) => (
                      <th key={i} className={`px-3 py-3 text-[12px] uppercase tracking-wide whitespace-nowrap ${warna}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <BarisReferensi
                      key={r.no} r={r} warna={warna} fav={fav.has(r.uid)} onFav={ubahFav}
                      note={notes[r.uid] || ""} onNote={ubahNote}
                    />
                  ))}
                </tbody>
              </table>
            </Card>
            <p className="text-[12px] text-abu mt-2 inline-flex items-center gap-1.5">
              Klik baris untuk melihat abstrak & detail · klik
              <Ikon as={Star} size={12} />
              untuk menandai favorit.
            </p>
          </div>
        );
      })}

      {semua.length > 0 && (
        <div className="mt-10">
          <h2 className="font-display text-xl font-semibold mb-1">Matriks literatur</h2>
          <p className="text-[12px] text-abu mb-3">
            Deteksi otomatis dari judul & abstrak — kolom kosong berarti tidak terdeteksi, bukan berarti tidak ada.
            Versi Excel bisa diunduh lewat tombol di atas.
          </p>
          {tanpaAbstrak > 0 && (
            <div className="flex items-start gap-2 border border-amber/40 bg-amber/10 text-teks/80 rounded-xl px-4 py-3 text-[12.5px] mb-3">
              <Ikon as={TriangleAlert} size={15} className="mt-0.5 text-amber" />
              <span>
                {tanpaAbstrak} dari {semua.length} referensi tidak menyediakan abstrak (dan tidak ditemukan di
                Semantic Scholar), jadi ringkasan/hasil utamanya bisa kosong. Metode tetap dideteksi dari judul.
              </span>
            </div>
          )}
          <Card className="p-0 overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-line">
                  {["No", "Judul", "Pendekatan", "Desain", "Sampel", "Analisis", "Instrumen", "Hasil utama"].map((h) => (
                    <th key={h} className="px-3 py-3 text-[12px] uppercase tracking-wide text-indigo whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {semua.map((r, i) => {
                  const m = r.metode || {};
                  return (
                    <tr key={i} className="border-b border-line align-top hover:bg-panel2/60 transition-colors">
                      <td className="px-3 py-3 text-abu">{i + 1}</td>
                      <td className="px-3 py-3 min-w-56 max-w-80 text-[12.5px] font-semibold leading-snug">{r.judul}</td>
                      <td className="px-3 py-3 text-[12.5px] whitespace-nowrap">{m.pendekatan || "—"}</td>
                      <td className="px-3 py-3 text-[12.5px]">{m.desain || "—"}</td>
                      <td className="px-3 py-3 text-[12.5px] whitespace-nowrap">{m.sampel || "—"}</td>
                      <td className="px-3 py-3 text-[12.5px]">{(m.analisis || []).join(", ") || "—"}</td>
                      <td className="px-3 py-3 text-[12.5px]">{(m.instrumen || []).join(", ") || "—"}</td>
                      <td className="px-3 py-3 text-[12.5px] max-w-72">{r.hasil_utama || "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        </div>
      )}

      <PanduanImpor />

      <div className="mt-8 rounded-2xl p-8 text-center text-white font-black text-2xl leading-snug bg-gradient-to-br from-indigodeep to-indigo shadow-lg shadow-indigo/25">
        MASUKKAN FILE DALAM ZIP KE MENDELEY / ZOTERO
        <div className="text-base font-bold mt-2 opacity-90">
          TERIMA KASIH SUDAH MEMAKAI REFERENSIA
        </div>
      </div>
    </motion.div>
  );
}