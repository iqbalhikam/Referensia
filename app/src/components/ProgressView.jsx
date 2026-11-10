import { useEffect, useMemo, useRef } from "react";
import { motion } from "framer-motion";
import { Card } from "./ui.jsx";
import { LoadingAnim } from "./Brand.jsx";
import { Ikon, CheckCircle2, Flag, Globe2, Loader2, SearchX, TriangleAlert } from "./icons.jsx";

function parseKuota(events) {
  const kuota = { Nasional: null, Internasional: null };
  for (const ev of events) {
    if (ev.event === "log") {
      const m = ev.text.match(/(Nasional|Internasional): (\d+)\/(\d+)/);
      if (m) kuota[m[1]] = { n: Number(m[2]), target: Number(m[3]) };
    }
    if (ev.event === "verification") {
      for (const [kat, c] of Object.entries(ev.counts)) kuota[kat] = c;
    }
  }
  return kuota;
}

function parseTahap(events) {
  let tahap = "";
  for (const ev of events) {
    if (ev.event === "log") {
      const m = ev.text.match(/\[(\d)\/4\]\s*(.+)/);
      if (m) tahap = `${m[1]}/4 — ${m[2].replace(/…\s*$/, "")}`;
    }
  }
  return tahap;
}

export default function ProgressView({ events, durasi, status, error }) {
  const logRef = useRef(null);
  const kuota = useMemo(() => parseKuota(events), [events]);
  const tahap = useMemo(() => parseTahap(events), [events]);
  const logs = useMemo(() => events.filter((e) => e.event === "log"), [events]);

  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [logs.length]);

  const menit = Math.floor(durasi / 60);
  const detik = durasi % 60;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      className="max-w-3xl mx-auto px-5 py-10"
    >
      <div className="flex flex-col items-center gap-4 mb-6">
        {status === "running" && <LoadingAnim size={110} />}
        <div className="flex items-center gap-3">
          <div className="inline-flex items-center gap-2 text-lg font-extrabold">
            {status === "done" && <Ikon as={CheckCircle2} size={20} className="text-emerald-400" />}
            {status === "empty" && <Ikon as={SearchX} size={20} className="text-abu" />}
            {status === "error" && <Ikon as={TriangleAlert} size={20} className="text-amber-400" />}
            {status === "running" && (tahap || "Menyiapkan mesin…")}
            {status === "done" && "Selesai! Menyiapkan hasil…"}
            {status === "empty" && "Tidak ada referensi yang cocok"}
            {status === "error" && "Terjadi kesalahan"}
          </div>
          <span className="text-abu text-sm tabular-nums">
            {menit}:{String(detik).padStart(2, "0")}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-5">
        {["Nasional", "Internasional"].map((kat) => {
          const k = kuota[kat];
          const warna = kat === "Nasional" ? "border-indigo text-indigo" : "border-amber text-amber";
          const IkonKat = kat === "Nasional" ? Flag : Globe2;
          const pas = k && k.n === k.target;
          return (
            <Card key={kat} className={`text-center border-2 ${warna.split(" ")[0]}`}>
              <div className="inline-flex items-center gap-1.5 text-sm text-abu">
                <Ikon as={IkonKat} size={14} />
                {kat.toUpperCase()}
              </div>
              <div className={`text-5xl font-black my-2 ${warna.split(" ")[1]}`}>
                {k ? k.n : "–"}
                <span className="text-2xl text-abu font-bold">/{k ? k.target : "?"}</span>
              </div>
              <div className="inline-flex items-center gap-1.5 text-sm">
                {!k && "menunggu…"}
                {k && pas && <><Ikon as={CheckCircle2} size={15} className="text-emerald-400" />PAS</>}
                {k && !pas && <><Ikon as={Loader2} size={15} className="animate-spin text-amber" />mencari…</>}
              </div>
              {k && (
                <div className="h-1.5 bg-line rounded-full mt-3 overflow-hidden">
                  <motion.div
                    className={`h-full rounded-full ${kat === "Nasional" ? "bg-indigo" : "bg-amber"}`}
                    animate={{ width: `${Math.min(100, (k.n / Math.max(1, k.target)) * 100)}%` }}
                  />
                </div>
              )}
            </Card>
          );
        })}
      </div>

      {error && (
        <div className="border border-red-500/40 bg-red-500/10 text-red-400 rounded-xl px-4 py-3 text-sm mb-5">
          {error}
        </div>
      )}

      <Card className="p-0 overflow-hidden">
        <div className="px-4 py-2.5 border-b border-line text-[12px] font-bold text-abu uppercase tracking-wider">
          Log mesin
        </div>
        <div ref={logRef} className="h-72 overflow-y-auto px-4 py-3 font-mono text-[12.5px] leading-relaxed bg-bg/60">
          {logs.map((ev, i) => {
            const tone = ev.tone || (ev.text.startsWith("   ✓") ? "ok" : "");
            return (
              <div key={i} className="text-abu whitespace-pre-wrap break-words">
                <span className="text-abu/40 select-none">{String(ev.t ?? 0).padStart(6)}s </span>
                <span className={tone === "warn" ? "text-amber-400" : tone === "ok" ? "text-emerald-400" : ""}>
                  {ev.text}
                </span>
              </div>
            );
          })}
          {status === "running" && (
            <motion.span animate={{ opacity: [1, 0] }} transition={{ repeat: Infinity, duration: 0.8 }} className="text-amber">
              ▌
            </motion.span>
          )}
        </div>
      </Card>

      <p className="text-center text-[12px] text-abu mt-4">
        Pencarian bisa memakan beberapa menit tergantung jumlah referensi & kecepatan unduh PDF.
      </p>
    </motion.div>
  );
}