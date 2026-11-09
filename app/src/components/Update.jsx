import { useState } from "react";
import { motion } from "framer-motion";
import { Card, Label, Toggle, SalinBtn } from "./ui.jsx";
import { unduhPembaruan, pasangPembaruan } from "../api.js";

const MB = (n) => (n > 0 ? `${(n / 1048576).toFixed(1)} MB` : "-");

function Gaya({ children }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 backdrop-blur-sm px-5 py-8 overflow-y-auto">
      <motion.div
        initial={{ opacity: 0, y: 18, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 10, scale: 0.98 }}
        transition={{ type: "spring", stiffness: 320, damping: 26 }}
        className="w-full max-w-xl"
      >
        {children}
      </motion.div>
    </div>
  );
}

/** Tanya sekali saja saat pengguna pertama kali membuka aplikasi. */
export function KonsenPembaruan({ onPilih }) {
  return (
    <Gaya>
      <Card className="p-6">
        <Label>Baru pertama kali membuka Referensia</Label>
        <h2 className="font-display text-[21px] font-bold mt-1.5">Aktifkan pembaruan otomatis?</h2>
        <p className="text-[13px] text-abu leading-relaxed mt-3">
          Kalau aktif, Referensia menghubungi <b>api.github.com</b> sekali setiap aplikasi dibuka hanya
          untuk menanyakan versi rilis terakhir. Tidak ada data pencarian, nama, atau token yang ikut
          terkirim. Saat ada versi baru, kamu tetap{" "}
          <b>ditanya dulu</b> — tidak ada yang dipasang diam-diam.
        </p>
        <p className="text-[13px] text-abu leading-relaxed mt-2.5">
          Menonaktifkannya pun aman: semua fitur pencarian tetap jalan, hanya saja kamu harus{" "}
          <a
            href="https://github.com/iqbalhikam/Referensia/releases"
            target="_blank"
            rel="noreferrer"
            className="text-indigo hover:underline"
          >
            mengunduh installer
          </a>{" "}
          sendiri ketika butuh versi baru.
        </p>
        <div className="grid sm:grid-cols-2 gap-2.5 mt-6">
          <button
            onClick={() => onPilih(true)}
            className="gradient-btn rounded-xl py-3 text-[14px] font-semibold text-white"
          >
            ✓ Aktifkan pembaruan otomatis
          </button>
          <button
            onClick={() => onPilih(false)}
            className="rounded-xl py-3 text-[14px] font-semibold border border-line text-abu hover:text-teks hover:border-indigo transition-colors"
          >
            Nonaktifkan saja
          </button>
        </div>
        <div className="text-[11.5px] text-abu/80 mt-3.5">Pilihan ini bisa diubah kapan saja lewat ⚙️ di kanan atas.</div>
      </Card>
    </Gaya>
  );
}

/** Unduh penginstal lalu jadwalkan pemasangan setelah aplikasi ditutup. */
export function PanelRilis({ data }) {
  const [status, setStatus] = useState("siap");
  const [berkas, setBerkas] = useState(null);
  const [galat, setGalat] = useState("");
  const r = data?.rilis || {};
  const aset = (r.aset || [])[0];

  async function unduh() {
    setGalat("");
    setStatus("mengunduh");
    try {
      const d = await unduhPembaruan(aset.unduh);
      setBerkas(d);
      setStatus("terunduh");
    } catch (e) {
      setGalat(e.message);
      setStatus("galat");
    }
  }

  async function pasang() {
    setGalat("");
    setStatus("memasang");
    try {
      await pasangPembaruan(berkas.lokasi);
      setStatus("dijadwalkan");
    } catch (e) {
      setGalat(e.message);
      setStatus("galat");
    }
  }

  return (
    <div className="mt-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px]">
        <span className="font-bold text-teks">{r.judul || `Rilis ${r.versi}`}</span>
        {r.terbit && <span className="text-abu">terbit {r.terbit}</span>}
        {aset && <span className="text-abu">penginstal {MB(aset.ukuran)}</span>}
      </div>

      {r.catatan && (
        <div className="mt-2.5 max-h-40 overflow-y-auto rounded-xl border border-line/60 bg-bg/50 px-3.5 py-2.5 text-[12.5px] leading-relaxed whitespace-pre-wrap text-teks/85">
          {r.catatan}
        </div>
      )}

      {status === "dijadwalkan" ? (
        <div className="mt-3 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-3.5 py-3 text-[13px] text-emerald-400">
          ✓ Penginstal siap. <b>Tutup jendela Referensia</b> sekarang — pemasangan berjalan otomatis beberapa
          detik kemudian.
        </div>
      ) : (
        <div className="flex flex-wrap gap-2 mt-3.5">
          {status !== "terunduh" && (
            <button
              onClick={unduh}
              disabled={!aset || status === "mengunduh"}
              className="gradient-btn rounded-xl px-4 py-2.5 text-[13px] font-semibold text-white disabled:opacity-60"
            >
              {status === "mengunduh" ? "Mengunduh…" : `⬇️ Unduh penginstal${aset ? ` (${MB(aset.ukuran)})` : ""}`}
            </button>
          )}
          {status === "terunduh" && berkas && (
            <button
              onClick={pasang}
              className="gradient-btn rounded-xl px-4 py-2.5 text-[13px] font-semibold text-white"
            >
              ▶ Pasang & tutup Referensia
            </button>
          )}
          {r.laman && (
            <a
              href={r.laman}
              target="_blank"
              rel="noreferrer"
              className="rounded-xl px-4 py-2.5 text-[13px] font-semibold border border-line text-abu hover:text-teks hover:border-indigo transition-colors"
            >
              Halaman rilis
            </a>
          )}
          {r.laman && <SalinBtn teks={r.laman}>tautan</SalinBtn>}
        </div>
      )}

      {status === "terunduh" && berkas && (
        <div className="text-[12px] text-abu mt-2.5 break-all">
          Tersimpan di <span className="text-teks/90">{berkas.lokasi}</span>
        </div>
      )}
      {!aset && <div className="text-[12px] text-amber-400 mt-2.5">Rilis ini belum punya penginstal .exe.</div>}
      {galat && <div className="text-[12px] text-amber-400 mt-2.5">⚠️ {galat}</div>}
      <div className="text-[11.5px] text-abu/80 mt-2.5">
        Berkas hanya diambil dari host GitHub dan disimpan di folder Referensia di Documents.
      </div>
    </div>
  );
}

