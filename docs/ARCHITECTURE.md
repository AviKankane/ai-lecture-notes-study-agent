# Architecture & System Design

This document describes the system design of the **AI Lecture Notes & Study Agent** — its layers, data flow, storage model, and the key engineering decisions behind it.

---

## 1. Overview

The application is a **local-first, RAG-based study assistant**. It has two conceptual halves:

1. **Ingestion pipeline (write path)** — converts a lecture (audio file or YouTube link) into structured notes, quizzes, and searchable vector embeddings. Orchestrated by a **LangGraph** state machine that runs asynchronously as a FastAPI background task.
2. **RAG query flow (read path)** — answers a user's question by retrieving relevant transcript chunks from the vector store and having an LLM generate a grounded, cited answer.

Audio never leaves the machine (Whisper runs locally); only text is sent to the Gemini API.

---

## 2. High-level block diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT  (Next.js 14 / React / TS / Tailwind)     │
│   Dashboard (/)          Lecture detail (/lectures/[id])     Chat (/chat) │
│   • Upload / YouTube      • Transcript, notes, quiz           • Threaded   │
│   • Subject/Chapter       • Processing log                     RAG chat    │
│   • Live status poll      • Interactive quiz                  • Sessions   │
└───────────────────────────────────┬───────────────────────────────────────┘
                                     │  REST / JSON (fetch)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        API LAYER  (FastAPI + CORS)                        │
│   /lectures   /lectures/upload   /lectures/youtube   /subjects   /chat    │
│   /chat/sessions        /health          (background tasks dispatched)    │
└───────┬───────────────────────────────┬───────────────────────┬──────────┘
        │ ingest                         │ query (RAG)           │ organize
        ▼                                ▼                       ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌──────────────────┐
│  PROCESSING           │   │  RAG QUERY LAYER      │   │  ORG / METADATA  │
│  LangGraph workflow   │   │  chat_service         │   │  Subject/Chapter │
│  (state machine)      │   │  • intent routing     │   │  get-or-create   │
│                       │   │  • retrieve + filter  │   │                  │
│                       │   │  • grounded generate  │   │                  │
└───┬───────────────────┘   └────────┬──────────────┘   └────────┬─────────┘
    │                                 │                          │
    ▼                                 ▼                          ▼
┌─────────────────────────── SERVICES ────────────────────────────────────┐
│  yt-dlp      Whisper       chunking     GeminiClient        validation   │
│  (audio      (local ASR    (300-word    (JSON/text/embed    (Pydantic    │
│   extract)    + ffmpeg)     windows)     + multi-key         schema)     │
│                                          failover)                       │
└───────┬──────────┬──────────────┬─────────────┬──────────────────────────┘
        │          │              │             │
        ▼          ▼              ▼             ▼
