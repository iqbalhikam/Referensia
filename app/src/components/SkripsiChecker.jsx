import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Ikon,
  FileText,
  Upload,
  Download,
  Copy,
  Check,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  BookOpen,
  Loader2,
  Trash2,
  TriangleAlert,
} from "./icons.jsx";
import { Card, SalinBtn, inputCls } from "./ui.jsx";
import {
  checkSkripsiText,
  checkSkripsiFile,
  downloadSkripsiAuditDocx,
} from "../api.js";

const CONTOH_DRAF_SKRIPSI = `SKRIPSI
PENGARUH MODEL PEMBELAJARAN BERBASIS MASALAH TERHADAP HASIL BELAJAR SISWA
Oleh: Ahmad Fadli (NIM: 190210001)

ABSTRAK
Penelitian ini bertujuan untuk menganalisis efektivitas model pembelajaran berbasis masalah pada materi IPA siswa sekolah menengah. Metode yang digunakan adalah eksperimen kuantitatif. Hasil penelitian menunjukkan bahwa terdapat peningkatan hasil belajar yang signifikan pada kelompok eksperimen dibandingkan kelompok kontrol.
Kata Kunci: pembelajaran berbasis masalah, hasil belajar, siswa.

BAB I PENDAHULUAN
Latar Belakang masalah dalam penelitian ini adalah rendahnya prestasi belajar siswa di sekolah. Rumusan Masalah dirumuskan untuk menguji apakah model ini efektif. Tujuan Penelitian adalah mengetahui peningkatan pemahaman konsep. Manfaat Penelitian diharapkan berguna bagi praktisi pendidikan.

BAB II TINJAUAN PUSTAKA
Menurut Sugiyono (2020), metode penelitian merupakan cara ilmiah untuk memperoleh data valid. Pembelajaran berbasis masalah dapat meningkatkan kemandirian siswa (Hidayat & Rahayu, 2021). Penelitian terdahulu oleh Pratama (2019) juga menunjukkan peningkatan signifikan. Namun, pendapat Widodo (2018) menegaskan bahwa guru harus membimbing siswa dengan cermat agar tujuan pembelajaran tercapai.

BAB III METODE PENELITIAN
Jenis Penelitian yang di gunakan adalah eksperimen semu (quasi experiment). Populasi dan sampel mencakup 60 siswa kelas VIII. Analisis Data memakai uji statistik regresi linier.

BAB IV HASIL DAN PEMBAHASAN
Hasil penelitian menunjukkan bahwa hipotesa terbukti secara empiris. Analisa data di lakukan secara teliti didalam kelas. Banyak siswa yang antusias karena metode ini adalah merupakan hal baru bagi mereka. Saya merasa bahwa metode ini sangat cocok di terapkan di sekolah tersebut. Penelitian ini memiliki kalimat yang sangat panjang sekali di mana peneliti mengumpulkan berbagai macam instrumen pengukuran dari puluhan responden yang berbeda di berbagai sekolah tanpa membatasi variabel pengganggu sehingga proses analisis membutuhkan waktu yang amat lama sekali.

BAB V KESIMPULAN DAN SARAN
Kesimpulan penelitian ini adalah model pembelajaran berbasis masalah efektif meningkatkan hasil belajar siswa.

DAFTAR PUSTAKA
Hidayat, T., & Rahayu, S. (2021). Pembelajaran Abad 21. Jurnal Pendidikan IPA Indonesia, 10(2), 45-56.
Pratama, B. (2019). Model Pembelajaran Inovatif. Bandung: Alfabeta.
Sugiyono. (2020). Metode Penelitian Kuantitatif. Bandung: Alfabeta.
Yusuf, M. (2022). Statistik Terapan Pendidikan. Jakarta: Prenada Media.
`;

