"use client";

import { useEffect, useRef, useState, useTransition } from "react";

import { fetchSubjects, ingestYoutube, uploadLecture } from "@/lib/api";
import { Subject } from "@/lib/types";

type Mode = "file" | "youtube";

export function UploadPanel() {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [mode, setMode] = useState<Mode>("file");
  const [subject, setSubject] = useState("");
  const [chapter, setChapter] = useState("");
  const [subsection, setSubsection] = useState("");
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [message, setMessage] = useState<string>("");
  const [isError, setIsError] = useState(false);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    fetchSubjects().then(setSubjects).catch(() => {});
  }, []);

  const matchedSubject = subjects.find((s) => s.name.toLowerCase() === subject.trim().toLowerCase());
  const chapterOptions = matchedSubject?.chapters ?? [];

  function meta() {
    return {
      subject: subject.trim() || undefined,
      chapter: chapter.trim() || undefined,
      subsection: subsection.trim() || undefined,
    };
  }

  function notify(text: string, error = false) {
    setMessage(text);
    setIsError(error);
  }

  function onSubmit() {
    if (mode === "file") {
      const file = inputRef.current?.files?.[0];
      if (!file) return notify("Choose an mp3, wav, or m4a file.", true);
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (!ext || !["mp3", "wav", "m4a"].includes(ext)) return notify("Unsupported file type.", true);
      startTransition(async () => {
        try {
          notify("Uploading lecture…");
          await uploadLecture(file, meta());
          notify("Upload queued — processing will begin shortly.");
          if (inputRef.current) inputRef.current.value = "";
          setTimeout(() => window.location.reload(), 700);
        } catch (e) {
          notify(e instanceof Error ? e.message : "Upload failed", true);
        }
      });
    } else {
      const url = youtubeUrl.trim();
      if (!url) return notify("Paste a YouTube link.", true);
      startTransition(async () => {
        try {
          notify("Fetching audio from YouTube…");
          await ingestYoutube(url, meta());
          notify("YouTube link queued — extracting audio, then processing.");
          setYoutubeUrl("");
          setTimeout(() => window.location.reload(), 700);
        } catch (e) {
          notify(e instanceof Error ? e.message : "YouTube ingest failed", true);
        }
      });
    }
  }

  const tabClass = (active: boolean) =>
    `rounded-lg px-4 py-2 text-sm font-medium transition ${
      active ? "bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-sm" : "border bg-white text-slate-600 hover:bg-orange-50"
    }`;

  return (
    <section className="rounded-2xl border border-white/60 bg-white/75 p-6 shadow-sm backdrop-blur">
      <div className="mb-4 flex items-center gap-2">
        <button className={tabClass(mode === "file")} onClick={() => setMode("file")}>
          🎧 Upload file
        </button>
        <button className={tabClass(mode === "youtube")} onClick={() => setMode("youtube")}>
          ▶️ YouTube link
        </button>
      </div>

      {/* Organization row */}
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Subject</label>
          <input
            list="subject-options"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="e.g. Science"
            className="w-full rounded-xl border bg-white px-3 py-2 text-sm shadow-sm focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-100"
          />
          <datalist id="subject-options">
            {subjects.map((s) => (
              <option key={s.id} value={s.name} />
            ))}
          </datalist>
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Chapter</label>
          <input
            list="chapter-options"
            value={chapter}
            onChange={(e) => setChapter(e.target.value)}
            placeholder="e.g. Quantum Mechanics"
            className="w-full rounded-xl border bg-white px-3 py-2 text-sm shadow-sm focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-100"
          />
          <datalist id="chapter-options">
            {chapterOptions.map((c) => (
              <option key={c.id} value={c.name} />
            ))}
          </datalist>
        </div>
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Subsection</label>
          <input
            value={subsection}
            onChange={(e) => setSubsection(e.target.value)}
            placeholder="e.g. Wave functions"
            className="w-full rounded-xl border bg-white px-3 py-2 text-sm shadow-sm focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-100"
          />
        </div>
      </div>

      {/* Source row */}
      <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-end">
        <div className="flex-1">
          {mode === "file" ? (
            <>
              <label className="mb-1 block text-sm font-semibold text-slate-800">Lecture audio</label>
              <input
                ref={inputRef}
                className="block w-full rounded-xl border bg-white px-3 py-2.5 text-sm shadow-sm file:mr-3 file:rounded-lg file:border-0 file:bg-orange-100 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-orange-700 hover:file:bg-orange-200"
                type="file"
                accept=".mp3,.wav,.m4a,audio/*"
              />
              <p className="mt-2 text-xs text-slate-500">Supported: mp3, wav, m4a. Transcribed locally via Whisper.</p>
            </>
          ) : (
            <>
              <label className="mb-1 block text-sm font-semibold text-slate-800">YouTube link</label>
              <input
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=…"
                className="block w-full rounded-xl border bg-white px-3 py-2.5 text-sm shadow-sm focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-100"
              />
              <p className="mt-2 text-xs text-slate-500">We extract the audio track, then transcribe &amp; process it just like an upload.</p>
            </>
          )}
        </div>
        <button
          className="rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:from-orange-600 hover:to-amber-600 disabled:opacity-50"
          disabled={isPending}
          onClick={onSubmit}
        >
          {isPending ? "Working…" : mode === "file" ? "Upload" : "Fetch & process"}
        </button>
      </div>

      {message ? <p className={`mt-3 text-sm ${isError ? "text-rose-600" : "text-slate-600"}`}>{message}</p> : null}
    </section>
  );
}
