import { LectureStatus } from "@/lib/types";

const styles: Record<LectureStatus, string> = {
  queued: "bg-slate-100 text-slate-700 ring-slate-200",
  transcribing: "bg-amber-100 text-amber-800 ring-amber-200",
  processing: "bg-orange-100 text-orange-800 ring-orange-200",
  indexing: "bg-lime-100 text-lime-800 ring-lime-200",
  done: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  failed: "bg-rose-100 text-rose-800 ring-rose-200",
};

const dotStyles: Record<LectureStatus, string> = {
  queued: "bg-slate-400",
  transcribing: "bg-amber-500",
  processing: "bg-orange-500",
  indexing: "bg-lime-500",
  done: "bg-emerald-500",
  failed: "bg-rose-500",
};

const ACTIVE: LectureStatus[] = ["queued", "transcribing", "processing", "indexing"];

export function StatusBadge({ status }: { status: LectureStatus }) {
  const active = ACTIVE.includes(status);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${styles[status]}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dotStyles[status]} ${active ? "animate-pulse" : ""}`} />
      {status}
    </span>
  );
}