/** Spanduk di bawah header saat versi baru tersedia. */
export function SpandukPembaruan({ data, onNanti, onPengaturan }) {
  const [buka, setBuka] = useState(false);
  const r = data?.rilis || {};
  return (
    <div className="sticky top-14 z-30 bg-indigodeep/20 border-b border-indigo/40 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-5 py-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[13px]">
        <span className="text-teks font-semibold">
          ⬆️ Referensia {r.versi} tersedia — kamu masih di {data.versi_sekarang}
        </span>
        <button onClick={() => setBuka((v) => !v)} className="text-indigo hover:underline font-medium">
          {buka ? "Sembunyikan" : "Lihat & unduh"}
        </button>
        <button onClick={onNanti} className="text-abu hover:text-teks">
          Nanti dulu
        </button>
        <button onClick={onPengaturan} className="ml-auto text-abu hover:text-teks">
          Pengaturan ⚙️
        </button>
        {buka && (
          <div className="w-full pb-1">
            <PanelRilis data={data} />
          </div>
        )}
      </div>
    </div>
  );
}

/** Isi modal ⚙️ Pengaturan. */
export function PengaturanPembaruan({ auto, onAuto, data, galat, sibuk, onPeriksa, onClose }) {
  return (
    <Gaya>
      <Card className="p-6">
        <div className="flex items-start">
          <div>
            <Label>Pengaturan</Label>
            <h2 className="font-display text-[19px] font-bold mt-1">Pembaruan aplikasi</h2>
          </div>
          <button onClick={onClose} className="ml-auto text-abu hover:text-teks text-lg leading-none px-1.5">
            ✕
          </button>
        </div>

        <div className="mt-4 rounded-xl border border-line/60 bg-bg/50 px-3.5 py-2.5 text-[13px] flex flex-wrap gap-x-6 gap-y-1">
          <span className="text-abu">
            Versi terpasang <b className="text-teks">{data?.versi_sekarang || "-"}</b>
          </span>
          <span className="text-abu">
            Rilis terbaru <b className="text-teks">{data?.rilis?.versi || "belum diperiksa"}</b>
          </span>
        </div>

        <div className="mt-4">
          <Toggle
            label="Periksa pembaruan otomatis"
            hint="Sekali tiap kali aplikasi dibuka, lewat api.github.com. Bisa dimatikan kapan saja."
            checked={auto === true}
            onChange={onAuto}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 mt-3">
          <button
            onClick={onPeriksa}
            disabled={sibuk}
            className="rounded-xl px-4 py-2 text-[13px] font-semibold border border-line text-teks hover:border-indigo transition-colors disabled:opacity-60"
          >
            {sibuk ? "Memeriksa…" : "🔄 Periksa sekarang"}
          </button>
          <span className="text-[12px] text-abu">
            {auto === false ? "Pemeriksaan otomatis nonaktif — periksa manual bila perlu." : ""}
          </span>
        </div>

        {galat && <div className="text-[12.5px] text-amber-400 mt-3">⚠️ {galat}</div>}

        {data?.ada_baru ? (
          <div className="mt-4 rounded-2xl border border-indigo/40 bg-indigodeep/15 p-4">
            <div className="text-[14px] font-bold text-teks">Ada versi baru: {data.rilis.versi}</div>
            <PanelRilis data={data} />
          </div>
        ) : (
          data && !galat && (
            <div className="mt-4 text-[13px] text-emerald-400">✓ Sudah versi terbaru.</div>
          )
        )}
      </Card>
    </Gaya>
  );
}
