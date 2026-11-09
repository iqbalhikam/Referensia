import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";
import SearchForm from "./components/SearchForm.jsx";
import ProgressView from "./components/ProgressView.jsx";
import ResultView from "./components/ResultView.jsx";
import LibraryView from "./components/LibraryView.jsx";
import AnalysisView from "./components/AnalysisView.jsx";
import { Welcome, LogoMark } from "./components/Brand.jsx";
import { KonsenPembaruan, SpandukPembaruan, PengaturanPembaruan } from "./components/Update.jsx";
import { startSearch, getJob, health, libraryEntry, downloadUrl, libraryDownloadUrl, cekUpdate } from "./api.js";

const KUNCI_AUTO = "referensia-auto-update";
const KUNCI_TUNDA = "referensia-tunda-pembaruan";

export default function App() {
  const [view, setView] = useState("form");
  const [jobId, setJobId] = useState(null);
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("running");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [durasi, setDurasi] = useState(0);
  const [backendOk, setBackendOk] = useState(null);
  const [splash, setSplash] = useState(true);
  const [src, setSrc] = useState("");
  const [libId, setLibId] = useState("");
  const [initialFav, setInitialFav] = useState([]);
  const [initialNotes, setInitialNotes] = useState({});
  const [zipHref, setZipHref] = useState("");
  const [tema, setTema] = useState(() => localStorage.getItem("referensia-tema") || "dark");
  const [auto, setAuto] = useState(() => {
    const simpan = localStorage.getItem(KUNCI_AUTO);
    return simpan === null ? null : simpan === "1";
  });
  const [rilis, setRilis] = useState(null);
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

  useEffect(() => {
    document.documentElement.dataset.theme = tema;
    localStorage.setItem("referensia-tema", tema);
  }, [tema]);

  useEffect(() => {
    health().then(() => setBackendOk(true)).catch(() => setBackendOk(false));
  }, []);

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
      {backendOk === false && (
        <div className="sticky top-14 z-30 bg-amber-500/15 border-b border-amber-500/40 text-amber-400 text-sm text-center px-4 py-2 backdrop-blur-md">
          ⚠️ Backend Python belum terdeteksi di port 8756 — jalankan dulu servernya (lihat panduan).
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
              className={`px-4 py-1.5 rounded-lg text-[13px] font-medium transition-colors ${
                view === "library"
                  ? "text-teks bg-indigodeep/20 border border-indigo/30"
                  : "text-abu hover:text-teks"
              }`}
            >
              📚 Pustaka
            </button>
            <button
              onClick={() => setBukaPengaturan(true)}
              title="Pengaturan pembaruan"
              className="relative ml-1 w-8 h-8 grid place-items-center rounded-lg text-abu hover:text-teks border border-line/60 transition-colors"
            >
              ⚙️
              {rilis?.ada_baru && <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-amber" />}
            </button>
            <button
              onClick={() => setTema(tema === "dark" ? "light" : "dark")}
              title={tema === "dark" ? "Ganti ke tema terang" : "Ganti ke tema gelap"}
              className="ml-1 w-8 h-8 grid place-items-center rounded-lg text-abu hover:text-teks border border-line/60 transition-colors"
            >
              {tema === "dark" ? "☀️" : "🌙"}
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
                  className="rounded-2xl px-8 py-3 font-bold border border-line text-abu hover:text-teks hover:border-indigo transition-colors"
                >
                  ← Kembali ke Form
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
      </AnimatePresence>
      <AnimatePresence>
        {auto === null && !splash && <KonsenPembaruan key="konsen" onPilih={pilihAuto} />}
        {bukaPengaturan && (
          <PengaturanPembaruan
            key="pengaturan" auto={auto} onAuto={pilihAuto} data={rilis} galat={galatRilis}
            sibuk={lagiCek} onPeriksa={() => periksa(true)} onClose={() => setBukaPengaturan(false)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}