export default function SkripsiChecker({ onBack }) {
  const [tabInput, setTabInput] = useState("file"); // file, text
  const [teksInput, setTeksInput] = useState("");
  const [namaBerkas, setNamaBerkas] = useState("");
  const [sedangMemuat, setSedangMemuat] = useState(false);
  const [pesanGalat, setPesanGalat] = useState("");
  const [hasilAudit, setHasilAudit] = useState(null);
  const [tabAktif, setTabAktif] = useState("ringkasan"); // ringkasan, sitasi, struktur, bahasa, keterbacaan
  const [filterBahasa, setFilterBahasa] = useState("semua");

  const fileInputRef = useRef(null);

  // Proses teks naskah langsung
  async function auditTeks(teks, label = "Draf_Skripsi.txt") {
    if (!teks || teks.trim().length < 50) {
      setPesanGalat("Naskah terlalu pendek (minimal 50 karakter).");
      return;
    }
    setSedangMemuat(true);
    setPesanGalat("");
    try {
      const res = await checkSkripsiText(teks, label);
      if (res.hasil) {
        setHasilAudit(res.hasil);
        setNamaBerkas(label);
      }
    } catch (e) {
      setPesanGalat(e.message || "Gagal memeriksa naskah skripsi.");
    } finally {
      setSedangMemuat(false);
    }
  }

  // Handle upload berkas (DOCX, PDF, TXT)
  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setSedangMemuat(true);
    setPesanGalat("");
    setNamaBerkas(file.name);

    const reader = new FileReader();
    reader.onload = async (event) => {
      const base64 = event.target?.result;
      if (typeof base64 !== "string") return;

      try {
        const res = await checkSkripsiFile(base64, file.name);
        if (res.hasil) {
          setHasilAudit(res.hasil);
        }
      } catch (err) {
        setPesanGalat(err.message || "Gagal memproses berkas.");
      } finally {
        setSedangMemuat(false);
      }
    };
    reader.readAsDataURL(file);
    e.target.value = "";
  }

  // Handle Drag & Drop
  function handleDrop(e) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (!file) return;

    setSedangMemuat(true);
    setPesanGalat("");
    setNamaBerkas(file.name);

    const reader = new FileReader();
    reader.onload = async (event) => {
      const base64 = event.target?.result;
      if (typeof base64 !== "string") return;

      try {
        const res = await checkSkripsiFile(base64, file.name);
        if (res.hasil) {
          setHasilAudit(res.hasil);
        }
      } catch (err) {
        setPesanGalat(err.message || "Gagal memproses berkas.");
      } finally {
        setSedangMemuat(false);
      }
    };
    reader.readAsDataURL(file);
  }

  function handleReset() {
    setHasilAudit(null);
    setTeksInput("");
    setNamaBerkas("");
    setPesanGalat("");
    setTabAktif("ringkasan");
  }

  return (
    <main className="max-w-6xl mx-auto px-5 py-8">
      {/* Header Halaman */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo/10 border border-indigo/20 text-indigo text-[12px] font-semibold mb-2">
            <Ikon as={CheckCircle2} size={14} />
            Fitur Baru: Skripsi Checker (100% Non-AI & Deterministik)
          </div>
          <h1 className="text-2xl font-display font-extrabold tracking-tight text-teks">
            Pemeriksa Kelayakan Naskah Skripsi
          </h1>
          <p className="text-sm text-abu mt-1 max-w-2xl leading-relaxed">
            Audit mandiri draf skripsi secara offline, cepat, dan transparan tanpa biaya AI. Memvalidasi kecocokan sitasi vs daftar pustaka, memeriksa kelengkapan Bab I–V, mendeteksi kata tidak baku (KBBI), imbuhan <code>di-</code>, pleonasme, serta kalimat bertele-tele.
          </p>
        </div>

        {hasilAudit && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => downloadSkripsiAuditDocx(hasilAudit)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-indigo text-white hover:bg-indigodeep transition-colors shadow-md"
              title="Unduh laporan hasil audit lengkap ke berkas Microsoft Word (.docx)"
            >
              <Ikon as={Download} size={14} />
              Unduh Laporan Audit (.docx)
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-panel border border-line text-abu hover:text-teks transition-colors"
            >
              <Ikon as={RotateCcw} size={13} />
              Periksa Draf Lain
            </button>
          </div>
        )}
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

      {/* JIKA BELUM ADA HASIL AUDIT: FORM INPUT (UPLOAD / TEMPEL) */}
      {!hasilAudit ? (
        <div className="space-y-4">
          {/* Toggle Cara Input */}
          <div className="flex items-center gap-2 border-b border-line/60 pb-3">
            <button
              type="button"
              onClick={() => setTabInput("file")}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-colors inline-flex items-center gap-2 ${
                tabInput === "file"
                  ? "bg-indigo text-white shadow"
                  : "bg-panel text-abu hover:text-teks border border-line"
              }`}
            >
              <Ikon as={Upload} size={14} />
              Unggah Berkas (.docx / .pdf / .txt)
            </button>
            <button
              type="button"
              onClick={() => setTabInput("text")}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-colors inline-flex items-center gap-2 ${
                tabInput === "text"
                  ? "bg-indigo text-white shadow"
                  : "bg-panel text-abu hover:text-teks border border-line"
              }`}
            >
              <Ikon as={FileText} size={14} />
              Tempel Teks Draf
            </button>
            <button
              type="button"
              onClick={() => {
                setTeksInput(CONTOH_DRAF_SKRIPSI);
                auditTeks(CONTOH_DRAF_SKRIPSI, "Contoh_Draf_Skripsi.docx");
              }}
              className="ml-auto px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-indigo/10 border border-indigo/25 text-indigo hover:bg-indigo/20 transition-colors inline-flex items-center gap-1.5"
            >
              <Ikon as={Sparkles} size={13} />
              Coba dengan Contoh Skripsi
            </button>
          </div>

          {/* Opsi 1: Upload Berkas */}
          {tabInput === "file" && (
            <Card className="p-8 text-center border-dashed border-2 border-line hover:border-indigo/50 transition-colors">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".docx,.pdf,.txt"
                className="hidden"
              />

              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                className="py-8 cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="w-16 h-16 mx-auto rounded-2xl bg-indigo/10 border border-indigo/20 flex items-center justify-center text-indigo mb-4 shadow-inner">
                  {sedangMemuat ? (
                    <Ikon as={Loader2} size={30} className="animate-spin" />
                  ) : (
                    <Ikon as={Upload} size={30} />
                  )}
                </div>
                <h2 className="text-lg font-bold text-teks mb-1">
                  {sedangMemuat
                    ? "Sedang Memeriksa & Mengaudit Naskah…"
                    : "Pilih atau Tarik Berkas Skripsi ke Sini"}
                </h2>
                <p className="text-xs text-abu mb-4">
                  Mendukung berkas Microsoft Word (<code>.docx</code>), Dokumen PDF (<code>.pdf</code>), atau Teks polos (<code>.txt</code>)
                </p>

                <button
                  type="button"
                  disabled={sedangMemuat}
                  className="px-6 py-2.5 rounded-xl text-xs font-bold bg-indigo text-white hover:bg-indigodeep transition-colors inline-flex items-center gap-2 shadow"
                >
                  <Ikon as={FileText} size={14} />
                  Pilih Berkas dari Komputer
                </button>
              </div>

              <div className="pt-4 border-t border-line/60 grid grid-cols-1 md:grid-cols-3 gap-3 text-left text-xs text-abu">
                <div className="p-3 rounded-xl bg-panel2/40 border border-line/40">
                  <div className="font-bold text-teks mb-0.5">🔒 100% Aman & Lokal</div>
                  Naskah skripsi Anda tidak pernah dikirim ke AI atau server luar. Seluruh pengecekan berjalan di laptop Anda.
                </div>
                <div className="p-3 rounded-xl bg-panel2/40 border border-line/40">
                  <div className="font-bold text-teks mb-0.5">⚡ Kilat & Deterministik</div>
                  Hasil audit selesai dalam pecahan detik dengan aturan baku KBBI dan pedoman akademik resmi.
                </div>
                <div className="p-3 rounded-xl bg-panel2/40 border border-line/40">
                  <div className="font-bold text-teks mb-0.5">📑 Laporan Siap Unduh</div>
                  Dapatkan daftar koreksi lengkap dan ekspor dokumen Word laporan audit untuk bahan revisi.
                </div>
              </div>
            </Card>
          )}

          {/* Opsi 2: Tempel Teks */}
          {tabInput === "text" && (
            <Card className="p-5 space-y-4">
              <div>
                <label className="block text-xs font-bold text-teks mb-1.5">
                  Tempelkan Naskah Skripsi (Bisa 1 Bab atau Seluruh Naskah):
                </label>
                <textarea
                  rows={14}
                  value={teksInput}
                  onChange={(e) => setTeksInput(e.target.value)}
                  placeholder="Tempelkan isi skripsi di sini (judul, abstrak, bab 1–5, dan daftar pustaka)..."
                  className={`${inputCls} font-mono text-xs resize-y`}
                />
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs text-abu">
                  {teksInput.split(/\s+/).filter(Boolean).length} kata terisi
                </span>

                <button
                  type="button"
                  disabled={sedangMemuat || teksInput.trim().length < 50}
                  onClick={() => auditTeks(teksInput, "Draf_Tempel.txt")}
                  className="px-6 py-2.5 rounded-xl font-bold text-xs bg-indigo text-white hover:bg-indigodeep disabled:opacity-50 transition-colors inline-flex items-center gap-2 shadow"
                >
                  {sedangMemuat ? (
                    <>
                      <Ikon as={Loader2} size={14} className="animate-spin" />
                      Sedang Mengaudit…
                    </>
                  ) : (
                    <>
                      <Ikon as={CheckCircle2} size={14} />
                      Mulai Audit Skripsi Sekarang
                    </>
                  )}
                </button>
              </div>
            </Card>
          )}
        </div>
      ) : (
        /* JIKA SUDAH ADA HASIL AUDIT: DASHBOARD HASIL */
        <div className="space-y-6">
          {/* Kartu Skor Utama & Ringkasan Cepat */}
          <Card className="p-6 bg-gradient-to-br from-panel/90 via-panel/80 to-indigodeep/15 border border-line">
            <div className="flex flex-wrap items-center justify-between gap-6 pb-6 border-b border-line/60">
              <div className="flex items-center gap-5">
                {/* Visual Skor Meter */}
                <div
                  className={`w-24 h-24 rounded-2xl flex flex-col items-center justify-center font-display shadow-lg border-2 ${
                    hasilAudit.skor >= 85
                      ? "bg-emerald-500/15 border-emerald-500 text-emerald-400"
                      : hasilAudit.skor >= 70
                      ? "bg-indigo/15 border-indigo text-indigo"
                      : hasilAudit.skor >= 50
                      ? "bg-amber-500/15 border-amber-500 text-amber-400"
                      : "bg-rose-500/15 border-rose-500 text-rose-400"
                  }`}
                >
                  <span className="text-3xl font-extrabold">{hasilAudit.skor}</span>
                  <span className="text-[11px] font-semibold tracking-wider uppercase opacity-80">
                    / 100
                  </span>
                </div>

                <div>
                  <div className="text-xs text-abu font-semibold uppercase tracking-wider mb-1">
                    Predikat Kelayakan Naskah
                  </div>
                  <h2 className="text-xl font-bold text-teks">
                    {hasilAudit.predikat}
                  </h2>
                  <p className="text-xs text-abu mt-1">
                    Berkas: <span className="text-teks font-mono">{hasilAudit.nama_berkas}</span>
                  </p>
                </div>
              </div>

              {/* Statistik Ringkas Naskah */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-panel2/60 border border-line">
                  <div className="text-abu text-[11px]">Total Kata</div>
                  <div className="text-base font-extrabold text-teks mt-0.5">
                    {hasilAudit.audit_keterbacaan?.total_kata.toLocaleString()}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-panel2/60 border border-line">
                  <div className="text-abu text-[11px]">Estimasi Halaman</div>
                  <div className="text-base font-extrabold text-teks mt-0.5">
                    ~{hasilAudit.audit_keterbacaan?.estimasi_halaman} hlm
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-panel2/60 border border-line">
                  <div className="text-abu text-[11px]">Sitasi Hilang</div>
                  <div className={`text-base font-extrabold mt-0.5 ${hasilAudit.audit_sitasi?.jumlah_sitasi_hilang > 0 ? "text-rose-400" : "text-emerald-400"}`}>
                    {hasilAudit.audit_sitasi?.jumlah_sitasi_hilang}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-panel2/60 border border-line">
                  <div className="text-abu text-[11px]">Isu Bahasa & EBI</div>
                  <div className="text-base font-extrabold text-teks mt-0.5">
                    {hasilAudit.audit_bahasa?.total_temuan}
                  </div>
                </div>
              </div>
            </div>

            {/* Navigasi Sub-Tab Hasil */}
            <div className="flex flex-wrap items-center gap-2 pt-4">
              <button
                type="button"
                onClick={() => setTabAktif("ringkasan")}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition-colors ${
                  tabAktif === "ringkasan"
                    ? "bg-indigo text-white shadow"
                    : "bg-panel2/60 text-abu hover:text-teks"
                }`}
              >
                📊 Ringkasan Temuan
              </button>
              <button
                type="button"
                onClick={() => setTabAktif("sitasi")}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition-colors inline-flex items-center gap-1.5 ${
                  tabAktif === "sitasi"
                    ? "bg-indigo text-white shadow"
                    : "bg-panel2/60 text-abu hover:text-teks"
                }`}
              >
                📚 Audit Sitasi & DP
                {hasilAudit.audit_sitasi?.jumlah_sitasi_hilang > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full bg-rose-500 text-white text-[10px]">
                    {hasilAudit.audit_sitasi.jumlah_sitasi_hilang}
                  </span>
                )}
              </button>
              <button
                type="button"
                onClick={() => setTabAktif("struktur")}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition-colors ${
                  tabAktif === "struktur"
                    ? "bg-indigo text-white shadow"
                    : "bg-panel2/60 text-abu hover:text-teks"
                }`}
              >
                📑 Struktur Bab ({hasilAudit.audit_struktur?.persentase_kelengkapan}%)
              </button>
              <button
                type="button"
                onClick={() => setTabAktif("bahasa")}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition-colors inline-flex items-center gap-1.5 ${
                  tabAktif === "bahasa"
                    ? "bg-indigo text-white shadow"
                    : "bg-panel2/60 text-abu hover:text-teks"
                }`}
              >
                ✍️ Kaidah Bahasa & EBI ({hasilAudit.audit_bahasa?.total_temuan})
              </button>
              <button
                type="button"
                onClick={() => setTabAktif("keterbacaan")}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition-colors ${
                  tabAktif === "keterbacaan"
                    ? "bg-indigo text-white shadow"
                    : "bg-panel2/60 text-abu hover:text-teks"
                }`}
              >
                ⏱️ Keterbacaan Kalimat
              </button>
            </div>
          </Card>

          {/* TAB 1: RINGKASAN */}
          {tabAktif === "ringkasan" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Box 1: Catatan Kritis Sitasi */}
              <Card className="p-5 border-l-4 border-l-rose-500">
                <div className="flex items-center gap-2 text-rose-400 font-bold text-sm mb-2">
                  <Ikon as={TriangleAlert} size={16} />
                  Kesesuaian Sitasi vs Daftar Pustaka
                </div>
                <p className="text-xs text-abu mb-3 leading-relaxed">
                  Dosen penguji kerap mencoret skripsi bila nama yang dikutip dalam teks tidak dapat ditemukan di Daftar Pustaka.
                </p>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between p-2 rounded-lg bg-panel2/50">
                    <span className="text-teks">Sitasi di dalam teks yang hilang di DP:</span>
                    <span className={`font-bold ${hasilAudit.audit_sitasi?.jumlah_sitasi_hilang > 0 ? "text-rose-400" : "text-emerald-400"}`}>
                      {hasilAudit.audit_sitasi?.jumlah_sitasi_hilang} entri
                    </span>
                  </div>
                  <div className="flex justify-between p-2 rounded-lg bg-panel2/50">
                    <span className="text-teks">Referensi di DP yang tidak pernah dikutip:</span>
                    <span className={`font-bold ${hasilAudit.audit_sitasi?.jumlah_dp_tidak_dikutip > 0 ? "text-amber-400" : "text-emerald-400"}`}>
                      {hasilAudit.audit_sitasi?.jumlah_dp_tidak_dikutip} entri
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setTabAktif("sitasi")}
                  className="mt-4 text-xs font-bold text-indigo hover:underline inline-flex items-center gap-1"
                >
                  Lihat Rincian Sitasi →
                </button>
              </Card>

              {/* Box 2: Kelengkapan Struktur */}
              <Card className="p-5 border-l-4 border-l-indigo">
                <div className="flex items-center gap-2 text-indigo font-bold text-sm mb-2">
                  <Ikon as={BookOpen} size={16} />
                  Sistematika Bab Standar
                </div>
                <p className="text-xs text-abu mb-3 leading-relaxed">
                  Memastikan Bab I (Pendahuluan), Bab II (Teori), Bab III (Metode), Bab IV (Hasil), Bab V (Penutup), dan Abstrak sudah terdeteksi.
                </p>
                <div className="p-2 rounded-lg bg-panel2/50 text-xs flex justify-between items-center mb-2">
                  <span className="text-teks">Kelengkapan Struktur Bab:</span>
                  <span className="font-bold text-indigo">
                    {hasilAudit.audit_struktur?.persentase_kelengkapan}% ({hasilAudit.audit_struktur?.jumlah_ditemukan}/{hasilAudit.audit_struktur?.total_bab_target})
                  </span>
                </div>
                {hasilAudit.audit_struktur?.analisis_abstrak && (
                  <div className="p-2 rounded-lg bg-panel2/50 text-xs text-abu">
                    Abstrak: <strong className="text-teks">{hasilAudit.audit_struktur.analisis_abstrak.jumlah_kata} kata</strong> — {hasilAudit.audit_struktur.analisis_abstrak.pesan}
                  </div>
                )}
                <button
                  type="button"
                  onClick={() => setTabAktif("struktur")}
                  className="mt-4 text-xs font-bold text-indigo hover:underline inline-flex items-center gap-1"
                >
                  Lihat Kelengkapan Bab →
                </button>
              </Card>

              {/* Box 3: Kaidah Bahasa */}
              <Card className="p-5 border-l-4 border-l-amber-500">
                <div className="flex items-center gap-2 text-amber-400 font-bold text-sm mb-2">
                  <Ikon as={FileText} size={16} />
                  Koreksi Tata Bahasa & EBI (KBBI)
                </div>
                <p className="text-xs text-abu mb-3 leading-relaxed">
                  Deteksi kata tidak baku (analisa, hipotesa), kesalahan spasi imbuhan <code>di-</code>, dan frasa pleonasme (adalah merupakan).
                </p>
                <div className="space-y-1.5 text-xs">
                  {Object.entries(hasilAudit.audit_bahasa?.ringkasan_kategori || {}).map(([kat, jml]) => (
                    <div key={kat} className="flex justify-between p-1.5 rounded bg-panel2/40">
                      <span className="text-teks capitalize">{kat.replace(/_/g, " ")}:</span>
                      <span className="font-bold text-amber-400">{jml} temuan</span>
                    </div>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => setTabAktif("bahasa")}
                  className="mt-4 text-xs font-bold text-indigo hover:underline inline-flex items-center gap-1"
                >
                  Lihat Daftar Koreksi Bahasa →
                </button>
              </Card>

              {/* Box 4: Keterbacaan Kalimat */}
              <Card className="p-5 border-l-4 border-l-emerald-500">
                <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm mb-2">
                  <Ikon as={CheckCircle2} size={16} />
                  Panjang & Alur Kalimat
                </div>
                <p className="text-xs text-abu mb-3 leading-relaxed">
                  Kalimat yang melebihi 35 kata berisiko menjadi kalimat rancu (*run-on sentences*) yang menyulitkan pembaca.
                </p>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between p-2 rounded-lg bg-panel2/50">
                    <span className="text-teks">Rata-rata panjang kalimat:</span>
                    <span className="font-bold text-teks">
                      {hasilAudit.audit_keterbacaan?.rerata_kata_per_kalimat} kata/kalimat
                    </span>
                  </div>
                  <div className="flex justify-between p-2 rounded-lg bg-panel2/50">
                    <span className="text-teks">Kalimat terlalu panjang (&gt;35 kata):</span>
                    <span className={`font-bold ${hasilAudit.audit_keterbacaan?.jumlah_kalimat_panjang > 0 ? "text-amber-400" : "text-emerald-400"}`}>
                      {hasilAudit.audit_keterbacaan?.jumlah_kalimat_panjang} kalimat
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setTabAktif("keterbacaan")}
                  className="mt-4 text-xs font-bold text-indigo hover:underline inline-flex items-center gap-1"
                >
                  Lihat Kalimat Terlalu Panjang →
                </button>
              </Card>
            </div>
          )}

          {/* TAB 2: AUDIT SITASI & DAFTAR PUSTAKA */}
          {tabAktif === "sitasi" && (
            <div className="space-y-4">
              {/* Sitasi Hilang (Kritis) */}
              <Card className="p-5 border border-rose-500/40 bg-rose-500/5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2 font-bold text-rose-400 text-sm">
                    <Ikon as={TriangleAlert} size={16} />
                    Sitasi dalam Teks yang TIDAK ADA di Daftar Pustaka ({hasilAudit.audit_sitasi?.jumlah_sitasi_hilang})
                  </div>
                  <span className="text-[11px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-bold">
                    Kritis (Wajib Diperbaiki)
                  </span>
                </div>

                {hasilAudit.audit_sitasi?.sitasi_hilang.length === 0 ? (
                  <div className="text-xs text-emerald-400 py-3 flex items-center gap-2">
                    <Ikon as={CheckCircle2} size={15} />
                    Luar biasa! Seluruh sitasi yang dikutip dalam teks telah tercantum di Daftar Pustaka.
                  </div>
                ) : (
                  <div className="space-y-2">
                    <p className="text-xs text-abu mb-2">
                      Referensi berikut dikutip dalam draf skripsi Anda, namun tidak ditemukan di bagian Daftar Pustaka. Tambahkan segera ke Daftar Pustaka:
                    </p>
                    {hasilAudit.audit_sitasi.sitasi_hilang.map((sh, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-panel2/80 border border-line flex flex-wrap items-center justify-between gap-3 text-xs"
                      >
                        <div>
                          <span className="font-bold text-teks font-mono text-sm">
                            {sh.teks_asli}
                          </span>
                          <span className="text-abu text-[11px] ml-2">
                            ({sh.jumlah_kemunculan}x dikutip dalam teks)
                          </span>
                        </div>
                        <SalinBtn teks={sh.teks_asli}>Salin Nama</SalinBtn>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              {/* Referensi DP yang Tidak Pernah Dikutip */}
              <Card className="p-5 border border-line">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2 font-bold text-amber-400 text-sm">
                    <Ikon as={BookOpen} size={16} />
                    Entri Daftar Pustaka yang TIDAK PERNAH Dikutip ({hasilAudit.audit_sitasi?.jumlah_dp_tidak_dikutip})
                  </div>
                  <span className="text-[11px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold">
                    Peringatan
                  </span>
                </div>

                {hasilAudit.audit_sitasi?.dp_tidak_dikutip.length === 0 ? (
                  <div className="text-xs text-emerald-400 py-3 flex items-center gap-2">
                    <Ikon as={CheckCircle2} size={15} />
                    Semua referensi di Daftar Pustaka benar-benar dikutip dalam naskah.
                  </div>
                ) : (
                  <div className="space-y-2">
                    <p className="text-xs text-abu mb-2">
                      Pedoman skripsi mewajibkan hanya referensi yang benar-benar dirujuk dalam teks yang dicantumkan di Daftar Pustaka. Hapus entri ini bila tidak dikutip:
                    </p>
                    {hasilAudit.audit_sitasi.dp_tidak_dikutip.map((dp, idx) => (
                      <div
                        key={idx}
                        className="p-3 rounded-xl bg-panel2/60 border border-line text-xs"
                      >
                        <div className="font-semibold text-teks mb-1">
                          {dp.penulis} {dp.tahun ? `(${dp.tahun})` : ""}
                        </div>
                        <div className="text-abu text-[11px] italic leading-relaxed">
                          {dp.teks_lengkap}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          )}

          {/* TAB 3: STRUKTUR BAB SKRIPSI */}
          {tabAktif === "struktur" && (
            <Card className="p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-line/60 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-teks">
                    Sistematika Bab & Sub-Bab Skripsi
                  </h3>
                  <p className="text-xs text-abu">
                    Berdasarkan pedoman umum penulisan karya ilmiah universitas di Indonesia.
                  </p>
                </div>
                <span className="text-sm font-extrabold text-indigo">
                  {hasilAudit.audit_struktur?.persentase_kelengkapan}% Terpenuhi
                </span>
              </div>

              <div className="space-y-3">
                {hasilAudit.audit_struktur?.daftar_bab.map((b) => (
                  <div
                    key={b.id}
                    className="p-3.5 rounded-xl bg-panel2/60 border border-line text-xs space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {b.status === "lengkap" ? (
                          <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">
                            ✓
                          </span>
                        ) : (
                          <span className="w-5 h-5 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center font-bold">
                            ✕
                          </span>
                        )}
                        <span className="font-bold text-teks text-sm">
                          {b.nama}
                        </span>
                      </div>

                      <span
                        className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                          b.status === "lengkap"
                            ? "bg-emerald-500/15 text-emerald-400"
                            : "bg-rose-500/15 text-rose-400"
                        }`}
                      >
                        {b.status === "lengkap" ? "Ditemukan" : "Belum Terdeteksi"}
                      </span>
                    </div>

                    {b.sub && b.sub.length > 0 && (
                      <div className="pl-7 grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-1 border-t border-line/40">
                        {b.sub.map((s) => (
                          <div
                            key={s.id}
                            className="flex items-center gap-2 text-[11.5px] text-abu"
                          >
                            <span
                              className={`w-1.5 h-1.5 rounded-full ${
                                s.status === "lengkap"
                                  ? "bg-emerald-400"
                                  : "bg-abu/40"
                              }`}
                            />
                            <span>{s.nama}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* TAB 4: KAIDAH BAHASA & EBI */}
          {tabAktif === "bahasa" && (
            <Card className="p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-teks">
                    Temuan Kaidah Bahasa, KBBI, & EBI ({hasilAudit.audit_bahasa?.total_temuan})
                  </h3>
                  <p className="text-xs text-abu">
                    Koreksi otomatis kata tidak baku, salah imbuhan di-, pleonasme, dan kata ganti informal.
                  </p>
                </div>

                <div className="flex items-center gap-1.5 text-xs">
                  <button
                    type="button"
                    onClick={() => setFilterBahasa("semua")}
                    className={`px-2.5 py-1 rounded-lg ${
                      filterBahasa === "semua"
                        ? "bg-indigo text-white font-bold"
                        : "bg-panel2 text-abu hover:text-teks"
                    }`}
                  >
                    Semua
                  </button>
                  <button
                    type="button"
                    onClick={() => setFilterBahasa("kata_tidak_baku")}
                    className={`px-2.5 py-1 rounded-lg ${
                      filterBahasa === "kata_tidak_baku"
                        ? "bg-indigo text-white font-bold"
                        : "bg-panel2 text-abu hover:text-teks"
                    }`}
                  >
                    Kata Tidak Baku
                  </button>
                  <button
                    type="button"
                    onClick={() => setFilterBahasa("imbuhan_di_terpisah")}
                    className={`px-2.5 py-1 rounded-lg ${
                      filterBahasa === "imbuhan_di_terpisah"
                        ? "bg-indigo text-white font-bold"
                        : "bg-panel2 text-abu hover:text-teks"
                    }`}
                  >
                    Imbuhan di-
                  </button>
                  <button
                    type="button"
                    onClick={() => setFilterBahasa("pleonasme")}
                    className={`px-2.5 py-1 rounded-lg ${
                      filterBahasa === "pleonasme"
                        ? "bg-indigo text-white font-bold"
                        : "bg-panel2 text-abu hover:text-teks"
                    }`}
                  >
                    Pleonasme
                  </button>
                </div>
              </div>

              <div className="space-y-3">
                {hasilAudit.audit_bahasa?.daftar_temuan
                  .filter((t) =>
                    filterBahasa === "semua" ? true : t.kategori === filterBahasa
                  )
                  .map((t, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl bg-panel2/60 border border-line text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-rose-400 line-through">
                            {t.teks_salah}
                          </span>
                          <span className="text-abu">→</span>
                          <span className="font-bold text-emerald-400">
                            {t.rekomendasi}
                          </span>
                        </div>
                        <span className="text-[10.5px] px-2 py-0.5 rounded bg-panel border border-line text-abu capitalize">
                          {t.kategori.replace(/_/g, " ")}
                        </span>
                      </div>

                      <p className="text-abu text-[11.5px]">{t.alasan}</p>
                      <p className="text-teks/80 text-[11.5px] italic bg-panel/70 p-2 rounded-lg border border-line/40">
                        "{t.cuplikan}"
                      </p>
                    </div>
                  ))}
              </div>
            </Card>
          )}

          {/* TAB 5: KETERBACAAN */}
          {tabAktif === "keterbacaan" && (
            <Card className="p-5 space-y-4">
              <div className="border-b border-line/60 pb-3">
                <h3 className="text-sm font-bold text-teks">
                  Deteksi Kalimat Terlalu Panjang (&gt;35 Kata)
                </h3>
                <p className="text-xs text-abu">
                  Kalimat yang terlalu panjang cenderung rancu dan melelahkan dosen penguji. Pecah menjadi kalimat-kalimat yang lebih padat dan lugas.
                </p>
              </div>

              {hasilAudit.audit_keterbacaan?.kalimat_terlalu_panjang.length === 0 ? (
                <div className="text-xs text-emerald-400 py-4 flex items-center gap-2">
                  <Ikon as={CheckCircle2} size={16} />
                  Bagus sekali! Tidak ditemukan kalimat yang melebihi batas 35 kata. Naskah Anda memiliki struktur kalimat yang proporsional.
                </div>
              ) : (
                <div className="space-y-3">
                  {hasilAudit.audit_keterbacaan.kalimat_terlalu_panjang.map((kp, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl bg-panel2/60 border border-line text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between font-bold text-amber-400">
                        <span>Kalimat #{idx + 1} ({kp.panjang_kata} kata)</span>
                        <SalinBtn teks={kp.cuplikan}>Salin Teks</SalinBtn>
                      </div>
                      <p className="text-teks italic leading-relaxed bg-panel/70 p-2.5 rounded-lg border border-line/40">
                        "{kp.cuplikan}"
                      </p>
                      <p className="text-abu text-[11px]">{kp.saran}</p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}
        </div>
      )}
    </main>
  );
}