┌────────────┐ ┌────────┐  ┌─────────────┐ ┌──────────────────┐
│ Filesystem │ │ SQLite │  │  ChromaDB   │ │  EXTERNAL APIs   │
│ data/      │ │ app.db │  │ vector store│ │  • Gemini (LLM   │
│  uploads/  │ │(SQLModel│ │ 3072-dim    │ │    + embeddings) │
│  *.mp3     │ │ tables) │ │ HNSW index  │ │  • YouTube       │
└────────────┘ └────────┘  └─────────────┘ └──────────────────┘
```

---

## 3. Layer breakdown

### 3.1 Client (Next.js App Router)
- **Server components** fetch initial data (`fetchLectures`, `fetchLecture`); **client components** handle interactivity.
- **Dashboard** — upload panel (file/YouTube tabs + Subject/Chapter/Subsection), lecture table with **live polling** (every 3s while any lecture is processing).
- **Lecture detail** — transcript, processing log, structured notes, interactive quiz.
- **Chat** — threaded message UI, session sidebar (history), lecture filter.

### 3.2 API layer (FastAPI)
- Thin routers that validate input (Pydantic), dispatch work, and serialize responses.
- Long-running ingestion is offloaded via `BackgroundTasks` so uploads return immediately.

### 3.3 Processing layer (LangGraph)
- A compiled `StateGraph` with typed state (`LectureGraphState`).
- **Conditional routing:** short vs. long transcripts; valid vs. repair vs. fail.
- Every node writes a `ProcessingEvent` (audit trail) and updates lecture status.

### 3.4 Services
| Service | Responsibility |
|---|---|
| `youtube` | Extract audio from a YouTube URL (yt-dlp + ffmpeg) |
| `transcription` | Local Whisper ASR → text + timestamped segments |
| `chunking` | Split section text into ~300-word windows (200–400 range) |
| `gemini_client` | LLM calls (JSON/text) + embeddings, with retry and **multi-key failover** |
| `validation` | Validate generated notes/quizzes against a Pydantic schema |
| `organization` | Get-or-create Subject/Chapter by name |

### 3.5 RAG layer
- `embeddings` → Gemini embedding calls.
- `chroma_store` → wrapper over ChromaDB (upsert, query-with-distances, count, delete).
- `chat_service` → intent routing, retrieval, relevance filtering, grounded generation, session memory.

### 3.6 Storage
- **SQLite** (`data/app.db`) — all textual/relational data.
- **ChromaDB** (`data/chroma/`) — embedding vectors (HNSW index) + chunk metadata.
- **Filesystem** (`data/uploads/`) — original/extracted audio files.

---

## 4. Ingestion pipeline (LangGraph state machine)

```
 upload file ──┐
               ├─► [Lecture: QUEUED] ─► background task
 youtube link ─┘         │
                         ▼
        (youtube only)  download_audio        # yt-dlp + ffmpeg → mp3
                         │
   START ─► load_lecture ─► transcribe_audio ─► classify_size
                              (Whisper)              │
                                         word_count < 500 ?
                                    ┌──── yes ────────┴──── no ─────┐
                                    ▼                               ▼
                          process_short_transcript      structure_transcript
                          (1 call: notes + quiz)                │
                                    │                    summarize_sections
                                    │                          │
                                    │                      generate_quiz
                                    └──────────┬────────────────┘
                                               ▼
                                       validate_outputs  ◄──────┐
                                      (Pydantic schema)         │ repair (≤2×)
                                   valid │ error ───► repair_outputs (LLM fixes JSON)
                                         ▼
                                   index_chunks
                          (chunk → Gemini embeddings → ChromaDB
                           + persist sections/quizzes → SQLite)
                                         │
                                         ▼
                                   mark_done ─► [DONE]     (failure ─► FAILED, retryable)
```

**Node responsibilities**

| Node | Does |
|---|---|
| `load_lecture` | Verify the audio file exists |
| `transcribe_audio` | Run Whisper → store transcript + segments; compute duration & word count; status `TRANSCRIBING` |
| `classify_transcript_size` | Route by `word_count < 500` |
| `process_short_transcript` | One Gemini call → 1 section + 3 quiz items (cheap path) |
| `structure_transcript` → `summarize_sections` → `generate_quiz` | Long path: split → summarize → 5 quiz items |
| `validate_outputs` | Pydantic validation; on failure route to repair |
| `repair_outputs` | Feed the validation error + bad JSON back to Gemini to fix (≤2 retries) |
| `index_chunks` | Persist sections/quizzes to SQLite; chunk → embed → upsert to Chroma; status `INDEXING` |
| `mark_done` / `mark_failed` | Terminal status transitions |

---

## 5. RAG query flow (chat)

```
 user question
       │
       ▼
  intent routing ──── greeting / small talk? ──► conversational reply (no retrieval)
       │ real question
       ▼
  embed question (Gemini) ─► ChromaDB nearest-neighbor search (top 8)
       ▼
  relevance filter  (keep chunks within 1.35× of the closest hit, cap 5)
       ▼
  prompt = [chat history] + [retrieved chunks] + [question]
       ▼
  Gemini generate ─► grounded 3-part answer + citations (lecture / section / timestamp)
       ▼
  persist user + assistant messages (session memory) ─► return to UI
