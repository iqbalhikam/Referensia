import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";
import SearchForm from "./components/SearchForm.jsx";
import ProgressView from "./components/ProgressView.jsx";
import ResultView from "./components/ResultView.jsx";
import LibraryView from "./components/LibraryView.jsx";
import AnalysisView from "./components/AnalysisView.jsx";
import CitationPageFinder from "./components/CitationPageFinder.jsx";
import SkripsiChecker from "./components/SkripsiChecker.jsx";
import { Welcome, LogoMark } from "./components/Brand.jsx";
import { KonsenPembaruan, SpandukPembaruan, PengaturanPembaruan } from "./components/Update.jsx";
import { Ikon, ArrowLeft, BookOpen, CheckCircle2, Droplets, Library, Loader2, Moon, Settings, Sun, TriangleAlert } from "./components/icons.jsx";
import { startSearch, getJob, health, libraryEntry, downloadUrl, libraryDownloadUrl, cekUpdate } from "./api.js";

const KUNCI_AUTO = "referensia-auto-update";
const KUNCI_TUNDA = "referensia-tunda-pembaruan";
const URUTAN_TEMA = ["dark", "light", "glass"];
const IKON_TEMA = { dark: Moon, light: Sun, glass: Droplets };
const NAMA_TEMA = { dark: "Gelap", light: "Terang", glass: "Liquid Glass" };

