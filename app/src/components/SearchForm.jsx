import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, Label, Toggle, Field, inputCls, IconCheck, IconSearch, IconArrow } from "./ui.jsx";
import { Ikon, ChevronDown } from "./icons.jsx";

const JENIS = ["Semua", "Artikel Jurnal", "Buku / Bab Buku", "Skripsi / Tesis / Disertasi"];

function Stepper({ label, dot, value, onChange, hint }) {
  const set = (v) => onChange(Math.max(0, Math.min(50, v)));
  return (
    <div className="rounded-xl border border-line/60 bg-bg/50 p-4">
      <div className="flex items-center gap-2 text-[13px] font-medium text-teks/90">
        <span className={`w-2 h-2 rounded-full ${dot}`} />
        {label}
      </div>
      <div className="flex items-center justify-between mt-3">
        <button
          type="button"
          onClick={() => set(value - 1)}
          className="w-8 h-8 rounded-lg border border-line text-abu hover:text-indigo hover:border-indigo/50 transition-colors text-lg leading-none"
          aria-label={`Kurangi ${label}`}
        >
          −
        </button>
        <span className="font-display text-3xl font-semibold tabular-nums">{value}</span>
        <button
          type="button"
          onClick={() => set(value + 1)}
          className="w-8 h-8 rounded-lg border border-line text-abu hover:text-indigo hover:border-indigo/50 transition-colors text-lg leading-none"
          aria-label={`Tambah ${label}`}
        >
          +
        </button>
      </div>
      <p className="text-[11px] text-abu mt-2.5 leading-snug">{hint}</p>
    </div>
  );
}

function Segmented({ options, value, onChange, id }) {
  return (
    <div className="inline-flex rounded-xl bg-bg/60 border border-line/60 p-1">
      {options.map(([val, label]) => (
        <button
          key={val}
          type="button"
          onClick={() => onChange(val)}
          className="relative px-4 py-1.5 text-[13px] font-medium rounded-lg"
        >
          {value === val && (
            <motion.span
              layoutId={`seg-${id}`}
              transition={{ type: "spring", stiffness: 400, damping: 32 }}
              className="absolute inset-0 rounded-lg bg-indigodeep/25 border border-indigo/40"
            />
          )}
          <span className={`relative transition-colors ${value === val ? "text-teks" : "text-abu hover:text-teks/80"}`}>
            {label}
          </span>
        </button>
      ))}
    </div>
  );
}

const FITUR = [
  ["Nasional & internasional terpisah", "Dikelompokkan dari negara penerbit, bukan bahasa"],
  ["Kualitas tersaring", "Filter penerbit predator + badge DOAJ & SINTA"],
  ["PDF legal, open access", "Situs bajakan otomatis dilewati"],
  ["Siap Mendeley & Zotero", "RIS + BibTeX + PDF, bertag kategori"],
  ["Analisis & sitasi", "Ringkasan, tabel metode, ekspor APA / IEEE"],
];

const ALUR = [
  ["01", "Topik", "Satu judul, diterjemahkan otomatis untuk pencarian global"],
  ["02", "Analisis", "TF-IDF menilai relevansi tiap kandidat sampai kuota pas"],
  ["03", "ZIP", "PDF + metadata + laporan, siap masuk Mendeley / Zotero"],
];

