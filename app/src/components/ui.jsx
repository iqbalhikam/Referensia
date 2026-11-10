import { useState } from "react";
import { motion } from "framer-motion";
import { Ikon, Check, Copy } from "./icons.jsx";

export function salinTeks(t) {
  if (navigator.clipboard?.writeText) return navigator.clipboard.writeText(t);
  const ta = document.createElement("textarea");
  ta.value = t;
  document.body.appendChild(ta);
  ta.select();
  document.execCommand("copy");
  ta.remove();
  return Promise.resolve();
}

export function SalinBtn({ teks, children }) {
  const [ok, setOk] = useState(false);
  return (
    <button
      type="button"
      onClick={() => salinTeks(teks).then(() => { setOk(true); setTimeout(() => setOk(false), 1500); })}
      className="inline-flex items-center gap-1.5 shrink-0 text-[11px] font-bold border border-line rounded-lg px-2.5 py-1 text-abu hover:text-indigo hover:border-indigo/50 transition-colors"
    >
      <Ikon as={ok ? Check : Copy} size={12} />
      {ok ? "tersalin" : `Salin ${children}`}
    </button>
  );
}

export function Card({ children, className = "" }) {
  return (
    <div
      className={`rf-card rounded-2xl border border-line/60 bg-panel/70 backdrop-blur-sm p-5 shadow-[0_12px_40px_-12px_rgba(0,0,0,0.5)] ${className}`}
    >
      {children}
    </div>
  );
}

export function Label({ children, className = "" }) {
  return (
    <div className={`text-[11px] font-semibold uppercase tracking-[0.16em] text-abu ${className}`}>
      {children}
    </div>
  );
}

export function SectionTitle({ children, color = "text-indigo" }) {
  return <div className={`text-[15px] font-extrabold mb-3 ${color}`}>{children}</div>;
}

export function Chip({ children }) {
  return (
    <span className="inline-block bg-panel2/80 border border-line/60 rounded-full px-3 py-1 m-0.5 text-[12px] text-teks/90">
      {children}
    </span>
  );
}

export function Toggle({ label, hint, checked, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex items-start gap-3 w-full text-left py-2.5 group"
    >
      <span
        className={`mt-0.5 w-9 h-5 shrink-0 rounded-full p-0.5 transition-colors ${
          checked ? "bg-indigodeep" : "bg-line"
        }`}
      >
        <motion.span
          layout
          transition={{ type: "spring", stiffness: 500, damping: 32 }}
          className={`block w-4 h-4 rounded-full bg-white shadow ${checked ? "ml-auto" : ""}`}
        />
      </span>
      <span>
        <span className="block text-sm font-medium text-teks/90 group-hover:text-indigo">{label}</span>
        {hint && <span className="block text-[12px] text-abu leading-snug mt-0.5">{hint}</span>}
      </span>
    </button>
  );
}

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="block text-[13px] font-medium text-teks/80 mb-1.5">{label}</span>
      {children}
      {hint && <span className="block text-[12px] text-abu mt-1.5">{hint}</span>}
    </label>
  );
}

export const inputCls =
  "w-full bg-bg/60 border border-line rounded-xl px-3.5 py-2.5 text-sm text-teks placeholder:text-abu/50 outline-none focus:border-indigo/60 focus:ring-2 focus:ring-indigo/20 transition-all";

export function ScoreBadge({ skor }) {
  const [teks, cls] =
    skor >= 65
      ? ["Sangat relevan", "bg-indigo/15 text-indigo border-indigo/40"]
      : skor >= 45
        ? ["Relevan", "bg-emerald-500/15 text-emerald-400 border-emerald-500/40"]
        : ["Pendukung", "bg-amber-500/15 text-amber-400 border-amber-500/40"];
  return (
    <span className={`inline-flex items-center gap-1.5 border rounded-full px-2.5 py-0.5 text-[12px] font-bold whitespace-nowrap ${cls}`}>
      {skor} · {teks}
    </span>
  );
}

export function IconSearch({ className = "w-4 h-4" }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" className={className}>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.8-3.8" />
    </svg>
  );
}

export function IconCheck({ className = "w-4 h-4" }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="m5 12.5 4.5 4.5L19 7.5" />
    </svg>
  );
}

export function IconArrow({ className = "w-4 h-4" }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M4 12h15" />
      <path d="m13 6 6 6-6 6" />
    </svg>
  );
}