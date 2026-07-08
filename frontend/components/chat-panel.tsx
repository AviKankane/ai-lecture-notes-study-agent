"use client";

import { useEffect, useRef, useState, useTransition } from "react";

import { askQuestion, deleteChatSession, fetchChatSession, fetchChatSessions } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import { ChatMessage, ChatSessionListItem, Citation, LectureListItem } from "@/lib/types";

import { Citations } from "./citations";

function MessageContent({ text }: { text: string }) {
  // Lightweight renderer: bold **headings** and keep line breaks, no extra deps.
  return (
    <div className="space-y-1 text-sm leading-relaxed text-slate-700">
      {text.split("\n").map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-1.5" />;
        const parts = line.split(/(\*\*[^*]+\*\*)/g);
        return (
          <p key={i} className="whitespace-pre-wrap">
            {parts.map((part, j) =>
              part.startsWith("**") && part.endsWith("**") ? (
                <strong key={j} className="font-semibold text-slate-900">
                  {part.slice(2, -2)}
                </strong>
              ) : (
                <span key={j}>{part}</span>
              )
            )}
          </p>
        );
      })}
    </div>
  );
}

export function ChatPanel({ lectures }: { lectures: LectureListItem[] }) {
  const [question, setQuestion] = useState("");
  const [selectedLectureIds, setSelectedLectureIds] = useState<number[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<ChatSessionListItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();
  const threadRef = useRef<HTMLDivElement | null>(null);

  const readyLectures = lectures.filter((lecture) => lecture.status === "done");

  async function loadSessions() {
    try {
      setSessions(await fetchChatSessions());
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isPending]);

  function toggleLecture(id: number) {
    setSelectedLectureIds((current) => (current.includes(id) ? current.filter((v) => v !== id) : [...current, id]));
  }

  function newChat() {
    setActiveSessionId(null);
    setMessages([]);
    setSelectedLectureIds([]);
    setError("");
    setQuestion("");
  }

  function openSession(id: number) {
    startTransition(async () => {
      try {
        const detail = await fetchChatSession(id);
        setActiveSessionId(detail.id);
        setMessages(detail.messages);
        setSelectedLectureIds(detail.lecture_ids ?? []);
        setError("");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load chat");
      }
    });
  }

  function removeSession(id: number) {
    startTransition(async () => {
      await deleteChatSession(id);
      if (id === activeSessionId) newChat();
      await loadSessions();
    });
  }

  function onSubmit() {
    if (!question.trim()) {
      setError("Enter a question.");
      return;
    }
    const asked = question.trim();
    setError("");
    setQuestion("");
    // optimistic user bubble
    const optimistic: ChatMessage = {
      id: Date.now(),
      role: "user",
      content: asked,
      citations: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);

    startTransition(async () => {
      try {
        const next = await askQuestion(asked, selectedLectureIds, activeSessionId);
        const assistant: ChatMessage = {
          id: Date.now() + 1,
          role: "assistant",
          content: next.answer,
          citations: next.citations as Citation[],
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistant]);
        if (next.session_id) setActiveSessionId(next.session_id);
        await loadSessions();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Chat failed");
      }
    });
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[300px,1fr]">
      {/* Sidebar: history + lecture filter */}
      <aside className="flex flex-col gap-4">
        <button
          onClick={newChat}
          className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:from-orange-600 hover:to-amber-600"
        >
          + New chat
        </button>

        <div className="rounded-2xl border border-white/60 bg-white/75 p-4 shadow-sm backdrop-blur">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">History</h2>
          <div className="mt-3 grid gap-1.5">
            {sessions.length ? (
              sessions.map((s) => (
                <div
                  key={s.id}
                  className={`group flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-sm transition ${
                    s.id === activeSessionId ? "bg-orange-100 text-orange-900" : "hover:bg-slate-100 text-slate-700"
                  }`}
                >
                  <button className="min-w-0 flex-1 text-left" onClick={() => openSession(s.id)}>
                    <span className="block truncate font-medium">{s.title}</span>
                    <span className="block text-xs text-slate-400">
                      {s.message_count} msgs · {relativeTime(s.updated_at)}
                    </span>
                  </button>
                  <button
                    className="opacity-0 transition group-hover:opacity-100 text-slate-400 hover:text-rose-600"
                    onClick={() => removeSession(s.id)}
                    aria-label="Delete chat"
                  >
                    ✕
                  </button>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No past chats yet.</p>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-white/60 bg-white/75 p-4 shadow-sm backdrop-blur">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Lecture filter</h2>
          <p className="mt-1.5 text-xs text-slate-500">Leave all unchecked to search every indexed lecture.</p>
          <div className="mt-3 grid gap-2">
            {readyLectures.length ? (
              readyLectures.map((lecture) => (
                <label
                  key={lecture.id}
                  className="flex items-start gap-2.5 rounded-lg border bg-white p-2.5 text-sm shadow-sm transition hover:border-orange-300 hover:bg-orange-50/40"
                >
                  <input
                    checked={selectedLectureIds.includes(lecture.id)}
                    className="mt-1 accent-orange-600"
                    type="checkbox"
                    onChange={() => toggleLecture(lecture.id)}
                  />
                  <span className="min-w-0">
                    <span className="block truncate font-medium text-slate-800">{lecture.title}</span>
                  </span>
                </label>
              ))
            ) : (
              <p className="text-sm text-slate-500">No indexed lectures yet.</p>
            )}
          </div>
        </div>
      </aside>

      {/* Main conversation */}
      <div className="flex min-h-[70vh] flex-col rounded-2xl border border-white/60 bg-white/75 shadow-sm backdrop-blur">
        <div ref={threadRef} className="flex-1 space-y-5 overflow-y-auto p-6">
          {messages.length === 0 && !isPending ? (
            <div className="mx-auto mt-10 max-w-lg rounded-2xl border bg-gradient-to-br from-orange-50 via-white to-lime-50 p-8 text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-white text-2xl shadow-sm">
                💬
              </div>
              <h3 className="text-base font-semibold text-slate-800">Ask your lectures anything</h3>
              <p className="mt-2 text-sm text-slate-600">
                Every answer is grounded in your retrieved transcript chunks, explained in detail, and shows the
                supporting citations. Follow-up questions remember the conversation.
              </p>
            </div>
          ) : null}

          {messages.map((m) =>
            m.role === "user" ? (
              <div key={m.id} className="flex justify-end">
                <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-gradient-to-r from-orange-500 to-amber-500 px-4 py-2.5 text-sm text-white shadow-sm">
                  {m.content}
                </div>
              </div>
            ) : (
              <div key={m.id} className="flex justify-start">
                <div className="max-w-[85%] space-y-3">
                  <div className="rounded-2xl rounded-bl-sm border bg-white px-4 py-3 shadow-sm">
                    <MessageContent text={m.content} />
                  </div>
                  {m.citations.length ? (
                    <div className="pl-1">
                      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">Citations</p>
                      <Citations citations={m.citations} />
                    </div>
                  ) : null}
                </div>
              </div>
            )
          )}

          {isPending ? (
            <div className="flex justify-start">
              <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-sm border bg-white px-4 py-3 shadow-sm">
                <span className="h-2 w-2 animate-bounce rounded-full bg-orange-400 [animation-delay:-0.3s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-orange-400 [animation-delay:-0.15s]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-orange-400" />
              </div>
            </div>
          ) : null}
        </div>

        {/* Composer */}
        <div className="border-t border-slate-200/70 p-4">
          {error ? <p className="mb-2 text-sm text-rose-600">{error}</p> : null}
          {!readyLectures.length ? (
            <p className="mb-2 text-sm text-slate-500">Chat activates after at least one lecture reaches <code>done</code>.</p>
          ) : null}
          <div className="flex items-end gap-3">
            <textarea
              className="min-h-[52px] max-h-40 flex-1 resize-none rounded-xl border bg-white px-4 py-3 text-sm shadow-sm focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-100"
              placeholder="Ask about definitions, examples, formulas, or anything covered in your lectures…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSubmit();
                }
              }}
            />
            <button
              className="rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:from-orange-600 hover:to-amber-600 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isPending || !readyLectures.length}
              onClick={onSubmit}
            >
              {isPending ? "…" : "Send"}
            </button>
          </div>
          <p className="mt-1.5 text-xs text-slate-400">Enter to send · Shift+Enter for a new line</p>
        </div>
      </div>
    </section>
  );
}