export default function SearchForm({ onSubmit, error }) {
  const [topik, setTopik] = useState("");
  const [nasional, setNasional] = useState(10);
  const [internasional, setInternasional] = useState(5);
  const [modeTahun, setModeTahun] = useState("bebas");
  const [umur, setUmur] = useState(5);
  const [dari, setDari] = useState(2020);
  const [sampai, setSampai] = useState(new Date().getFullYear());
  const [opsiLanjut, setOpsiLanjut] = useState(false);
  const [jenis, setJenis] = useState("Semua");
  const [dorks, setDorks] = useState(true);
  const [wajibDoi, setWajibDoi] = useState(true);
  const [wajibPdf, setWajibPdf] = useState(true);
  const [longgar, setLonggar] = useState(true);
  const [saringPredator, setSaringPredator] = useState(true);
  const [cekIndeks, setCekIndeks] = useState(true);
  const [snowball, setSnowball] = useState(true);
  const [topikEn, setTopikEn] = useState("");
  const [email, setEmail] = useState("");
  const [oaKey, setOaKey] = useState("");

  const siap = topik.trim().length > 0 && nasional + internasional > 0;

  function kirim(e) {
    e.preventDefault();
    onSubmit({
      judul_topik: topik.trim(),
      jumlah_nasional: nasional,
      jumlah_internasional: internasional,
      jenis_referensi: jenis,
      umur_maksimal: modeTahun === "umur" ? Number(umur) || 0 : 0,
      tahun_dari: modeTahun === "rentang" ? Number(dari) || 0 : 0,
      tahun_sampai: modeTahun === "rentang" ? Number(sampai) || 0 : 0,
      wajib_ada_DOI: wajibDoi,
      wajib_ada_PDF: wajibPdf,
      longgarkan_jika_kurang: longgar,
      pakai_google_dorks: dorks,
      saring_predator: saringPredator,
      cek_indeks: cekIndeks,
      pakai_snowball: snowball,
      judul_topik_inggris: topikEn.trim(),
      email: email.trim(),
      openalex_api_key: oaKey.trim(),
    });
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -14 }}
      transition={{ duration: 0.35 }}
      className="max-w-6xl mx-auto px-5 py-10 grid lg:grid-cols-[380px_1fr] gap-10 items-start"
    >
      {/* ===== panel brand kiri ===== */}
      <aside className="lg:sticky lg:top-24 space-y-8">
        <div>
          <Label className="mb-4 text-indigo">Pencarian referensi ilmiah</Label>
          <h1 className="font-display text-4xl xl:text-[44px] font-semibold leading-[1.12] tracking-tight">
            Cari referensi,
            <br />
            dapat jumlah <span className="gradient-text">pas.</span>
          </h1>
          <p className="text-abu text-[14px] leading-relaxed mt-4">
            Masukkan satu judul topik — Referensia memburu jurnal, buku, dan skripsi,
            menganalisis relevansinya, lalu mengemas PDF legal dalam ZIP siap Mendeley & Zotero.
            Tidak kurang, tidak lebih.
          </p>
        </div>

        <ul className="space-y-3">
          {FITUR.map(([judul, sub]) => (
            <li key={judul} className="flex gap-3">
              <span className="mt-0.5 w-5 h-5 shrink-0 rounded-full bg-indigodeep/20 border border-indigo/40 text-indigo grid place-items-center">
                <IconCheck className="w-3 h-3" />
              </span>
              <span>
                <span className="block text-[13.5px] font-medium text-teks/90">{judul}</span>
                <span className="block text-[12px] text-abu">{sub}</span>
              </span>
            </li>
          ))}
        </ul>

        <div className="border-t border-line/60 pt-6">
          <Label className="mb-4">Alur kerja</Label>
          <ol className="space-y-4">
            {ALUR.map(([no, judul, sub], i) => (
              <li key={no} className="flex gap-4">
                <span className="font-display text-[13px] font-semibold text-amber/90 tabular-nums pt-0.5">{no}</span>
                <span className="relative">
                  {i < ALUR.length - 1 && (
                    <span className="absolute left-[7px] top-6 bottom-[-14px] w-px bg-line/50" />
                  )}
                  <span className="block text-[13.5px] font-medium text-teks/90">{judul}</span>
                  <span className="block text-[12px] text-abu leading-snug">{sub}</span>
                </span>
              </li>
            ))}
          </ol>
        </div>
      </aside>

      {/* ===== form kanan ===== */}
      <form onSubmit={kirim}>
        <Card className="p-0 overflow-hidden">
          <div className="p-6">
            <Label className="mb-3">Topik</Label>
            <textarea
              className={`${inputCls} min-h-28 resize-y text-[15px] leading-relaxed`}
              placeholder="Contoh: Pengaruh media sosial terhadap prestasi belajar mahasiswa"
              value={topik}
              onChange={(e) => setTopik(e.target.value)}
            />
          </div>

          <div className="p-6 border-t border-line/60">
            <div className="flex items-baseline justify-between mb-3">
              <Label>Kuota referensi</Label>
              <span className="text-[12px] text-abu">
                total <span className="text-teks font-semibold tabular-nums">{nasional + internasional}</span>
              </span>
            </div>
            <div className="grid sm:grid-cols-2 gap-4">
              <Stepper
                label="Nasional" dot="bg-indigo" value={nasional} onChange={setNasional}
                hint="Jurnal / penerbit / repositori Indonesia"
              />
              <Stepper
                label="Internasional" dot="bg-amber" value={internasional} onChange={setInternasional}
                hint="Dicari dengan versi Inggris topikmu"
              />
            </div>
          </div>

          <div className="p-6 border-t border-line/60">
            <Label className="mb-3">Rentang tahun</Label>
            <Segmented
              id="tahun"
              value={modeTahun}
              onChange={setModeTahun}
              options={[
                ["bebas", "Semua tahun"],
                ["umur", "Umur maksimal"],
                ["rentang", "Rentang tahun"],
              ]}
            />
            <AnimatePresence mode="wait">
              {modeTahun === "umur" && (
                <motion.div
                  key="umur"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="pt-4 max-w-56">
                    <Field label="Umur maksimal (tahun)" hint={`Berarti terbit ${new Date().getFullYear() - (Number(umur) || 0)}–${new Date().getFullYear()}`}>
                      <input type="number" min="1" max="50" className={inputCls} value={umur} onChange={(e) => setUmur(e.target.value)} />
                    </Field>
                  </div>
                </motion.div>
              )}
              {modeTahun === "rentang" && (
                <motion.div
                  key="rentang"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="pt-4 grid grid-cols-2 gap-4 max-w-md">
                    <Field label="Dari tahun">
                      <input type="number" min="1900" max="2100" className={inputCls} value={dari} onChange={(e) => setDari(e.target.value)} />
                    </Field>
                    <Field label="Sampai tahun">
                      <input type="number" min="1900" max="2100" className={inputCls} value={sampai} onChange={(e) => setSampai(e.target.value)} />
                    </Field>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            {modeTahun === "bebas" && (
              <p className="text-[12px] text-abu mt-3">Tanpa batasan tahun terbit.</p>
            )}
          </div>

          <div className="border-t border-line/60">
            <button
              type="button"
              onClick={() => setOpsiLanjut(!opsiLanjut)}
              className="w-full flex items-center justify-between px-6 py-4 text-[13px] font-medium text-abu hover:text-teks transition-colors"
            >
              <span>Opsi lanjutan</span>
              <motion.span animate={{ rotate: opsiLanjut ? 180 : 0 }} className="text-abu">
                <Ikon as={ChevronDown} size={15} />
              </motion.span>
            </button>
            <AnimatePresence>
              {opsiLanjut && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="px-6 pb-6 space-y-5">
                    <Field label="Jenis referensi">
                      <select className={inputCls} value={jenis} onChange={(e) => setJenis(e.target.value)}>
                        {JENIS.map((j) => <option key={j} value={j}>{j}</option>)}
                      </select>
                    </Field>
                    <div className="divide-y divide-line/60">
                      <Toggle checked={dorks} onChange={setDorks} label="Google Dorks (filetype:pdf)"
                        hint="Menambah PDF dari repositori kampus & situs jurnal" />
                      <Toggle checked={wajibDoi} onChange={setWajibDoi} label="Wajib punya DOI"
                        hint="Matikan jika mencari skripsi — banyak skripsi tidak ber-DOI" />
                      <Toggle checked={wajibPdf} onChange={setWajibPdf} label="Wajib PDF berhasil diunduh"
                        hint="Jumlah PDF di ZIP = jumlah yang diminta" />
                      <Toggle checked={longgar} onChange={setLonggar} label="Longgarkan jika kurang"
                        hint="Longgarkan tahun → DOI → PDF agar jumlah tetap pas" />
                      <Toggle checked={saringPredator} onChange={setSaringPredator} label="Saring penerbit predator"
                        hint="Kandidat dari penerbit predator (daftar hitam Beall) tidak ikut dipilih" />
                      <Toggle checked={cekIndeks} onChange={setCekIndeks} label="Cek indeks DOAJ & SINTA"
                        hint="Badge kualitas + bonus skor untuk jurnal terindeks DOAJ / terakreditasi SINTA" />
                      <Toggle checked={snowball} onChange={setSnowball} label="Snowballing (jejaring sitasi)"
                        hint="Ikuti sitasi paper unggulan untuk menemukan referensi relevan yang terlewat" />
                    </div>
                    <Field label="Judul versi Inggris (opsional)"
                      hint="Kosongkan agar diterjemahkan otomatis; isi jika topik memakai singkatan khas Indonesia">
                      <input className={inputCls} value={topikEn} onChange={(e) => setTopikEn(e.target.value)} />
                    </Field>
                    <div className="grid sm:grid-cols-2 gap-4">
                      <Field label="Email (opsional)" hint="Membantu menemukan PDF legal lewat Unpaywall">
                        <input className={inputCls} value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nama@email.com" />
                      </Field>
                      <Field label="API key OpenAlex (opsional)" hint="Isi hanya jika muncul pesan kuota habis">
                        <input className={inputCls} value={oaKey} onChange={(e) => setOaKey(e.target.value)} />
                      </Field>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="p-6 border-t border-line/60 bg-bg/40">
            {error && (
              <div className="border border-red-500/40 bg-red-500/10 text-red-400 rounded-xl px-4 py-3 text-sm mb-4">
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={!siap}
              className="gradient-btn w-full rounded-xl py-3.5 text-[15px] font-semibold text-white flex items-center justify-center gap-2.5"
            >
              <IconSearch className="w-4 h-4" />
              Mulai Pencarian
              <IconArrow className="w-4 h-4" />
            </button>
            <p className="text-center text-[11.5px] text-abu mt-3">
              Metadata OpenAlex + Crossref · PDF hanya dari sumber open access / legal
            </p>
          </div>
        </Card>
      </form>
    </motion.div>
  );
}