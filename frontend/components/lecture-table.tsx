"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState, useTransition } from "react";

import { deleteLecture, fetchLectures, retryLecture } from "@/lib/api";
import { formatDuration, formatTimestamp } from "@/lib/format";
import { LectureListItem, LectureStatus } from "@/lib/types";

import { StatusBadge } from "./status-badge";

const ACTIVE_STATUSES: LectureStatus[] = ["queued", "transcribing", "processing", "indexing"];

export function LectureTable({ lectures: initialLectures }: { lectures: LectureListItem[] }) {
  const [lectures, setLectures] = useState<LectureListItem[]>(initialLectures);
  const [isPending, startTransition] = useTransition();
  const [lastSynced, setLastSynced] = useState<Date | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const anyActive = lectures.some((lecture) => ACTIVE_STATUSES.includes(lecture.status));

  const refresh = useCallback(async () => {
    try {
      const next = await fetchLectures();
      setLectures(next);
      setLastSynced(new Date());
    } catch {
      // keep showing the last good snapshot on transient errors
    }
  }, []);

  // Live polling: only while something is processing, so the dashboard stays fresh
  // without the user having to refresh — and stops once everything settles.
  useEffect(() => {
    if (!anyActive) {
      if (timer.current) clearInterval(timer.current);
      return;
    }
    timer.current = setInterval(refresh, 3000);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [anyActive, refresh]);

  function handleRetry(id: number) {
    startTransition(async () => {
      await retryLecture(id);
      await refresh();
    });
  }

  function handleDelete(id: number) {
    startTransition(async () => {
      await deleteLecture(id);
      await refresh();
    });
  }

  if (!lectures.length) {
    return (
      <section className="rounded-2xl border border-white/60 bg-white/70 p-8 text-center text-sm text-slate-600 shadow-sm backdrop-blur">
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-orange-100 to-lime-100 text-xl">
          🎧
        </div>
        No lectures yet. Upload audio to start generating notes, quizzes, and chat context.
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-white/60 bg-white/75 shadow-sm backdrop-blur">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200/70 px-5 py-3">
        <h2 className="text-sm font-semibold text-slate-800">Your lectures</h2>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          {anyActive ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 font-medium text-amber-700">
              <span className="h-1.5 w-1.5 animate-ping rounded-full bg-amber-500" />
              Live · processing
            </span>
          ) : (
            <span className="rounded-full bg-emerald-50 px-2.5 py-1 font-medium text-emerald-700">All up to date</span>
          )}
          {lastSynced ? <span>synced {formatTimestamp(lastSynced.toISOString())}</span> : null}
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50/80">
            <tr className="text-left text-slate-600">
              <th className="px-5 py-3 font-medium">Lecture</th>
              <th className="px-5 py-3 font-medium">Subject / Chapter</th>
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3 font-medium">Words</th>
              <th className="px-5 py-3 font-medium">Length</th>
              <th className="px-5 py-3 font-medium">Updated</th>
              <th className="px-5 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {lectures.map((lecture) => (
              <tr key={lecture.id} className="transition hover:bg-orange-50/30">
                <td className="px-5 py-4">
                  <div className="flex items-center gap-1.5 font-medium text-slate-800">
                    <span title={lecture.source_type === "youtube" ? "From YouTube" : "Uploaded file"}>
                      {lecture.source_type === "youtube" ? "▶️" : "🎧"}
                    </span>
                    {lecture.title}
                  </div>
                  <div className="text-xs text-slate-500">{lecture.original_filename}</div>
                </td>
                <td className="px-5 py-4">
                  {lecture.subject_name ? (
                    <div className="flex flex-col gap-1">
                      <span className="inline-flex w-fit items-center rounded-full bg-lime-100 px-2.5 py-0.5 text-xs font-medium text-lime-800">
                        {lecture.subject_name}
                      </span>
                      {lecture.chapter_name ? <span className="text-xs text-slate-600">{lecture.chapter_name}</span> : null}
                      {lecture.subsection ? <span className="text-xs text-slate-400">{lecture.subsection}</span> : null}
                    </div>
                  ) : (
                    <span className="text-xs text-slate-400">—</span>
                  )}
                </td>
                <td className="px-5 py-4">
                  <StatusBadge status={lecture.status} />
                  {lecture.error_message ? <div className="mt-2 max-w-xs text-xs text-rose-600">{lecture.error_message}</div> : null}
                </td>
                <td className="px-5 py-4 text-slate-600">{lecture.word_count ?? "—"}</td>
                <td className="px-5 py-4 text-slate-600">{formatDuration(lecture.duration_seconds)}</td>
                <td className="px-5 py-4 text-slate-600">{formatTimestamp(lecture.updated_at)} UTC</td>
                <td className="px-5 py-4">
                  <div className="flex flex-wrap gap-2">
                    <Link
                      className="rounded-lg border border-orange-200 bg-white px-3 py-2 font-medium text-orange-700 transition hover:bg-orange-50"
                      href={`/lectures/${lecture.id}`}
                    >
                      Open
                    </Link>
                    {lecture.status === "failed" ? (
                      <button
                        className="rounded-lg border bg-white px-3 py-2 transition hover:bg-slate-50 disabled:opacity-50"
                        disabled={isPending}
                        onClick={() => handleRetry(lecture.id)}
                      >
                        Retry
                      </button>
                    ) : null}
                    <button
                      className="rounded-lg border border-rose-200 bg-white px-3 py-2 text-rose-700 transition hover:bg-rose-50 disabled:opacity-50"
                      disabled={isPending}
                      onClick={() => handleDelete(lecture.id)}
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
