import {
  AlertTriangle, ArrowLeft, ArrowRight, ArrowUpFromLine, BookMarked, BookOpen,
  BrainCircuit, Calculator, Check, CheckCircle2, ChevronDown, ChevronRight, Compass,
  Copy, Download, Droplets, FileArchive, FileCode2, FileSpreadsheet, FileText, Flag,
  FlaskConical, FolderOpen, Globe2, KeyRound, Library, Link2, Loader2, Minus, Moon,
  Network, NotebookPen, Play, Plus, Puzzle, RefreshCw, RotateCcw, Search, SearchX, Settings,
  Sparkles, Star, StickyNote, Sun, Trash2, TrendingUp, TriangleAlert, Trophy, Upload, X, Zap,
} from "lucide-react";

export {
  AlertTriangle, ArrowLeft, ArrowRight, ArrowUpFromLine, BookMarked, BookOpen,
  BrainCircuit, Calculator, Check, CheckCircle2, ChevronDown, ChevronRight, Compass,
  Copy, Download, Droplets, FileArchive, FileCode2, FileSpreadsheet, FileText, Flag,
  FlaskConical, FolderOpen, Globe2, KeyRound, Library, Link2, Loader2, Minus, Moon,
  Network, NotebookPen, Play, Plus, Puzzle, RefreshCw, RotateCcw, Search, SearchX, Settings,
  Sparkles, Star, StickyNote, Sun, Trash2, TrendingUp, TriangleAlert, Trophy, Upload, X, Zap,
};

/** Ikon garis seragam 24px yang sejajar dengan teks di sekitarnya. */
export function Ikon({ as: IkonAs, size = 16, strokeWidth = 2, className = "", ...sisa }) {
  return (
    <IkonAs
      size={size}
      strokeWidth={strokeWidth}
      aria-hidden="true"
      className={`inline-block shrink-0 align-[-0.125em] ${className}`}
      {...sisa}
    />
  );
}