```

**Retrieval details**
- Each chunk is embedded to a **3072-dim** vector and stored with metadata: `lecture_id`, `lecture_title`, `section_id`, `section_title`, and (when known) `start_seconds`/`end_seconds`.
- The lecture filter maps to a Chroma `where` clause: `{"lecture_id": {"$in": [...]}}`.
- **Relevance filtering** keeps only chunks whose distance is within `1.35×` of the closest hit (relative, so it adapts to embedding scale) — this stops loosely-related chunks (e.g. "radiation" for a "conduction" query) from being cited.

---

## 6. Data model

```
Subject ──1:N── Chapter
   │                │
   └────────┐   ┌───┘
            ▼   ▼
          Lecture ──1:1── Transcript        (full text + timestamped segments)
            │   ├──1:N── Section            (title, summary, text, start/end)
            │   ├──1:N── QuizItem           (question, options, answer, explanation)
            │   └──1:N── ProcessingEvent    (per-step audit log)
            │
ChatSession ──1:N── ChatMessage             (role, content, citations)   [chat memory]
```

- **SQLite** holds all *text*; **Chroma** holds the *vectors*. They stay in sync via `lecture_id` / `section_id`.
- Chunk vector ids are deterministic: `lecture-{lecture_id}-section-{section_id}-chunk-{n}` → re-indexing is idempotent.

---

## 7. Key design decisions

| Concern | Decision | Rationale |
|---|---|---|
| Orchestration | LangGraph state machine | Explicit branching + a self-repair loop for malformed LLM JSON |
| Grounding | Retrieve → constrain prompt → cite | Prevents hallucination; answers traceable to source |
| Relevance | Distance filter relative to best hit | Cuts cross-topic citation leakage without a magic absolute threshold |
| Intent | Route greetings away from retrieval | Natural small-talk replies instead of robotic refusals |
| Privacy | Whisper runs locally | Audio never leaves the machine |
| Resilience | Multi-key failover, graceful LLM errors, startup recovery | Survives rate limits, API failures, and mid-job restarts |
| Async | FastAPI BackgroundTasks | Non-blocking uploads; UI polls for status |
| Idempotency | Delete-then-reindex on (re)process | Re-running never duplicates vectors |
| Schema evolution | PRAGMA-based column migration on startup | Adds new columns to existing SQLite tables safely |

---

## 8. Request lifecycles

**Upload → Done**
1. `POST /lectures/upload` saves the file, creates a `Lecture` (`QUEUED`), resolves Subject/Chapter, dispatches a background task.
2. LangGraph workflow: transcribe → structure/summarize/quiz → validate (→repair) → index → `DONE`.
3. Dashboard polling reflects each status change live.

**YouTube → Done**
1. `POST /lectures/youtube` creates the lecture and dispatches `run_youtube_ingestion`.
2. `download_audio` (yt-dlp + ffmpeg) fetches the mp3 and updates the lecture, then the normal workflow runs.

**Question → Answer**
1. `POST /chat` → `answer_question` stores the user message, routes intent.
2. Real question: embed → Chroma search → relevance filter → grounded generate → persist assistant message + citations → respond.

---

## 9. Failure handling

- **LLM quota/rate limit (429):** the Gemini client fails over across configured keys; if all are exhausted, chat returns a friendly message and the pipeline marks the lecture `FAILED` (retryable).
- **Malformed LLM output:** caught by `validate_outputs`, repaired by `repair_outputs` (≤2 attempts).
- **Server restart mid-job:** on startup, lectures stuck in a non-terminal state are flipped to `FAILED` with a clear message so the user can retry.
- **Transient network errors:** Tenacity retries (exponential backoff, 3 attempts) per key.
