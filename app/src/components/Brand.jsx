import { useEffect, useRef } from "react";
import { health } from "../api.js";

export function LogoMark({ className = "w-10 h-10" }) {
  return (
    <svg viewBox="0 0 120 120" className={className} aria-hidden="true">
      <rect width="120" height="120" rx="28" fill="#4F46E5" />
      <path d="M30 22H68Q74 22 74 28V80L49 65L24 80V28Q24 22 30 22Z" fill="#fff" />
      <rect x="34" y="36" width="30" height="5" rx="2.5" fill="#C7D2FE" />
      <rect x="34" y="48" width="20" height="5" rx="2.5" fill="#C7D2FE" />
      <circle cx="80" cy="74" r="21" fill="#4F46E5" stroke="#FBBF24" strokeWidth="7" />
      <line x1="95" y1="89" x2="108" y2="102" stroke="#FBBF24" strokeWidth="9" strokeLinecap="round" />
      <circle cx="80" cy="74" r="5" fill="#fff" />
    </svg>
  );
}

export function Welcome({ onDone }) {
  const ref = useRef(null);
  useEffect(() => {
    const shownAt = performance.now();
    let batal = false;
    health()
      .catch(() => {})
      .then(() => {
        const tunggu = Math.max(0, 3000 - (performance.now() - shownAt));
        setTimeout(() => {
          if (batal) return;
          ref.current?.classList.add("rf-out");
          setTimeout(() => {
            if (!batal) onDone();
          }, 500);
        }, tunggu);
      });
    return () => {
      batal = true;
    };
  }, [onDone]);

  return (
    <div id="rf-welcome" ref={ref} role="status" aria-label="Selamat datang di Referensia">
      <div className="rf-stage">
        <svg className="rf-logo" viewBox="0 0 120 120" aria-hidden="true">
          <rect className="rf-tile" width="120" height="120" rx="28" fill="#4F46E5" />
          <path className="rf-mark" d="M30 22H68Q74 22 74 28V80L49 65L24 80V28Q24 22 30 22Z" fill="#FFFFFF" />
          <rect className="rf-line a" x="34" y="36" width="30" height="5" rx="2.5" fill="#C7D2FE" />
          <rect className="rf-line b" x="34" y="48" width="20" height="5" rx="2.5" fill="#C7D2FE" />
          <g className="rf-lens">
            <circle cx="80" cy="74" r="21" fill="#4F46E5" stroke="#FBBF24" strokeWidth="7" />
            <line x1="95" y1="89" x2="108" y2="102" stroke="#FBBF24" strokeWidth="9" strokeLinecap="round" />
            <circle cx="80" cy="74" r="5" fill="#FFFFFF" />
          </g>
        </svg>
        <h1 className="rf-word">Referensia</h1>
        <p className="rf-tag">Cari referensi dengan mudah</p>
      </div>
    </div>
  );
}

export function LoadingAnim({ size = 120, label }) {
  return (
    <div className="rfl" role="status" aria-label={label || "Memuat"}>
      <svg viewBox="0 0 180 180" style={{ width: size, height: size }} aria-hidden="true">
        <rect className="ripple" x="40" y="40" width="100" height="100" rx="26" />
        <rect className="ripple r2" x="40" y="40" width="100" height="100" rx="26" />
        <circle cx="90" cy="90" r="72" fill="none" stroke="#4F46E5" strokeOpacity=".12" strokeWidth="2" />
        <rect className="tile" x="40" y="40" width="100" height="100" rx="26" fill="#4F46E5" />
        <g transform="translate(40 40) scale(.8333)">
          <path d="M30 22H68Q74 22 74 28V80L49 65L24 80V28Q24 22 30 22Z" fill="#fff" />
          <rect className="ln a" x="34" y="36" width="30" height="5" rx="2.5" />
          <rect className="ln b" x="34" y="48" width="20" height="5" rx="2.5" />
        </g>
        <g className="orbit">
          <circle cx="90" cy="90" r="72" fill="none" stroke="#FBBF24" strokeWidth="4" strokeLinecap="round" strokeDasharray="120 400" transform="rotate(174.5 90 90)" opacity=".25" />
          <circle cx="90" cy="90" r="72" fill="none" stroke="#FBBF24" strokeWidth="4" strokeLinecap="round" strokeDasharray="80 400" transform="rotate(206.3 90 90)" opacity=".5" />
          <circle cx="90" cy="90" r="72" fill="none" stroke="#FBBF24" strokeWidth="4" strokeLinecap="round" strokeDasharray="40 400" transform="rotate(238.2 90 90)" opacity=".9" />
          <line x1="82" y1="26" x2="73" y2="35" stroke="#FBBF24" strokeWidth="6" strokeLinecap="round" />
          <circle cx="90" cy="18" r="11" fill="#4F46E5" stroke="#FBBF24" strokeWidth="5" />
          <circle cx="90" cy="18" r="3" fill="#fff" />
        </g>
      </svg>
      {label && <p className="rfl-label">{label}</p>}
    </div>
  );
}