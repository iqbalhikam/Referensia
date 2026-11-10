import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Ikon,
  BookOpen,
  Copy,
  Check,
  Search,
  Download,
  Upload,
  FileText,
  Sparkles,
  RotateCcw,
  Link2,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Trash2,
  Library,
} from "./icons.jsx";
import { Card, SalinBtn, inputCls } from "./ui.jsx";
import {
  parseRis,
  searchCitationPageSingle,
  searchCitationPageBatch,
  scanPdfCitation,
  unduhBlobRis,
  unduhBlobDocx,
  library,
  libraryEntry,
} from "../api.js";

const CONTOH_RIS = `TY  - JOUR
TI  - The Effect of Problem-Based Learning on Students Critical Thinking Skills
AU  - Susanto, Ahmad
AU  - Rahmawati, Siti
PY  - 2021
JO  - Jurnal Pendidikan IPA Indonesia
VL  - 10
IS  - 2
SP  - 145
EP  - 158
DO  - 10.15294/jpii.v10i2.29876
ER  - 

TY  - JOUR
TI  - Artificial Intelligence in Higher Education: A Critical Systematic Review
AU  - Zawacki-Richter, Olaf
AU  - Marín, Victoria I.
AU  - Bond, Melissa
AU  - Gouverneur, Franziska
PY  - 2019
JO  - International Journal of Educational Technology in Higher Education
VL  - 16
IS  - 1
DO  - 10.1186/s41239-019-0171-0
ER  - 

TY  - JOUR
TI  - Pembelajaran Berdiferensiasi untuk Meningkatkan Pemahaman Konsep Siswa
AU  - Handayani, Fitri
AU  - Wulandari, Retno
PY  - 2022
JO  - Jurnal Basicedu
VL  - 6
IS  - 4
SP  - 5890
EP  - 5899
DO  - 10.31004/basicedu.v6i4.3120
ER  - `;

