import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Card, SectionTitle, SalinBtn, inputCls, Field } from "./ui.jsx";
import {
  Ikon, ArrowLeft, BookMarked, Calculator, Compass, Download, Flag, FlaskConical,
  Globe2, KeyRound, Minus, Network, Plus, Puzzle, Sparkles, TrendingUp, TriangleAlert, Trophy,
} from "./icons.jsx";
import { jaringanSitasi, asistenAI } from "../api.js";

const TABS = [
  ["tren", "Tren & Gap", TrendingUp],
  ["jaringan", "Jaringan Sitasi", Network],
  ["ai", "Asisten AI", Sparkles],
];

const KOSONG = { tahun: [], sumber: [], pendekatan: {}, analisis: {}, indeks: {}, kunci: {}, klaster: [], gap: [] };

function JudulBagian({ ikon, children }) {
  return (
    <SectionTitle color="text-indigo">
      <span className="inline-flex items-center gap-2">
        <Ikon as={ikon} size={15} />
        {children}
      </span>
    </SectionTitle>
  );
}

export default function AnalysisView({ result, src, onBack }) {
  const [tab, setTab] = useState("tren");
  const analisis = result.analisis || KOSONG;
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      className="max-w-6xl mx-auto px-5 py-8"
    >
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <button onClick={onBack} className="inline-flex items-center gap-1.5 text-[12.5px] font-bold text-abu hover:text-teks mb-2">
            <Ikon as={ArrowLeft} size={14} />
            Kembali ke hasil
          </button>
          <h1 className="font-display text-2xl font-semibold text-teks">Analisis lanjutan</h1>
          <p className="text-sm text-abu mt-1">{result.topik}</p>
        </div>
        <div className="flex gap-1.5 rounded-xl border border-line bg-panel/60 p-1">
          {TABS.map(([id, label, IkonTab]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-[13px] font-bold transition-colors ${
                tab === id ? "bg-indigodeep/25 text-teks border border-indigo/30" : "text-abu hover:text-teks"
              }`}
            >
              <Ikon as={IkonTab} size={14} />
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6">
        {tab === "tren" && <Tren result={result} analisis={analisis} />}
        {tab === "jaringan" && <Jaringan src={src} />}
        {tab === "ai" && <Asisten src={src} />}
      </div>
    </motion.div>
  );
}

function Tren({ result, analisis }) {
  const semua = ["Nasional", "Internasional"].flatMap((k) => result.hasil[k] || []);
  const tahun = analisis.tahun || [];
  const maks = Math.max(1, ...tahun.map((t) => t.Nasional + t.Internasional));
  const total = semua.length;
  const tahunAda = semua.map((r) => r.tahun).filter(Boolean);
  const rentang = tahunAda.length ? `${Math.min(...tahunAda)}–${Math.max(...tahunAda)}` : "—";
  const sitasi = semua.map((r) => r.sitasi || 0);
  const median = sitasi.length
    ? [...sitasi].sort((a, b) => a - b)[Math.floor(sitasi.length / 2)]
    : 0;
  const pendekatan = Object.entries(analisis.pendekatan || {}).sort((a, b) => b[1] - a[1]);
  const analisisTeknik = Object.entries(analisis.analisis || {}).sort((a, b) => b[1] - a[1]).slice(0, 8);

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          ["Rentang tahun", rentang],
          ["Median sitasi", `${median}×`],
          ["Terindeks DOAJ", analisis.indeks?.DOAJ ?? 0],
          ["Terakreditasi SINTA", analisis.indeks?.SINTA ?? 0],
        ].map(([label, nilai]) => (
          <Card key={label} className="text-center py-4">
            <div className="text-2xl font-black gradient-text">{nilai}</div>
            <div className="text-[12px] text-abu mt-1">{label}</div>
          </Card>
        ))}
      </div>

      <Card>
        <JudulBagian ikon={TrendingUp}>Sebaran tahun terbit</JudulBagian>
        {tahun.length ? (
          <>
            <div className="flex items-end gap-2 h-44 overflow-x-auto pb-1">
              {tahun.map((t) => {
                const n = t.Nasional + t.Internasional;
                return (
                  <div key={t.tahun} className="flex-1 min-w-[44px] flex flex-col items-center justify-end gap-1">
                    <div className="text-[11px] text-abu">{n}</div>
                    <div className="w-full flex flex-col justify-end" style={{ height: 124 }}>
                      {t.Internasional > 0 && (
                        <div
                          className="w-full bg-amber rounded-t"
                          style={{ height: `${(t.Internasional / maks) * 124}px` }}
                          title={`Internasional ${t.Internasional}`}
                        />
                      )}
                      {t.Nasional > 0 && (
                        <div
                          className={`w-full bg-indigo ${t.Internasional ? "" : "rounded-t"}`}
                          style={{ height: `${(t.Nasional / maks) * 124}px` }}
                          title={`Nasional ${t.Nasional}`}
                        />
                      )}
                    </div>
                    <div className="text-[11px] text-abu">{t.tahun}</div>
                  </div>
                );
              })}
            </div>
            <div className="flex gap-4 text-[12px] text-abu mt-3">
              <span><i className="inline-block w-2.5 h-2.5 rounded-sm bg-indigo mr-1.5" />Nasional</span>
              <span><i className="inline-block w-2.5 h-2.5 rounded-sm bg-amber mr-1.5" />Internasional</span>
            </div>
          </>
        ) : (
          <p className="text-sm text-abu">Tahun terbit tidak tersedia pada referensi ini.</p>
        )}
      </Card>

      <div className="grid md:grid-cols-2 gap-4">
        <Card>
          <JudulBagian ikon={FlaskConical}>Pendekatan penelitian</JudulBagian>
          {pendekatan.length ? (
            <div className="space-y-2.5">
              {pendekatan.map(([label, n]) => (
                <div key={label}>
                  <div className="flex justify-between text-[12.5px] mb-1">
                    <span className="text-teks">{label}</span>
                    <span className="text-abu">{n} · {Math.round((n / total) * 100)}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-line/60 overflow-hidden">
                    <div className="h-full rounded-full bg-indigo" style={{ width: `${(n / total) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-abu">Pendekatan belum terdeteksi dari abstrak.</p>
          )}
        </Card>

        <Card>
          <JudulBagian ikon={Calculator}>Teknik analisis terbanyak</JudulBagian>
          {analisisTeknik.length ? (
            <div className="space-y-2.5">
              {analisisTeknik.map(([label, n]) => (
                <div key={label}>
                  <div className="flex justify-between text-[12.5px] mb-1">
                    <span className="text-teks">{label}</span>
                    <span className="text-abu">{n} referensi</span>
                  </div>
                  <div className="h-2 rounded-full bg-line/60 overflow-hidden">
                    <div className="h-full rounded-full bg-amber" style={{ width: `${(n / Math.max(1, analisisTeknik[0][1])) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-abu">Teknik analisis belum terdeteksi.</p>
          )}
        </Card>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card>
          <JudulBagian ikon={BookMarked}>Jurnal paling sering muncul</JudulBagian>
          {analisis.sumber?.length ? (
            <div className="space-y-2">
              {analisis.sumber.map((s, i) => (
                <div key={s.nama} className="flex items-start gap-2.5 text-[13px]">
                  <span className="w-5 h-5 shrink-0 rounded-md bg-panel2 text-[11px] font-bold grid place-items-center text-abu">
                    {i + 1}
                  </span>
                  <span className="flex-1 text-teks leading-snug">{s.nama}</span>
                  <span className="text-abu tabular-nums">{s.jumlah}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-abu">Nama jurnal tidak tersedia.</p>
          )}
        </Card>

        <Card>
          <JudulBagian ikon={KeyRound}>Kata kunci yang paling dibahas</JudulBagian>
          {["Nasional", "Internasional"].map((kat) =>
            analisis.kunci?.[kat]?.length ? (
              <div key={kat} className="mb-4 last:mb-0">
                <div className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-abu mb-2">
                  <Ikon as={kat === "Nasional" ? Flag : Globe2} size={12} />
                  {kat}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {analisis.kunci[kat].map((k) => (
                    <span key={k.kata} className="rounded-full border border-line bg-bg/40 px-2.5 py-1 text-[12px] text-teks">
                      {k.kata} <span className="text-abu">{k.jumlah}</span>
                    </span>
                  ))}
                </div>
              </div>
            ) : null
          )}
          {!analisis.kunci?.Nasional?.length && !analisis.kunci?.Internasional?.length && (
            <p className="text-sm text-abu">Kata kunci tidak tersedia pada entri lama.</p>
          )}
        </Card>
      </div>

      {analisis.klaster?.length > 0 && (
        <Card>
          <JudulBagian ikon={Puzzle}>Klaster topik</JudulBagian>
          <div className="grid md:grid-cols-2 gap-3">
            {analisis.klaster.map((k, i) => (
              <div key={i} className="rounded-xl border border-line bg-bg/40 px-3.5 py-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-[13px] font-bold text-teks leading-snug">{k.label}</div>
                  <span className="text-[11px] text-abu shrink-0">{k.jumlah} referensi</span>
                </div>
                <ul className="mt-2 space-y-1 text-[12px] text-abu list-disc pl-4">
                  {k.judul.map((j, n) => (
                    <li key={n} className="leading-snug">{j}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card>
        <JudulBagian ikon={Compass}>Petunjuk celah penelitian (dari abstrak)</JudulBagian>
        {analisis.gap?.length ? (
          <div className="space-y-3">
            {analisis.gap.map((g, i) => (
              <blockquote key={i} className="border-l-2 border-amber/70 pl-3.5">
                <p className="text-[13px] text-teks leading-relaxed">“{g.teks}”</p>
                <p className="text-[11.5px] text-abu mt-1">
                  — {g.judul} ({g.tahun || "—"})
                </p>
              </blockquote>
            ))}
            <p className="text-[11.5px] text-abu">
              Kutipan diambil apa adanya dari abstrak, bukan kesimpulan otomatis. Gunakan sebagai bahan
              awal, lalu baca paper aslinya.
            </p>
          </div>
        ) : (
          <p className="text-sm text-abu">
            Tidak ada kalimat penanda celah penelitian yang terdeteksi. Coba cari lebih banyak referensi
            atau gunakan Asisten AI untuk menyusun gap dari abstrak yang ada.
          </p>
        )}
      </Card>
    </div>
  );
}

function hitungTataLetak(nodes, edges, lebar = 780, tinggi = 480) {
  if (!nodes.length) return [];
  const pos = nodes.map((n, i) => {
    const sudut = (2 * Math.PI * i) / nodes.length;
    const r = Math.min(lebar, tinggi) * 0.33;
    return { ...n, x: lebar / 2 + Math.cos(sudut) * r, y: tinggi / 2 + Math.sin(sudut) * r, vx: 0, vy: 0 };
  });
  const indeks = new Map(pos.map((p, i) => [p.id, i]));
  const tautan = edges
    .map((e) => [indeks.get(e.source), indeks.get(e.target)])
    .filter(([a, b]) => a !== undefined && b !== undefined);
  for (let it = 0; it < 240; it++) {
    const alpha = 1 - it / 240;
    for (let i = 0; i < pos.length; i++) {
      for (let j = i + 1; j < pos.length; j++) {
        let dx = pos[j].x - pos[i].x;
        let dy = pos[j].y - pos[i].y;
        const d2 = dx * dx + dy * dy || 0.01;
        const d = Math.sqrt(d2);
        const gaya = 6200 / d2;
        dx /= d;
        dy /= d;
        pos[i].vx -= dx * gaya;
        pos[i].vy -= dy * gaya;
        pos[j].vx += dx * gaya;
        pos[j].vy += dy * gaya;
      }
    }
    for (const [a, b] of tautan) {
      let dx = pos[b].x - pos[a].x;
      let dy = pos[b].y - pos[a].y;
      const d = Math.hypot(dx, dy) || 0.01;
      const gaya = (d - 130) * 0.014;
      dx /= d;
      dy /= d;
      pos[a].vx += dx * gaya;
      pos[a].vy += dy * gaya;
      pos[b].vx -= dx * gaya;
      pos[b].vy -= dy * gaya;
    }
    for (const p of pos) {
      p.vx += (lebar / 2 - p.x) * 0.002;
      p.vy += (tinggi / 2 - p.y) * 0.002;
      p.x = Math.max(28, Math.min(lebar - 28, p.x + p.vx * alpha));
      p.y = Math.max(28, Math.min(tinggi - 28, p.y + p.vy * alpha));
      p.vx *= 0.55;
      p.vy *= 0.55;
    }
  }
  return pos;
}

const CACHE_JARINGAN = new Map();

function Jaringan({ src }) {
  const [data, setData] = useState(() => CACHE_JARINGAN.get(src) || null);
  const [err, setErr] = useState("");
  const [sibuk, setSibuk] = useState(() => !CACHE_JARINGAN.has(src));

  async function muat() {
    setSibuk(true);
    setErr("");
    try {
      const d = await jaringanSitasi(src);
      CACHE_JARINGAN.set(src, d);
      setData(d);
    } catch (e) {
      setErr(e.message);
    } finally {
      setSibuk(false);
    }
  }

  useEffect(() => {
    if (!CACHE_JARINGAN.has(src)) muat();
  }, [src]);

  if (sibuk) {
    return (
      <Card className="text-center py-12">
        <Ikon as={Network} size={38} className="text-indigo/70 mb-3" strokeWidth={1.5} />
        <div className="font-bold">Menghubungi OpenAlex…</div>
        <p className="text-sm text-abu mt-1">Mengambil daftar referensi & sitasi tiap paper (bisa 30–60 detik).</p>
      </Card>
    );
  }
  if (err) {
    return (
      <Card className="text-center py-10">
        <div className="inline-flex items-center gap-1.5 text-sm text-amber mb-3">
          <Ikon as={TriangleAlert} size={15} />
          {err}
        </div>
        <button onClick={muat} className="rounded-xl border border-line px-5 py-2.5 text-[13px] font-bold hover:border-indigo">
          Coba lagi
        </button>
      </Card>
    );
  }
  if (!data?.nodes?.length) {
    return (
      <Card>
        <p className="text-sm text-abu">{data?.catatan || "Jaringan sitasi tidak bisa dibangun dari referensi ini."}</p>
      </Card>
    );
  }
  return <Graf data={data} />;
}

function Graf({ data }) {
  const lebar = 780;
  const tinggi = 480;
  const [zoom, setZoom] = useState(1);
  const [geser, setGeser] = useState({ x: 0, y: 0 });
  const tarik = useRef(null);
  const kotak = useRef(null);
  const tata = useMemo(() => hitungTataLetak(data.nodes, data.edges, lebar, tinggi), [data]);
  const peta = useMemo(() => new Map(tata.map((n) => [n.id, n])), [tata]);
  const maksSitasi = Math.max(1, ...data.nodes.map((n) => n.sitasi || 0));

  useEffect(() => {
    const el = kotak.current;
    if (!el) return;
    const onWheel = (e) => {
      e.preventDefault();
      setZoom((z) => Math.max(0.5, Math.min(2.6, z - e.deltaY * 0.0012)));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  function mulai(e) {
    const r = e.currentTarget.getBoundingClientRect();
    tarik.current = { x: e.clientX, y: e.clientY, gx: geser.x, gy: geser.y, skala: lebar / r.width };
    e.currentTarget.setPointerCapture?.(e.pointerId);
  }
  function gerak(e) {
    if (!tarik.current) return;
    setGeser({
      x: tarik.current.gx + (e.clientX - tarik.current.x) * tarik.current.skala,
      y: tarik.current.gy + (e.clientY - tarik.current.y) * tarik.current.skala,
    });
  }
  function lepas() {
    tarik.current = null;
  }

  return (
    <div className="space-y-4">
      <Card className="p-0 overflow-hidden">
        <div className="flex items-center justify-between gap-3 px-4 py-2.5 border-b border-line flex-wrap">
          <div className="text-[12px] text-abu">
            {data.jumlah.dikenali} paper dikenali · {data.jumlah.luar} karya luar · {data.jumlah.koneksi} koneksi sitasi
          </div>
          <div className="flex items-center gap-1.5">
            <button onClick={() => setZoom((z) => Math.min(2.6, z + 0.2))} title="Perbesar" className="w-7 h-7 grid place-items-center rounded-lg border border-line text-abu hover:text-teks">
              <Ikon as={Plus} size={14} />
            </button>
            <button onClick={() => setZoom((z) => Math.max(0.5, z - 0.2))} title="Perkecil" className="w-7 h-7 grid place-items-center rounded-lg border border-line text-abu hover:text-teks">
              <Ikon as={Minus} size={14} />
            </button>
            <button
              onClick={() => { setZoom(1); setGeser({ x: 0, y: 0 }); }}
              className="px-2.5 h-7 rounded-lg border border-line text-[12px] text-abu hover:text-teks"
            >
              Reset
            </button>
          </div>
        </div>
        <div ref={kotak} className="bg-bg/50">
          <svg
            viewBox={`0 0 ${lebar} ${tinggi}`}
            className="w-full h-auto cursor-grab active:cursor-grabbing touch-none select-none"
            onPointerDown={mulai}
            onPointerMove={gerak}
            onPointerUp={lepas}
            onPointerLeave={lepas}
          >
            <defs>
              <marker id="panah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--rf-abu)" />
              </marker>
            </defs>
            <g transform={`translate(${geser.x} ${geser.y}) scale(${zoom})`}>
              {data.edges.map((e, i) => {
                const a = peta.get(e.source);
                const b = peta.get(e.target);
                if (!a || !b) return null;
                return (
                  <line
                    key={i}
                    x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                    stroke="var(--rf-abu)" strokeWidth={1.1} strokeOpacity={0.55}
                    markerEnd="url(#panah)"
                  />
                );
              })}
              {tata.map((n) => {
                const r = 6 + Math.min(14, Math.sqrt((n.sitasi || 0) / maksSitasi) * 15);
                const warna = n.luar ? "transparent" : n.kategori === "Nasional" ? "var(--rf-indigo)" : "var(--rf-amber)";
                return (
                  <g key={n.id}>
                    <circle
                      cx={n.x} cy={n.y} r={r}
                      fill={warna}
                      stroke={n.luar ? "var(--rf-abu)" : "var(--rf-bg)"}
                      strokeWidth={n.luar ? 1.5 : 1}
                      strokeDasharray={n.luar ? "3 2" : undefined}
                    >
                      <title>{`${n.label}\n${n.tahun || "—"} · dikutip ${n.sitasi}×`}</title>
                    </circle>
                    <text
                      x={n.x} y={n.y + r + 10}
                      textAnchor="middle" fontSize={9.5}
                      fill={n.luar ? "var(--rf-abu)" : "var(--rf-teks)"}
                    >
                      {(n.label || "").slice(0, 34)}{(n.label || "").length > 34 ? "…" : ""}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>
        </div>
      </Card>

      <p className="text-[12px] text-abu">
        Geser untuk menggeser, scroll/zoom untuk memperbesar. Panah berarti “mengutip”: ujung panah adalah
        paper yang dikutip. Lingkaran putus-putus = karya luar yang dikutip minimal dua paper terpilih.
        {data.catatan ? ` ${data.catatan}` : ""}
      </p>

      <Card>
        <JudulBagian ikon={Trophy}>Paper paling berpengaruh di hasil ini</JudulBagian>
        <div className="space-y-2">
          {data.teratas.map((n, i) => (
            <div key={n.id} className="flex items-start gap-3 text-[13px]">
              <span className="w-6 h-6 shrink-0 rounded-md bg-panel2 text-[11px] font-bold grid place-items-center text-abu">
                {i + 1}
              </span>
              <div className="flex-1">
                <div className="text-teks leading-snug">{n.label}</div>
                <div className="text-[11.5px] text-abu">
                  {n.tahun || "—"} · dikutip {n.sitasi}× · {n.kategori || "-"}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

const PRESET = [
  { id: "openai", label: "OpenAI", base: "https://api.openai.com/v1", model: "gpt-4o-mini" },
  { id: "deepseek", label: "DeepSeek", base: "https://api.deepseek.com/v1", model: "deepseek-chat" },
  { id: "gemini", label: "Google Gemini", base: "https://generativelanguage.googleapis.com/v1beta/openai", model: "gemini-2.0-flash" },
  { id: "openrouter", label: "OpenRouter", base: "https://openrouter.ai/api/v1", model: "" },
];

const TUGAS = [
  ["sintesis", "Sintesis per tema"],
  ["bandingkan", "Tabel perbandingan"],
  ["rumusan", "Rumusan masalah & gap"],
];

function Asisten({ src }) {
  const [penyedia, setPenyedia] = useState(() => localStorage.getItem("referensia-ai-penyedia") || "openai");
  const preset = PRESET.find((p) => p.id === penyedia) || PRESET[0];
  const [base, setBase] = useState(() => localStorage.getItem("referensia-ai-base") || PRESET[0].base);
  const [model, setModel] = useState(() => localStorage.getItem("referensia-ai-model") || PRESET[0].model);
  const [key, setKey] = useState(() => localStorage.getItem("referensia-ai-key") || "");
  const [tugas, setTugas] = useState("sintesis");
  const [instruksi, setInstruksi] = useState("");
  const [sibuk, setSibuk] = useState(false);
  const [teks, setTeks] = useState("");
  const [err, setErr] = useState("");

  function gantiPenyedia(id) {
    const p = PRESET.find((x) => x.id === id) || PRESET[0];
    setPenyedia(id);
    setBase(p.base);
    setModel(p.model);
  }

  async function jalankan() {
    setErr("");
    setTeks("");
    setSibuk(true);
    try {
      const d = await asistenAI({ src, key: key.trim(), base_url: base.trim(), model: model.trim(), tugas, instruksi });
      setTeks(d.teks || "");
      localStorage.setItem("referensia-ai-penyedia", penyedia);
      localStorage.setItem("referensia-ai-base", base.trim());
      localStorage.setItem("referensia-ai-model", model.trim());
      localStorage.setItem("referensia-ai-key", key.trim());
    } catch (e) {
      setErr(e.message);
    } finally {
      setSibuk(false);
    }
  }

  function unduh() {
    const blob = new Blob([teks], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "Referensia_sintesis_AI.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      <Card>
        <JudulBagian ikon={Sparkles}>Asisten AI (pakai API key sendiri)</JudulBagian>
        <p className="text-[12.5px] text-abu mb-4 leading-relaxed">
          AI hanya membaca judul, abstrak, metode, dan hasil utama dari referensi di hasil ini. Key
          disimpan di perangkat ini dan dikirim langsung ke penyedia yang kamu pilih — bukan ke server
          Referensia. Biaya pemakaian ditanggung akun penyedianya.
        </p>
        <div className="grid md:grid-cols-2 gap-3">
          <Field label="Penyedia">
            <select className={inputCls} value={penyedia} onChange={(e) => gantiPenyedia(e.target.value)}>
              {PRESET.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </Field>
          <Field label="Model (bisa diganti)">
            <input className={inputCls} value={model} onChange={(e) => setModel(e.target.value)} placeholder="nama model" />
          </Field>
          <Field label="Base URL API" hint="Harus https:// dan kompatibel dengan /chat/completions.">
            <input className={inputCls} value={base} onChange={(e) => setBase(e.target.value)} placeholder={preset.base} />
          </Field>
          <Field label="API key">
            <input type="password" className={inputCls} value={key} onChange={(e) => setKey(e.target.value)} placeholder="sk-…" />
          </Field>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {TUGAS.map(([id, label]) => (
            <button
              key={id}
              onClick={() => setTugas(id)}
              className={`rounded-full px-3.5 py-1.5 text-[12.5px] font-bold border transition-colors ${
                tugas === id ? "border-indigo text-indigo bg-indigo/10" : "border-line text-abu hover:text-teks"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="mt-3">
          <Field label="Instruksi tambahan (opsional)">
            <textarea
              rows={2} className={inputCls} value={instruksi}
              onChange={(e) => setInstruksi(e.target.value)}
              placeholder="Contoh: fokus pada metode kuantitatif dan konteks sekolah menengah."
            />
          </Field>
        </div>
        <div className="flex items-center gap-3 mt-3 flex-wrap">
          <button
            onClick={jalankan}
            disabled={sibuk || !key.trim() || !model.trim() || !base.trim()}
            className="gradient-btn rounded-xl px-5 py-2.5 text-[13px] font-bold text-white disabled:opacity-50"
          >
            {sibuk ? "Menyusun…" : "Jalankan AI"}
          </button>
          <span className="text-[11.5px] text-abu">Biasanya 10–40 detik tergantung penyedia.</span>
        </div>
        {err && (
          <div className="flex items-start gap-1.5 mt-3 text-[13px] text-amber">
            <Ikon as={TriangleAlert} size={15} className="mt-0.5" />
            {err}
          </div>
        )}
      </Card>

      {teks && (
        <Card>
          <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
            <SectionTitle color="text-indigo">Hasil</SectionTitle>
            <div className="flex items-center gap-2">
              <SalinBtn teks={teks}>hasil AI</SalinBtn>
              <button onClick={unduh} className="inline-flex items-center gap-1.5 rounded-xl border border-line px-3 py-1.5 text-[12px] font-bold text-abu hover:text-teks">
                <Ikon as={Download} size={13} />
                .md
              </button>
            </div>
          </div>
          <div className="whitespace-pre-wrap text-[13px] leading-relaxed text-teks">{teks}</div>
          <p className="text-[11.5px] text-abu mt-4 border-t border-line/60 pt-3">
            Periksa kembali kutipan dan klaim AI sebelum dimasukkan ke skripsi — AI bisa keliru.
          </p>
        </Card>
      )}
    </div>
  );
}
