# 🎓 AI Lecture Notes & Study Agent

> Turn lecture **audio** or a **YouTube link** into structured notes, auto-generated quizzes, and a **citation-grounded study chatbot** — all running locally.

A full-stack, **RAG-based** (Retrieval-Augmented Generation) study assistant. Upload a lecture (or paste a YouTube URL); it transcribes the audio locally, splits it into structured sections with summaries, generates a quiz, indexes everything into a vector database, and lets you **chat with your lectures** — every answer grounded in the source material with inline citations.

<p align="center">
  <em>Next.js · TypeScript · FastAPI · LangGraph · Whisper · ChromaDB · Gemini</em>
</p>

---

## ✨ What it does

| | Feature |
|---|---|
| 🎧 | **Two ingestion paths** — upload `mp3 / wav / m4a`, or paste a **YouTube link** (audio auto-extracted with `yt-dlp`) |
| 📝 | **Structured notes** — transcript split into titled sections, each with an AI summary |
| ❓ | **Interactive quizzes** — auto-generated MCQs; pick an answer, get graded, see the explanation |
| 💬 | **RAG chat with citations** — ask questions in natural language; answers cite the exact lecture/section/timestamp |
| 🗂️ | **Organization** — file lectures under **Subject → Chapter → Subsection** |
| 🧠 | **Conversation memory** — follow-up questions ("explain that more") remember the thread; past chats are saved |
| 🔒 | **Local-first & private** — transcription runs on your machine; only text is sent to the LLM |

---

## 🏗️ How it works

The system has two halves: an **ingestion pipeline** (build the knowledge base) and a **RAG query flow** (answer questions from it).

### Stage 1 — Ingestion pipeline (LangGraph state machine)

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

**Status lifecycle:** `QUEUED → TRANSCRIBING → INDEXING → DONE` (or `FAILED`).

### Stage 2 — RAG query flow (chat)

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
  Gemini generate ─► grounded answer + citations (lecture / section / timestamp)
       ▼
  persist messages (session memory) ─► return to UI
```

> 📖 Full component breakdown, data model, and design decisions: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**

---

## 🧰 Tech stack

**Frontend:** Next.js 14 (App Router) · React 18 · TypeScript · Tailwind CSS
**Backend:** FastAPI · SQLModel (SQLite) · Pydantic · Tenacity
**AI / ML:** LangGraph (orchestration) · OpenAI Whisper (local ASR) · Google Gemini (generation + embeddings) · ChromaDB (vector store)
**Ingestion:** yt-dlp + ffmpeg (YouTube audio extraction)

---

## 📂 Project structure

```
.
├── backend/
│   └── app/
│       ├── main.py            # FastAPI app factory, router wiring, startup
│       ├── config.py          # settings + multi-key Gemini config
│       ├── database.py        # engine, migrations, startup recovery
│       ├── models.py          # SQLModel tables
│       ├── schemas.py         # Pydantic request/response models
│       ├── api/               # routers: lectures, subjects, chat, health
│       ├── graph/             # LangGraph: workflow, nodes, state
│       ├── services/          # whisper, gemini_client, youtube, chunking, validation
│       └── rag/               # embeddings, chroma_store, chat_service
├── frontend/
│   ├── app/                   # pages: dashboard, /chat, /lectures/[id]
│   ├── components/            # upload-panel, lecture-table, chat-panel, quiz-view …
│   └── lib/                   # api client, types, formatters
├── data/                      # SQLite db, Chroma vectors, uploaded audio (gitignored)
├── docs/ARCHITECTURE.md       # system design
└── README.md
```

---

## 🚀 Getting started

### Prerequisites
- **Python 3.11 or 3.12** (Whisper does not install cleanly on 3.14)
- **Node.js 20+**
- **ffmpeg** installed locally (`brew install ffmpeg` on macOS)
- A **Google Gemini API key** ([get one here](https://aistudio.google.com/apikey))

### 1. Clone & configure
```bash
git clone <your-repo-url>
cd ai-lecture-notes-study-agent
cp .env.example .env
# edit .env and add your GEMINI_API_KEY
```

### 2. Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
uvicorn backend.app.main:app --reload      # → http://localhost:8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev                                 # → http://localhost:3000
```

Open **http://localhost:3000** and upload a lecture or paste a YouTube link.

---

## ⚙️ Configuration (`.env`)

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | Gemini API key (comma-separate for multiple) | — |
| `GEMINI_API_KEY_2` | Optional second key — used for automatic failover on quota limits | — |
| `GEMINI_MODEL` | Generation model | `gemini-2.5-flash` |
| `GEMINI_EMBEDDING_MODEL` | Embedding model | `gemini-embedding-2` |
| `WHISPER_MODEL` | Whisper size (`tiny`/`base`/`small`/…) | `base` |
| `DATABASE_URL` | SQLite path | `sqlite:///./data/app.db` |
| `CHROMA_PATH` | Chroma persistence dir | `./data/chroma` |
| `UPLOAD_DIR` | Audio storage dir | `./data/uploads` |
| `BACKEND_CORS_ORIGINS` | Allowed frontend origins | `http://localhost:3000` |

> **Free-tier note:** Gemini's free tier caps requests per **day, per project, per model**. If you hit `429`, switch `GEMINI_MODEL`, add a key from a *different* project, or enable billing. The backend fails over across keys automatically and degrades gracefully.

---

## 🔌 API reference

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/lectures/upload` | Upload audio (+ optional subject/chapter/subsection) |
| `POST` | `/lectures/youtube` | Ingest a YouTube link |
| `GET` | `/lectures` | List lectures (optional `?subject_id=`) |
| `GET` | `/lectures/{id}` | Full detail: transcript, notes, quiz, events |
| `POST` | `/lectures/{id}/retry` | Reprocess a failed lecture |
| `DELETE` | `/lectures/{id}` | Delete lecture + audio + vectors |
| `GET` / `POST` | `/subjects` | List / create subjects |
| `POST` | `/subjects/{id}/chapters` | Add a chapter |
| `POST` | `/chat` | Ask a question (RAG) |
| `GET` | `/chat/sessions` | List chat sessions |
| `GET` / `DELETE` | `/chat/sessions/{id}` | Get / delete a session |

Interactive docs (Swagger UI) at **http://localhost:8000/docs**.

---

## 🧪 Tests
```bash
cd backend && pytest
```

---

## 🧭 Design highlights

- **Self-healing pipeline** — malformed LLM JSON is fed back for repair (up to 2 retries) before failing.
- **Hallucination guardrails** — chat answers only from retrieved context; unsupported questions are declined.
- **Relevance filtering** — retrieval keeps only chunks close to the best match, preventing cross-topic citation leakage.
- **Intent routing** — greetings get a natural reply instead of a robotic "not in the lectures".
- **Production hardening** — multi-key API failover, graceful LLM-error handling, live status polling, and startup recovery for interrupted jobs.

## 🗺️ Roadmap / known limitations
- Single-user, local MVP (no auth) — background jobs run in-process rather than on a queue.
- No streaming chat responses yet.
- Subject/chapter is set at upload time (no rename/delete UI yet).

## 📄 License
MIT (or your choice).
