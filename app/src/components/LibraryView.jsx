import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Card, Label, SalinBtn } from "./ui.jsx";
import { Ikon, ArrowLeft, ArrowRight, FileArchive, FolderOpen, Star, StickyNote, Trash2 } from "./icons.jsx";
import { library, hapusLibrary, libraryDownloadUrl, favorites } from "../api.js";

function tanggalCantik(iso) {
  try {
    return new Date(iso).toLocaleString("id-ID", {
      day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function LibraryView({ onOpen, onBack }) {
  const [tab, setTab] = useState("riwayat");
  const [entries, setEntries] = useState(null);
  const [favGroups, setFavGroups] = useState(null);
  const [error, setError] = useState("");

  async function muat() {
    try {
      const [lib, fav] = await Promise.all([library(), favorites()]);
      setEntries(lib);
      setFavGroups(fav);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => { muat(); }, []);

  async function hapus(id) {
    if (!window.confirm("Hapus entri ini dari pustaka? File ZIP/PDF di disk tidak ikut terhapus.")) return;
    try {
      await hapusLibrary(id);
      muat();
    } catch (e) {
      setError(e.message);
    }
  }

  const kosong = entries && entries.length === 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -14 }}
      transition={{ duration: 0.35 }}
      className="max-w-5xl mx-auto px-5 py-10"
    >
      <div className="flex items-end justify-between flex-wrap gap-4 mb-6">
        <div>
          <Label>Pustaka lokal</Label>
          <h1 className="font-display text-3xl font-semibold mt-2">Riwayat & Favorit</h1>
          <p className="text-sm text-abu mt-2">
            Setiap pencarian yang selesai tersimpan otomatis di sini (maks. 100) — buka lagi kapan saja
            tanpa mencari ulang.
          </p>
        </div>
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 font-bold border border-line text-abu hover:text-teks hover:border-indigo transition-colors"
        >
          <Ikon as={ArrowLeft} size={15} />
          Kembali
        </button>
      </div>

      <div className="inline-flex rounded-xl bg-bg/60 border border-line/60 p-1 mb-6">
        {[["riwayat", `Riwayat${entries ? ` (${entries.length})` : ""}`],
          ["favorit", `Favorit${favGroups ? ` (${favGroups.reduce((a, g) => a + g.refs.length, 0)})` : ""}`]].map(([val, label]) => (
          <button
            key={val}
            type="button"
            onClick={() => setTab(val)}
            className={`px-5 py-2 text-[13px] font-medium rounded-lg transition-colors ${
              tab === val ? "bg-indigodeep/25 border border-indigo/40 text-teks" : "text-abu hover:text-teks/80"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {error && (
        <div className="border border-red-500/40 bg-red-500/10 text-red-400 rounded-xl px-4 py-3 text-sm mb-4">
          {error}
        </div>
      )}

      {!entries && !error && <p className="text-abu text-sm">Memuat pustaka…</p>}

      {tab === "riwayat" && kosong && (
        <Card className="text-center py-12">
          <Ikon as={FolderOpen} size={38} className="text-abu/60 mb-3" strokeWidth={1.5} />
          <div className="font-bold text-lg">Pustaka masih kosong</div>
          <p className="text-sm text-abu mt-2">Mulai satu pencarian — hasilnya akan otomatis tersimpan di sini.</p>
        </Card>
      )}

      {tab === "riwayat" && entries?.map((e) => (
        <Card key={e.id} className="mb-3">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="min-w-0 flex-1">
              <div className="text-[12px] text-abu">{tanggalCantik(e.tanggal)}</div>
              <div className="font-bold text-[15px] leading-snug mt-1">{e.topik}</div>
              <div className="text-[12.5px] text-abu mt-1.5">
                {e.total} referensi · {e.jumlah_pdf} PDF
                {e.n_favorit > 0 && (
                  <span className="text-amber inline-flex items-center gap-1 ml-1">
                    ·<Ikon as={Star} size={12} className="fill-current" />{e.n_favorit} favorit
                  </span>
                )}
                {!e.zip_ada && <span className="text-amber-400"> · ZIP tidak ada di disk</span>}
              </div>
            </div>
            <div className="flex gap-2 shrink-0">
              <button
                onClick={() => onOpen(e.id)}
                className="rounded-xl px-4 py-2 text-[13px] font-bold gradient-btn text-white"
              >
                Buka hasil
              </button>
              {e.zip_ada && (
                <a
                  href={libraryDownloadUrl(e.id)}
                  className="inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-[13px] font-bold border border-line text-abu hover:text-teks hover:border-indigo/60 transition-colors"
                >
                  <Ikon as={FileArchive} size={14} />
                  ZIP
                </a>
              )}
              <button
                onClick={() => hapus(e.id)}
                className="rounded-xl px-3 py-2 text-[13px] font-bold border border-line text-abu hover:text-red-400 hover:border-red-500/50 transition-colors"
                title="Hapus dari pustaka"
              >
                <Ikon as={Trash2} size={15} />
              </button>
            </div>
          </div>
        </Card>
      ))}

      {tab === "favorit" && favGroups && favGroups.length === 0 && (
        <Card className="text-center py-12">
          <Ikon as={Star} size={38} className="text-abu/60 mb-3" strokeWidth={1.5} />
          <div className="font-bold text-lg">Belum ada favorit</div>
          <p className="text-sm text-abu mt-2">
            Di halaman hasil, klik ikon bintang pada baris referensi untuk menandainya. Favorit terkumpul di sini.
          </p>
        </Card>
      )}

      {tab === "favorit" && favGroups?.map((g) => (
        <Card key={g.lib_id} className="mb-4">
          <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
            <div>
              <div className="font-bold text-[14px]">{g.topik}</div>
              <div className="text-[12px] text-abu">{tanggalCantik(g.tanggal)} · {g.refs.length} favorit</div>
            </div>
            <button
              onClick={() => onOpen(g.lib_id)}
              className="inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-[12.5px] font-bold border border-line text-abu hover:text-teks hover:border-indigo/60 transition-colors"
            >
              Buka hasil lengkap
              <Ikon as={ArrowRight} size={13} />
            </button>
          </div>
          <div className="space-y-3">
            {g.refs.map((r) => (
              <div key={r.uid} className="border-t border-line/60 pt-3">
                <div className="text-[13px] font-semibold leading-snug">
                  <Ikon as={Star} size={13} className="fill-current text-amber mr-1.5" />{r.judul}
                  <span className="text-abu font-normal"> ({r.tahun || "-"})</span>
                </div>
                {r.catatan_pribadi && (
                  <div className="flex items-start gap-1.5 text-[12px] text-abu mt-1">
                    <Ikon as={StickyNote} size={13} className="mt-0.5" />
                    {r.catatan_pribadi}
                  </div>
                )}
                {r.apa && (
                  <div className="flex items-start gap-2 mt-1.5">
                    <span className="text-abu text-[12px] flex-1">{r.apa}</span>
                    <SalinBtn teks={r.apa}>APA</SalinBtn>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      ))}
    </motion.div>
  );
}