export default function CitationPageFinder({ onBack }) {
  const [items, setItems] = useState([]);
  const [namaBerkas, setNamaBerkas] = useState("");
  const [queryKutipan, setQueryKutipan] = useState("");
  const [sedangMemuat, setSedangMemuat] = useState(false);
  const [pesanStatus, setPesanStatus] = useState("");
  const [pesanGalat, setPesanGalat] = useState("");
  const [teksTempel, setTeksTempel] = useState("");
  const [bukaTempel, setBukaTempel] = useState(false);
  const [filterStatus, setFilterStatus] = useState("semua"); // semua, butuh, lengkap, ada_kutipan
  const [daftarPustakaLokal, setDaftarPustakaLokal] = useState([]);
  const [bukaPustakaModal, setBukaPustakaModal] = useState(false);
  const [detailItemKutipan, setDetailItemKutipan] = useState(null); // untuk modal cari kutipan per item
  const [kutipanPerItem, setKutipanPerItem] = useState("");
  const [pdfManualUpload, setPdfManualUpload] = useState(null);
  const [sedangScanItem, setSedangScanItem] = useState(false);

  const fileInputRef = useRef(null);
  const pdfInputRef = useRef(null);

  // Parse berkas RIS dari teks
  async function prosesTeksRis(teks, label = "berkas.ris") {
    setPesanGalat("");
    setPesanStatus("Mem-parsing entri RIS…");
    setSedangMemuat(true);
    try {
      const res = await parseRis(teks);
      if (!res.items || res.items.length === 0) {
        throw new Error("Tidak ditemukan rekaman referensi yang valid dalam berkas RIS.");
      }
      setItems(res.items);
      setNamaBerkas(label);
      setPesanStatus(`Berhasil memuat ${res.items.length} referensi dari ${label}`);
      setBukaTempel(false);
    } catch (e) {
      setPesanGalat(e.message || "Gagal memproses berkas RIS.");
      setPesanStatus("");
    } finally {
      setSedangMemuat(false);
    }
  }

  // Handle upload berkas .ris
  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const teks = event.target?.result;
      if (typeof teks === "string") {
        prosesTeksRis(teks, file.name);
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  // Handle Drag & Drop
  function handleDrop(e) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const teks = event.target?.result;
      if (typeof teks === "string") {
        prosesTeksRis(teks, file.name);
      }
    };
    reader.readAsText(file);
  }

  // Muat dari Pustaka Tersimpan
  async function bukaModalPustaka() {
    setPesanGalat("");
    try {
      const list = await library();
      setDaftarPustakaLokal(list || []);
      setBukaPustakaModal(true);
    } catch (e) {
      setPesanGalat("Gagal mengambil riwayat pustaka: " + e.message);
    }
  }

  async function pilihEntriPustaka(id, topik) {
    setBukaPustakaModal(false);
    setPesanStatus(`Mengambil data dari pencarian "${topik}"…`);
    setSedangMemuat(true);
    try {
      const entri = await libraryEntry(id);
      const refs = [
        ...(entri.result?.hasil?.Nasional || []),
        ...(entri.result?.hasil?.Internasional || []),
      ];
      if (!refs.length) throw new Error("Tidak ada referensi dalam pencarian ini.");

      // Konversi ke format item RIS
      const itemsBaru = refs.map((r, i) => {
        const sp = r.sp || "";
        const ep = r.ep || "";
        const hal = sp && ep && sp !== ep ? `${sp}–${ep}` : sp;
        return {
          uid: r.uid || `lib_${i + 1}`,
          no: i + 1,
          tipe: "JOUR",
          judul: r.judul,
          penulis: r.penulis || [],
          tahun: r.tahun,
          sumber: r.sumber,
          penerbit: r.penerbit,
          volume: r.volume || "",
          issue: r.issue || "",
          sp: sp,
          ep: ep,
          halaman_ada: hal,
          doi: r.doi || "",
          url: r.url || "",
          pdf_link: r.pdf ? `PDF/${r.kategori}/${r.pdf}` : "",
          abstrak: r.abstrak || "",
          status_halaman: hal ? "lengkap" : "belum_ada",
          hasil_cari: null,
        };
      });

      setItems(itemsBaru);
      setNamaBerkas(`Pustaka: ${topik}`);
      setPesanStatus(`Berhasil memuat ${itemsBaru.length} referensi.`);
    } catch (e) {
      setPesanGalat(e.message || "Gagal memuat pustaka.");
    } finally {
      setSedangMemuat(false);
    }
  }

  // Aksi Pencarian Halaman Batch (Search Semua)
  async function cariHalamanSemua() {
    if (!items.length) return;
    setSedangMemuat(true);
    setPesanGalat("");
    setPesanStatus(
      queryKutipan.trim()
        ? `Memindai metadata halaman & teks kutipan di PDF untuk ${items.length} referensi…`
        : `Mencari nomor halaman resmi (Crossref & OpenAlex) untuk ${items.length} referensi…`
    );

    try {
      const res = await searchCitationPageBatch(items, queryKutipan);
      if (res.items) {
        // Gabungkan hasil dengan state
        const mapHasil = new Map(res.items.map((it) => [it.uid, it]));
        setItems((prev) =>
          prev.map((it) => {
            const h = mapHasil.get(it.uid);
            if (!h) return it;
            return {
              ...it,
              sp: h.sp || it.sp,
              ep: h.ep || it.ep,
              halaman_rentang: h.halaman_rentang || it.halaman_rentang,
              volume: h.volume || it.volume,
              issue: h.issue || it.issue,
              sumber: h.sumber || it.sumber,
              doi: h.doi || it.doi,
              pdf_url: h.pdf_url || it.pdf_url,
              status_halaman: h.status_halaman,
              scan_pdf: h.scan_pdf,
              sitasi: h.sitasi,
            };
          })
        );
        setPesanStatus(
          `Selesai! Metadata halaman dan sitasi berhasil diperbarui.`
        );
      }
    } catch (e) {
      setPesanGalat("Gagal mencari halaman: " + e.message);
    } finally {
      setSedangMemuat(false);
    }
  }

  // Aksi Cari Halaman Single Item
  async function cariHalamanItem(item, teksKutipanKhusus = "") {
    setSedangMemuat(true);
    setPesanGalat("");
    try {
      const res = await searchCitationPageSingle(item, teksKutipanKhusus || queryKutipan);
      if (res.item) {
        const h = res.item;
        setItems((prev) =>
          prev.map((it) =>
            it.uid === item.uid
              ? {
                  ...it,
                  sp: h.sp || it.sp,
                  ep: h.ep || it.ep,
                  halaman_rentang: h.halaman_rentang || it.halaman_rentang,
                  volume: h.volume || it.volume,
                  issue: h.issue || it.issue,
                  sumber: h.sumber || it.sumber,
                  doi: h.doi || it.doi,
                  pdf_url: h.pdf_url || it.pdf_url,
                  status_halaman: h.status_halaman,
                  scan_pdf: h.scan_pdf,
                  sitasi: h.sitasi,
                }
              : it
          )
        );
        return h;
      }
    } catch (e) {
      setPesanGalat(`Gagal mencari halaman untuk "${item.judul}": ${e.message}`);
    } finally {
      setSedangMemuat(false);
    }
  }

  // Pemindaian PDF Manual jika user mengunggah PDF
  async function handleScanPdfManual() {
    if (!detailItemKutipan || !pdfManualUpload || !kutipanPerItem.trim()) {
      setPesanGalat("Pilih berkas PDF dan isi kalimat kutipan terlebih dahulu.");
      return;
    }

    setSedangScanItem(true);
    setPesanGalat("");

    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64 = e.target?.result;
        if (typeof base64 !== "string") return;

        try {
          const res = await scanPdfCitation(
            base64,
            kutipanPerItem,
            detailItemKutipan.sp || ""
          );

          if (res.scan) {
            setItems((prev) =>
              prev.map((it) => {
                if (it.uid === detailItemKutipan.uid) {
                  const updated = {
                    ...it,
                    scan_pdf: res.scan,
                  };
                  return updated;
                }
                return it;
              })
            );

            setDetailItemKutipan((prev) =>
              prev ? { ...prev, scan_pdf: res.scan } : null
            );
          }
        } catch (err) {
          setPesanGalat("Pemindaian PDF gagal: " + err.message);
        } finally {
          setSedangScanItem(false);
        }
      };
      reader.readAsDataURL(pdfManualUpload);
    } catch (err) {
      setPesanGalat("Gagal membaca berkas: " + err.message);
      setSedangScanItem(false);
    }
  }

  // Reset / Bersihkan
  function handleReset() {
    setItems([]);
    setNamaBerkas("");
    setQueryKutipan("");
    setPesanStatus("");
    setPesanGalat("");
  }

  // Filter items
  const itemsFiltered = items.filter((it) => {
    if (filterStatus === "butuh") {
      return !it.halaman_rentang && !it.sp && !it.halaman_ada;
    }
    if (filterStatus === "lengkap") {
      return Boolean(it.halaman_rentang || it.sp || it.halaman_ada);
    }
    if (filterStatus === "ada_kutipan") {
      return Boolean(it.scan_pdf && it.scan_pdf.ditemukan);
    }
    return true;
  });

  const jumlahLengkap = items.filter(
    (it) => it.halaman_rentang || it.sp || it.halaman_ada
  ).length;
  const jumlahKutipanDitemukan = items.filter(
    (it) => it.scan_pdf && it.scan_pdf.ditemukan
  ).length;

  return (
    <main className="max-w-6xl mx-auto px-5 py-8">
      {/* Header Halaman */}
      <div className="mb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo/10 border border-indigo/20 text-indigo text-[12px] font-semibold mb-2">
              <Ikon as={BookOpen} size={14} />
              Fitur Baru: Pencari Halaman Sitasi
            </div>
            <h1 className="text-2xl font-display font-extrabold tracking-tight text-teks">
              Pencari Halaman Sitasi Ilmiah
            </h1>
            <p className="text-sm text-abu mt-1 max-w-2xl leading-relaxed">
              Import berkas <code className="text-indigo bg-indigo/10 px-1 py-0.5 rounded text-[12px]">.ris</code> (Zotero, Mendeley, Scholar) lalu langsung search untuk melengkapi nomor halaman terbitan (SP–EP, Vol, No) serta mendeteksi halaman kutipan spesifik di PDF (hlm. X) secara otomatis.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {items.length > 0 && (
              <>
                <button
                  type="button"
                  onClick={() => unduhBlobRis(items)}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-panel border border-line text-teks hover:border-indigo/50 transition-colors"
                  title="Unduh berkas .ris baru dengan nomor halaman yang telah dilengkapi"
                >
                  <Ikon as={Download} size={14} />
                  Ekspor RIS Terupdate
                </button>
                <button
                  type="button"
                  onClick={() => unduhBlobDocx(items, queryKutipan)}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-indigo text-white hover:bg-indigodeep transition-colors"
                  title="Unduh berkas Microsoft Word berisi rekap halaman & sitasi"
                >
                  <Ikon as={FileText} size={14} />
                  Unduh Rekap Word (.docx)
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Alert Galat */}
      {pesanGalat && (
        <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm flex items-start gap-3">
          <Ikon as={AlertTriangle} size={18} className="shrink-0 mt-0.5" />
          <div className="flex-1">{pesanGalat}</div>
          <button
            onClick={() => setPesanGalat("")}
            className="text-xs text-rose-400/80 hover:text-rose-300 font-bold"
          >
            Tutup
          </button>
        </div>
      )}

      {/* Alert Status Info */}
      {pesanStatus && (
        <div className="mb-6 p-3.5 rounded-xl bg-indigo/10 border border-indigo/25 text-indigo text-sm flex items-center gap-2.5">
          {sedangMemuat ? (
            <Ikon as={Loader2} size={16} className="animate-spin shrink-0" />
          ) : (
            <Ikon as={CheckCircle2} size={16} className="shrink-0" />
          )}
          <span>{pesanStatus}</span>
        </div>
      )}

      {/* Bagian 1: Zona Import RIS (Jika belum ada items atau ingin ganti) */}
      {items.length === 0 ? (
        <Card className="p-8 text-center border-dashed border-2 border-line hover:border-indigo/50 transition-colors">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".ris,.txt"
            className="hidden"
          />

          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            className="py-6 cursor-pointer"
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="w-16 h-16 mx-auto rounded-2xl bg-indigo/10 border border-indigo/20 flex items-center justify-center text-indigo mb-4 shadow-inner">
              <Ikon as={Upload} size={28} />
            </div>
            <h2 className="text-lg font-bold text-teks mb-1">
              Tarik & Letakkan Berkas RIS di Sini
            </h2>
            <p className="text-sm text-abu mb-4">
              atau klik untuk memilih berkas dari komputer (.ris atau .txt)
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-4 border-t border-line/60">
            <button
              type="button"
              onClick={() => setBukaTempel(true)}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-panel border border-line text-teks hover:border-indigo/50 transition-colors inline-flex items-center gap-1.5"
            >
              <Ikon as={Copy} size={13} />
              Tempel Teks RIS
            </button>
            <button
              type="button"
              onClick={bukaModalPustaka}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-panel border border-line text-teks hover:border-indigo/50 transition-colors inline-flex items-center gap-1.5"
            >
              <Ikon as={Library} size={13} />
              Muat dari Pustaka Saya
            </button>
            <button
              type="button"
              onClick={() => prosesTeksRis(CONTOH_RIS, "contoh_referensi.ris")}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo/10 border border-indigo/30 text-indigo hover:bg-indigo/20 transition-colors inline-flex items-center gap-1.5"
            >
              <Ikon as={Sparkles} size={13} />
              Coba dengan Contoh RIS
            </button>
          </div>
        </Card>
      ) : (
        /* Bagian 2: Search Bar & Info Berkas */
        <div className="space-y-6">
          <Card className="p-5 bg-gradient-to-br from-panel/90 via-panel/80 to-indigodeep/10 border border-line">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-3 border-b border-line/60">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 inline-block animate-pulse" />
                <span className="text-xs font-bold text-teks">
                  {namaBerkas || "Daftar Referensi RIS"}
                </span>
                <span className="text-xs text-abu font-mono">
                  ({items.length} referensi dimuat)
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="text-xs font-semibold text-abu hover:text-indigo inline-flex items-center gap-1"
                >
                  <Ikon as={Upload} size={12} /> Ganti Berkas
                </button>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".ris,.txt"
                  className="hidden"
                />
                <span className="text-abu/40">|</span>
                <button
                  type="button"
                  onClick={handleReset}
                  className="text-xs font-semibold text-rose-400 hover:text-rose-300 inline-flex items-center gap-1"
                >
                  <Ikon as={Trash2} size={12} /> Bersihkan
                </button>
              </div>
            </div>

            {/* Input Pencarian Halaman Sitasi */}
            <div className="space-y-3">
              <label className="block">
                <span className="text-xs font-bold text-teks/90 mb-1.5 flex items-center gap-1.5">
                  <Ikon as={Search} size={14} className="text-indigo" />
                  Kata Kunci / Kalimat Kutipan yang Dicari di Dokumen (Opsional):
                </span>
                <div className="relative">
                  <input
                    type="text"
                    value={queryKutipan}
                    onChange={(e) => setQueryKutipan(e.target.value)}
                    placeholder='Contoh: "keterampilan berpikir kritis" atau "model problem based learning terbukti..."'
                    className={`${inputCls} pr-10`}
                  />
                  {queryKutipan && (
                    <button
                      type="button"
                      onClick={() => setQueryKutipan("")}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-abu hover:text-teks text-xs"
                    >
                      ✕
                    </button>
                  )}
                </div>
                <span className="text-[11.5px] text-abu block mt-1">
                  💡 <strong>Langsung Search:</strong> Klik tombol cari di bawah. Jika kolom kutipan diisi, sistem otomatis memindai PDF untuk menemukan nomor halaman tepat (hlm. X) tempat kalimat tersebut berada. Jika dikosongkan, sistem melengkapi nomor halaman resmi jurnal (Start–End Page, Volume, Issue) dari Crossref & OpenAlex.
                </span>
              </label>

              <div className="flex flex-wrap items-center gap-3 pt-2">
                <button
                  type="button"
                  disabled={sedangMemuat}
                  onClick={cariHalamanSemua}
                  className="px-5 py-2.5 rounded-xl font-bold text-sm bg-gradient-to-r from-indigo to-indigodeep text-white shadow-lg hover:shadow-indigo/25 hover:brightness-110 active:scale-95 disabled:opacity-50 transition-all inline-flex items-center gap-2"
                >
                  {sedangMemuat ? (
                    <>
                      <Ikon as={Loader2} size={16} className="animate-spin" />
                      Sedang Mencari Halaman…
                    </>
                  ) : (
                    <>
                      <Ikon as={Search} size={16} />
                      Cari Halaman Sitasi Sekarang
                    </>
                  )}
                </button>
              </div>
            </div>
          </Card>

          {/* Filter & Statistik Ringkas */}
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-1.5 bg-panel/80 border border-line rounded-xl p-1">
              <button
                type="button"
                onClick={() => setFilterStatus("semua")}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  filterStatus === "semua"
                    ? "bg-indigo/20 text-indigo font-bold border border-indigo/30"
                    : "text-abu hover:text-teks"
                }`}
              >
                Semua ({items.length})
              </button>
              <button
                type="button"
                onClick={() => setFilterStatus("butuh")}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  filterStatus === "butuh"
                    ? "bg-indigo/20 text-indigo font-bold border border-indigo/30"
                    : "text-abu hover:text-teks"
                }`}
              >
                Butuh Halaman ({items.length - jumlahLengkap})
              </button>
              <button
                type="button"
                onClick={() => setFilterStatus("lengkap")}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  filterStatus === "lengkap"
                    ? "bg-indigo/20 text-indigo font-bold border border-indigo/30"
                    : "text-abu hover:text-teks"
                }`}
              >
                Halaman Lengkap ({jumlahLengkap})
              </button>
              {jumlahKutipanDitemukan > 0 && (
                <button
                  type="button"
                  onClick={() => setFilterStatus("ada_kutipan")}
                  className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                    filterStatus === "ada_kutipan"
                      ? "bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30"
                      : "text-abu hover:text-teks"
                  }`}
                >
                  Kutipan Ditemukan ({jumlahKutipanDitemukan})
                </button>
              )}
            </div>

            <div className="text-abu">
              Menampilkan {itemsFiltered.length} dari {items.length} referensi
            </div>
          </div>

          {/* Daftar Kartu Referensi */}
          <div className="space-y-4">
            {itemsFiltered.map((it, idx) => {
              const hlm =
                it.halaman_rentang ||
                (it.sp && it.ep && it.sp !== it.ep ? `${it.sp}–${it.ep}` : it.sp) ||
                it.halaman_ada;
              const scan = it.scan_pdf;

              return (
                <Card
                  key={it.uid || idx}
                  className="p-5 hover:border-indigo/40 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      {/* Badge Nomor & Halaman Status */}
                      <div className="flex flex-wrap items-center gap-2 mb-2">
                        <span className="font-mono text-[11px] font-bold px-2 py-0.5 rounded bg-panel2 text-abu">
                          #{it.no || idx + 1}
                        </span>

                        {hlm ? (
                          <span className="inline-flex items-center gap-1 text-[11.5px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
                            <Ikon as={Check} size={12} />
                            Halaman: {hlm}
                            {it.volume && ` (Vol. ${it.volume}${it.issue ? `, No. ${it.issue}` : ""})`}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11.5px] font-bold px-2.5 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-400">
                            Halaman belum terdata
                          </span>
                        )}

                        {it.doi && (
                          <a
                            href={`https://doi.org/${it.doi}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[11px] text-indigo/80 hover:text-indigo hover:underline font-mono inline-flex items-center gap-1"
                          >
                            <Ikon as={Link2} size={11} />
                            DOI: {it.doi}
                          </a>
                        )}
                      </div>

                      {/* Judul Artikel */}
                      <h3 className="text-base font-bold text-teks mb-1 leading-snug">
                        {it.judul}
                      </h3>

                      {/* Penulis & Jurnal */}
                      <p className="text-xs text-abu mb-3">
                        <span className="text-teks/80 font-medium">
                          {it.penulis?.length
                            ? it.penulis.join("; ")
                            : "Anonim"}
                        </span>
                        {it.tahun && ` (${it.tahun})`}
                        {it.sumber && ` · `}
                        <span className="italic">{it.sumber}</span>
                      </p>

                      {/* Hasil Scan Teks Kutipan PDF jika ada */}
                      {scan && scan.ditemukan && (
                        <div className="mb-3 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-teks space-y-1">
                          <div className="flex items-center gap-2 font-bold text-emerald-400">
                            <Ikon as={CheckCircle2} size={14} />
                            <span>
                              Kutipan Ditemukan di Halaman Terbitan: {scan.halaman_jurnal} (Halaman PDF ke-{scan.halaman_pdf} dari {scan.total_halaman_pdf})
                            </span>
                            <span className="ml-auto text-[11px] font-normal px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                              {scan.tipe_cocok}
                            </span>
                          </div>
                          <p className="text-abu text-[11.5px] italic leading-relaxed pt-1">
                            "{scan.snippet}"
                          </p>
                        </div>
                      )}

                      {/* Sitasi Siap Salin */}
                      <div className="mt-3 pt-3 border-t border-line/50 flex flex-wrap items-center gap-2">
                        {it.sitasi?.intext_apa && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-[11px] text-abu font-semibold">
                              In-Text:
                            </span>
                            <SalinBtn teks={it.sitasi.intext_apa}>
                              {it.sitasi.intext_apa}
                            </SalinBtn>
                          </div>
                        )}

                        {it.sitasi?.daftar_pustaka_apa && (
                          <SalinBtn teks={it.sitasi.daftar_pustaka_apa}>
                            Daftar Pustaka APA
                          </SalinBtn>
                        )}

                        {hlm && (
                          <SalinBtn teks={`hlm. ${hlm}`}>
                            hlm. {hlm}
                          </SalinBtn>
                        )}
                      </div>
                    </div>

                    {/* Tombol Aksi Spesifik Kartu */}
                    <div className="shrink-0 flex flex-col gap-1.5">
                      <button
                        type="button"
                        onClick={() => cariHalamanItem(it)}
                        className="p-2 rounded-xl text-xs font-semibold bg-panel border border-line text-abu hover:text-indigo hover:border-indigo/50 transition-colors inline-flex items-center gap-1.5"
                        title="Cari metadata nomor halaman artikel ini"
                      >
                        <Ikon as={Search} size={13} />
                        Cari Halaman
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setDetailItemKutipan(it);
                          setKutipanPerItem(queryKutipan);
                          setPdfManualUpload(null);
                        }}
                        className="p-2 rounded-xl text-xs font-semibold bg-indigo/10 border border-indigo/25 text-indigo hover:bg-indigo/20 transition-colors inline-flex items-center gap-1.5"
                        title="Pindai kutipan spesifik atau unggah PDF artikel ini"
                      >
                        <Ikon as={Sparkles} size={13} />
                        Scan Kutipan PDF
                      </button>

                      {it.pdf_url && (
                        <a
                          href={it.pdf_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 rounded-xl text-xs font-semibold bg-panel border border-line text-abu hover:text-emerald-400 hover:border-emerald-500/50 transition-colors inline-flex items-center gap-1.5"
                          title="Buka atau unduh PDF Open Access resmi"
                        >
                          <Ikon as={Download} size={13} />
                          Buka PDF
                        </a>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* Modal: Tempel Teks RIS */}
      <AnimatePresence>
        {bukaTempel && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-2xl bg-panel rounded-2xl border border-line p-6 shadow-2xl"
            >
              <h3 className="text-lg font-bold text-teks mb-2 flex items-center gap-2">
                <Ikon as={Copy} size={18} className="text-indigo" />
                Tempel Teks Berkas RIS
              </h3>
              <p className="text-xs text-abu mb-4">
                Salin teks berformat RIS (dimulai dari TY - ... hingga ER - ) dari Mendeley, Zotero, atau Google Scholar, lalu tempelkan di bawah ini:
              </p>
              <textarea
                rows={10}
                value={teksTempel}
                onChange={(e) => setTeksTempel(e.target.value)}
                placeholder={"TY  - JOUR\nTI  - Judul Artikel...\nAU  - Nama Penulis...\nER  -"}
                className={`${inputCls} font-mono text-xs mb-4 resize-y`}
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setBukaTempel(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-abu hover:text-teks"
                >
                  Batal
                </button>
                <button
                  type="button"
                  disabled={!teksTempel.trim()}
                  onClick={() => prosesTeksRis(teksTempel, "teks_tempel.ris")}
                  className="px-5 py-2 rounded-xl text-xs font-bold bg-indigo text-white hover:bg-indigodeep disabled:opacity-50 transition-colors"
                >
                  Proses Teks RIS
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Modal: Pilih dari Pustaka Saya */}
      <AnimatePresence>
        {bukaPustakaModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-2xl max-h-[80vh] flex flex-col bg-panel rounded-2xl border border-line p-6 shadow-2xl"
            >
              <h3 className="text-lg font-bold text-teks mb-2 flex items-center gap-2">
                <Ikon as={Library} size={18} className="text-indigo" />
                Pilih Riwayat Pencarian dari Pustaka
              </h3>
              <p className="text-xs text-abu mb-4">
                Pilih salah satu hasil pencarian referensi yang tersimpan untuk langsung dicari halaman sitasinya:
              </p>
              <div className="flex-1 overflow-y-auto space-y-2 pr-1 mb-4">
                {daftarPustakaLokal.length === 0 ? (
                  <div className="text-center py-8 text-abu text-xs">
                    Belum ada riwayat pencarian di Pustaka.
                  </div>
                ) : (
                  daftarPustakaLokal.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => pilihEntriPustaka(p.id, p.topik)}
                      className="w-full text-left p-3.5 rounded-xl bg-panel2/60 border border-line hover:border-indigo/50 hover:bg-indigodeep/10 transition-colors"
                    >
                      <div className="font-bold text-sm text-teks mb-1">
                        {p.topik}
                      </div>
                      <div className="flex items-center gap-3 text-xs text-abu">
                        <span>{p.tanggal ? p.tanggal.slice(0, 10) : ""}</span>
                        <span>·</span>
                        <span>{p.total} Referensi</span>
                        <span>·</span>
                        <span>{p.jumlah_pdf} PDF</span>
                      </div>
                    </button>
                  ))
                )}
              </div>
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => setBukaPustakaModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-abu hover:text-teks"
                >
                  Tutup
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Modal: Scan Kutipan PDF Khusus untuk Suatu Item */}
      <AnimatePresence>
        {detailItemKutipan && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-xl bg-panel rounded-2xl border border-line p-6 shadow-2xl space-y-4"
            >
              <h3 className="text-base font-bold text-teks flex items-center gap-2">
                <Ikon as={Sparkles} size={18} className="text-indigo" />
                Pindai Letak Halaman Kutipan di PDF
              </h3>

              <div className="p-3 rounded-xl bg-panel2/60 border border-line text-xs">
                <div className="font-bold text-teks">{detailItemKutipan.judul}</div>
                <div className="text-abu mt-0.5">
                  {detailItemKutipan.penulis?.join("; ")} ({detailItemKutipan.tahun})
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-teks/90 mb-1.5">
                  Kalimat atau Kata Kunci Kutipan:
                </label>
                <textarea
                  rows={3}
                  value={kutipanPerItem}
                  onChange={(e) => setKutipanPerItem(e.target.value)}
                  placeholder="Tempel kalimat yang Anda kutip di skripsi/makalah untuk paper ini..."
                  className={`${inputCls} text-xs`}
                />
              </div>

              {/* Opsi Upload PDF Sendiri jika paper tertutup */}
              <div className="p-3.5 rounded-xl border border-dashed border-line bg-panel2/30">
                <div className="text-xs font-semibold text-teks mb-1 flex items-center justify-between">
                  <span>Punya berkas PDF di komputer?</span>
                  {pdfManualUpload && (
                    <span className="text-[11px] text-emerald-400 font-bold">
                      {pdfManualUpload.name}
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-abu mb-2">
                  Jika PDF online tidak dapat diakses bebas (berbayar), Anda bisa mengunggah berkas PDF dari komputer untuk langsung dipindai halamannya.
                </p>
                <input
                  type="file"
                  ref={pdfInputRef}
                  accept=".pdf"
                  onChange={(e) => setPdfManualUpload(e.target.files?.[0] || null)}
                  className="text-xs text-abu file:mr-2 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo/20 file:text-indigo hover:file:bg-indigo/30"
                />
              </div>

              {/* Hasil pemindaian jika sudah ada */}
              {detailItemKutipan.scan_pdf && detailItemKutipan.scan_pdf.ditemukan && (
                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs">
                  <div className="font-bold text-emerald-400 mb-1">
                    ✓ Ditemukan di Halaman: {detailItemKutipan.scan_pdf.halaman_jurnal} (PDF hal. {detailItemKutipan.scan_pdf.halaman_pdf})
                  </div>
                  <div className="text-abu italic">
                    "{detailItemKutipan.scan_pdf.snippet}"
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setDetailItemKutipan(null)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-abu hover:text-teks"
                >
                  Tutup
                </button>

                {pdfManualUpload ? (
                  <button
                    type="button"
                    disabled={sedangScanItem || !kutipanPerItem.trim()}
                    onClick={handleScanPdfManual}
                    className="px-5 py-2 rounded-xl text-xs font-bold bg-indigo text-white hover:bg-indigodeep disabled:opacity-50 transition-colors inline-flex items-center gap-1.5"
                  >
                    {sedangScanItem ? (
                      <>
                        <Ikon as={Loader2} size={14} className="animate-spin" />
                        Memindai Berkas PDF…
                      </>
                    ) : (
                      "Pindai PDF Unggahan"
                    )}
                  </button>
                ) : (
                  <button
                    type="button"
                    disabled={sedangMemuat || !kutipanPerItem.trim()}
                    onClick={async () => {
                      const res = await cariHalamanItem(detailItemKutipan, kutipanPerItem);
                      if (res) {
                        setDetailItemKutipan((prev) =>
                          prev ? { ...prev, scan_pdf: res.scan_pdf } : null
                        );
                      }
                    }}
                    className="px-5 py-2 rounded-xl text-xs font-bold bg-indigo text-white hover:bg-indigodeep disabled:opacity-50 transition-colors inline-flex items-center gap-1.5"
                  >
                    {sedangMemuat ? (
                      <>
                        <Ikon as={Loader2} size={14} className="animate-spin" />
                        Mencari di PDF Online…
                      </>
                    ) : (
                      "Cari di PDF Online"
                    )}
                  </button>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </main>
  );
}