export default function App() {
  const [view, setView] = useState("form");
  const [jobId, setJobId] = useState(null);
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("running");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [durasi, setDurasi] = useState(0);
  const [backendOk, setBackendOk] = useState(null); // null = sedang menyambung
  const menyambung = useRef(false);
  const [splash, setSplash] = useState(true);
  const [src, setSrc] = useState("");
  const [libId, setLibId] = useState("");
  const [initialFav, setInitialFav] = useState([]);
  const [initialNotes, setInitialNotes] = useState({});
  const [zipHref, setZipHref] = useState("");
  const [tema, setTema] = useState(() => {
    const simpan = localStorage.getItem("referensia-tema");
    return URUTAN_TEMA.includes(simpan) ? simpan : "dark";
  });
  const [auto, setAuto] = useState(() => {
    const simpan = localStorage.getItem(KUNCI_AUTO);
    return simpan === null ? null : simpan === "1";
  });
  const [rilis, setRilis] = useState(null);
  const [versi, setVersi] = useState("");
  const [galatRilis, setGalatRilis] = useState("");
  const [lagiCek, setLagiCek] = useState(false);
  const [bukaPengaturan, setBukaPengaturan] = useState(false);
  const [spandukTutup, setSpandukTutup] = useState(false);
  const cursor = useRef(0);
  const selesaiSplash = useCallback(() => setSplash(false), []);

  const periksa = useCallback(async (paksa = false) => {
    setLagiCek(true);
    try {
      setRilis(await cekUpdate(paksa));
      setGalatRilis("");
    } catch (e) {
      setGalatRilis(e.message);
    } finally {
      setLagiCek(false);
    }
  }, []);

  function pilihAuto(nyalakan) {
    localStorage.setItem(KUNCI_AUTO, nyalakan ? "1" : "0");
    setAuto(nyalakan);
    setSpandukTutup(false);
    if (nyalakan) periksa(true);
  }

  const putarTema = () => setTema((t) => URUTAN_TEMA[(URUTAN_TEMA.indexOf(t) + 1) % URUTAN_TEMA.length]);

  useEffect(() => {
    document.documentElement.dataset.theme = tema;
    localStorage.setItem("referensia-tema", tema);
  }, [tema]);

  // Sidecar PyInstaller butuh beberapa detik di pembukaan pertama — ulangi
  // pemeriksaan alih-alih langsung menyimpulkan backend mati.
  const sambungBackend = useCallback(async () => {
    if (menyambung.current) return;
    menyambung.current = true;
    setBackendOk(null);
    try {
      for (let i = 0; i < 40; i++) {
        try {
          const d = await health();
          setBackendOk(true);
          setVersi(d.versi || "");
          return;
        } catch {
          if (i >= 7) setBackendOk(false); // peringatan tampil, percobaan tetap lanjut
          await new Promise((r) => setTimeout(r, 1000));
        }
      }
      setBackendOk(false);
    } finally {
      menyambung.current = false;
    }
  }, []);

  useEffect(() => {
    sambungBackend();
  }, [sambungBackend]);

  // Pemeriksaan senyap saat aplikasi dibuka — hanya bila pengguna mengizinkan
  // dan spanduk sebelumnya tidak sedang ditunda ("Nanti dulu").
  useEffect(() => {
    if (backendOk !== true || auto !== true) return;
    if (Number(localStorage.getItem(KUNCI_TUNDA) || 0) > Date.now()) return;
    periksa(false);
  }, [backendOk, auto, periksa]);

  useEffect(() => {
    if (view !== "progress" || !jobId) return;
    let aktif = true;
    const timer = setInterval(async () => {
      try {
        const d = await getJob(jobId, cursor.current);
        if (!aktif) return;
        cursor.current = d.next;
        setEvents((prev) => [...prev, ...d.events]);
        setDurasi(d.durasi);
        setStatus(d.status);
        setBackendOk(true);
        if (d.status === "done" && d.result) {
          setResult(d.result);
          setSrc(`job:${jobId}`);
          setLibId(jobId);
          setInitialFav([]);
          setInitialNotes({});
          setZipHref(downloadUrl(jobId));
          setView("result");
        }
        if (d.status === "error") setError(d.error || "Kesalahan tidak diketahui");
      } catch {
        if (aktif) setBackendOk(false);
      }
    }, 1200);
    return () => {
      aktif = false;
      clearInterval(timer);
    };
  }, [view, jobId]);

  async function mulai(params) {
    setError("");
    try {
      const d = await startSearch(params);
      cursor.current = 0;
      setEvents([]);
      setResult(null);
      setStatus("running");
      setDurasi(0);
      setJobId(d.job_id);
      setView("progress");
    } catch (e) {
      setError(e.message);
    }
  }

  async function bukaPustaka(id) {
    setError("");
    try {
      const e = await libraryEntry(id);
      setResult(e.result);
      setSrc(`lib:${id}`);
      setLibId(id);
      setInitialFav(e.favorit || []);
      setInitialNotes(e.catatan || {});
      setZipHref(libraryDownloadUrl(id));
      setView("result");
    } catch (e) {
      setError(e.message);
    }
  }

  function reset() {
    setView("form");
    setJobId(null);
    setEvents([]);
    setResult(null);
    setError("");
    setSrc("");
    setLibId("");
    setInitialFav([]);
    setInitialNotes({});
    setZipHref("");
  }

  return (
    <div className="min-h-screen">
      {splash && <Welcome onDone={selesaiSplash} />}
      {backendOk === null && (
        <div className="sticky top-14 z-30 bg-indigodeep/15 border-b border-indigo/40 text-indigo text-sm text-center px-4 py-2 backdrop-blur-md">
          <Ikon as={Loader2} size={15} className="animate-spin mr-1.5" />
          Menyambungkan ke mesin Referensia… <span className="text-abu text-[12.5px]">(pembukaan pertama bisa 10–20 detik)</span>
        </div>
      )}
      {backendOk === false && (
        <div className="sticky top-14 z-30 bg-amber-500/15 border-b border-amber-500/40 text-amber-400 text-sm text-center px-4 py-2 backdrop-blur-md">
          <Ikon as={TriangleAlert} size={15} className="mr-1.5" />
          Mesin Referensia di port 8756 belum merespons.
          <button onClick={sambungBackend} className="ml-2 font-semibold underline hover:text-amber-300">
            Coba lagi
          </button>
          <span className="block text-[12px] text-amber-400/80 mt-0.5">
            Mode browser: pastikan <code>python backend/server.py</code> berjalan. Log: Documents\Referensia\backend.log
          </span>
        </div>
      )}
      {rilis?.ada_baru && !spandukTutup && (
        <SpandukPembaruan
          data={rilis}
          onNanti={() => {
            localStorage.setItem(KUNCI_TUNDA, String(Date.now() + 86400000));
            setSpandukTutup(true);
          }}
          onPengaturan={() => setBukaPengaturan(true)}
        />
      )}
      <header className="sticky top-0 z-40 backdrop-blur-md bg-bg/70 border-b border-line/60">
        <div className="max-w-6xl mx-auto px-5 h-14 flex items-center">
          <div className="flex items-center gap-2.5">
            <LogoMark className="w-7 h-7" />
            <span className="font-display font-bold text-lg tracking-tight">Referensia</span>
          </div>
          <nav className="ml-auto flex items-center gap-1">
            <button
              onClick={reset}
              className={`px-4 py-1.5 rounded-lg text-[13px] font-medium transition-colors ${
                view === "form" || view === "progress" || view === "result" || view === "analysis"
                  ? "text-teks bg-indigodeep/20 border border-indigo/30"
                  : "text-abu hover:text-teks"
              }`}
            >
              Pencarian
            </button>
            <button
              onClick={() => setView("library")}
              className={`px-4 py-1.5 rounded-lg text-[13px] font-medium transition-colors inline-flex items-center gap-1.5 ${
                view === "library"
                  ? "text-teks bg-indigodeep/20 border border-indigo/30"
                  : "text-abu hover:text-teks"
              }`}
            >
              <Ikon as={Library} size={15} />
              Pustaka
            </button>
            <button
              onClick={() => setView("citation-page")}
              className={`px-4 py-1.5 rounded-lg text-[13px] font-medium transition-colors inline-flex items-center gap-1.5 ${
                view === "citation-page"
                  ? "text-teks bg-indigodeep/20 border border-indigo/30"
                  : "text-abu hover:text-teks"
              }`}
            >
              <Ikon as={BookOpen} size={15} />
              Halaman Sitasi
            </button>
            <button
              onClick={() => setView("skripsi-checker")}
              className={`px-4 py-1.5 rounded-lg text-[13px] font-medium transition-colors inline-flex items-center gap-1.5 ${
                view === "skripsi-checker"
                  ? "text-teks bg-indigodeep/20 border border-indigo/30"
                  : "text-abu hover:text-teks"
              }`}
            >
              <Ikon as={CheckCircle2} size={15} />
              Skripsi Checker
            </button>
            <button
              onClick={() => setBukaPengaturan(true)}
              title="Pengaturan tampilan & pembaruan"
              className="relative ml-1 w-8 h-8 grid place-items-center rounded-lg text-abu hover:text-teks border border-line/60 transition-colors"
            >
              <Ikon as={Settings} size={16} />
              {rilis?.ada_baru && <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-amber" />}
            </button>
            <button
              onClick={putarTema}
              title={`Tema ${NAMA_TEMA[tema]} — klik untuk ${NAMA_TEMA[URUTAN_TEMA[(URUTAN_TEMA.indexOf(tema) + 1) % URUTAN_TEMA.length]]}`}
              className="ml-1 w-8 h-8 grid place-items-center rounded-lg text-abu hover:text-teks border border-line/60 transition-colors"
            >
              <Ikon as={IKON_TEMA[tema]} size={16} />
            </button>
          </nav>
        </div>
      </header>
      <AnimatePresence mode="wait">
        {view === "form" && <SearchForm key="form" onSubmit={mulai} error={error} />}
        {view === "progress" && (
          <div key="progress">
            <ProgressView events={events} durasi={durasi} status={status} error={status === "error" ? error : ""} />
            {(status === "empty" || status === "error") && (
              <div className="text-center pb-10 -mt-4">
                <button
                  onClick={reset}
                  className="inline-flex items-center gap-2 rounded-2xl px-8 py-3 font-bold border border-line text-abu hover:text-teks hover:border-indigo transition-colors"
                >
                  <Ikon as={ArrowLeft} size={16} />
                  Kembali ke Form
                </button>
              </div>
            )}
          </div>
        )}
        {view === "result" && result && (
          <ResultView
            key="result" result={result} src={src} libId={libId}
            initialFav={initialFav} initialNotes={initialNotes} zipHref={zipHref} onReset={reset}
            onAnalisis={() => setView("analysis")}
          />
        )}
        {view === "analysis" && result && (
          <AnalysisView
            key="analysis" result={result} src={src}
            onBack={() => setView("result")}
          />
        )}
        {view === "library" && (
          <LibraryView key="library" onOpen={bukaPustaka} onBack={reset} />
        )}
        {view === "citation-page" && (
          <CitationPageFinder key="citation-page" onBack={reset} />
        )}
        {view === "skripsi-checker" && (
          <SkripsiChecker key="skripsi-checker" onBack={reset} />
        )}
      </AnimatePresence>
      <AnimatePresence>
        {auto === null && !splash && <KonsenPembaruan key="konsen" onPilih={pilihAuto} />}
        {bukaPengaturan && (
          <PengaturanPembaruan
            key="pengaturan" auto={auto} onAuto={pilihAuto} data={rilis} versi={versi} galat={galatRilis}
            sibuk={lagiCek} onPeriksa={() => periksa(true)} onClose={() => setBukaPengaturan(false)}
            tema={tema} onTema={setTema}
          />
        )}
      </AnimatePresence>
    </div>
  );
}