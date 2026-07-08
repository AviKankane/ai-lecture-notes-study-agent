from __future__ import annotations

import re

from sqlmodel import Session, select

from ..database import engine
from ..models import ChatMessage, ChatSession, utcnow
from ..schemas import ChatResponse, Citation
from ..services.gemini_client import GeminiClient
from .chroma_store import ChromaStore
from .embeddings import embed_texts

HISTORY_TURNS = 6  # how many prior messages to feed back in for follow-up context
MAX_CONTEXT_CHUNKS = 5  # cap chunks used for context/citations
RELEVANCE_FACTOR = 1.35  # keep chunks whose distance is within this multiple of the closest hit


def _filter_relevant(matches: list[dict]) -> list[dict]:
    """Chroma returns the N nearest chunks regardless of how relevant they truly are, so a
    query about 'conduction' can drag in a loosely-related 'radiation' chunk. Keep only chunks
    close to the best match (relative to the top hit, so it adapts to the embedding scale)."""
    scored = [m for m in matches if m.get("distance") is not None]
    if not scored:
        return matches[:MAX_CONTEXT_CHUNKS]
    scored.sort(key=lambda m: m["distance"])
    best = scored[0]["distance"]
    threshold = best * RELEVANCE_FACTOR + 1e-6
    kept = [m for m in scored if m["distance"] <= threshold]
    return kept[:MAX_CONTEXT_CHUNKS]

# Greetings, thanks, and questions about the assistant itself — these should get a
# warm conversational reply, NOT a "not in the lectures" refusal.
_SMALLTALK_EXACT = {
    "hi", "hey", "hello", "helloo", "yo", "hii", "hiii", "heya", "hiya", "sup", "hola",
    "namaste", "hey there", "hello there", "thanks", "thank you", "thankyou", "ty",
    "thx", "ok", "okay", "k", "cool", "nice", "great", "awesome", "good", "bye",
    "goodbye", "see ya", "good morning", "good afternoon", "good evening", "gm", "wassup",
    "whats up", "what's up", "how are you", "how are you?", "who are you", "who are you?",
    "what can you do", "what can you do?", "what can u do", "help", "what is this",
    "how do you work",
}
_GREETING_PREFIXES = ("hi", "hey", "hello", "thanks", "thank", "good morning", "good afternoon", "good evening", "yo ")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower()).strip("!.?,")


def is_smalltalk(question: str) -> bool:
    t = _normalize(question)
    if not t:
        return True
    if t in _SMALLTALK_EXACT:
        return True
    words = t.split()
    if len(words) <= 3 and any(t.startswith(p) for p in _GREETING_PREFIXES):
        return True
    return False


def _friendly_llm_error(exc: Exception) -> str:
    text = str(exc)
    if "429" in text or "RESOURCE_EXHAUSTED" in text or "quota" in text.lower():
        return (
            "⚠️ The language model is rate-limited right now — every configured Gemini key has hit its "
            "quota. Your question was saved — please try again in a minute, add another key, or enable "
            "billing on a key."
        )
    return "⚠️ The language model could not be reached just now. Your question was saved — please try again shortly."


def _get_or_create_session(
    db: Session, session_id: int | None, lecture_ids: list[int], question: str
) -> ChatSession:
    if session_id is not None:
        session = db.get(ChatSession, session_id)
        if session is not None:
            if lecture_ids:
                session.lecture_ids_json = lecture_ids
            session.updated_at = utcnow()
            db.add(session)
            return session
    title = question.strip()[:60] or "New chat"
    session = ChatSession(title=title, lecture_ids_json=lecture_ids)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _recent_history(db: Session, session_id: int) -> list[ChatMessage]:
    messages = db.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(HISTORY_TURNS)
    ).all()
    return list(reversed(messages))


def _history_block(history: list[ChatMessage]) -> str:
    if not history:
        return ""
    rendered = "\n".join(f"{m.role.upper()}: {m.content}" for m in history)
    return (
        "Conversation so far (use it to resolve follow-ups like 'explain that more' or 'why?'):\n"
        f"{rendered}\n\n"
    )


def _greeting_prompt(question: str, history: list[ChatMessage], has_lectures: bool) -> str:
    hint = (
        "The student already has processed lectures, so invite them to ask about that material."
        if has_lectures
        else "The student has not uploaded any lectures yet, so gently suggest uploading an audio file or a YouTube link."
    )
    return (
        "You are a warm, encouraging study assistant that helps students learn from their own "
        "uploaded lecture material. The student's message is casual (a greeting, thanks, or a "
        "question about you) rather than a specific lecture question. "
        "Reply naturally and briefly (1-2 sentences). Do NOT say you don't know or mention missing "
        f"data. {hint}\n\n"
        f"{_history_block(history)}"
        f"Student: {question}"
    )


def _grounded_prompt(question: str, context: str, history: list[ChatMessage]) -> str:
    return (
        "You are a patient study tutor answering from a student's own lecture material. "
        "The retrieved transcript excerpts below are your source of truth. Ground every claim in "
        "them and do not introduce outside facts the excerpts do not support.\n\n"
        "If the student's message is actually just a greeting or small talk, reply warmly in one "
        "sentence and invite a lecture question — do not refuse.\n\n"
        "Otherwise answer in three parts using this exact markdown layout:\n"
        "**Answer**\n"
        "1-3 sentences answering the question directly from the lecture.\n\n"
        "**In detail**\n"
        "A thorough explanation (3-6 sentences) that unpacks the idea, defines terms, and walks "
        "through the reasoning or example from the lecture so it is easy to understand.\n\n"
        "**From the lecture**\n"
        "1-2 short paraphrased references pointing to what the lecture actually said.\n\n"
        "Only if the student clearly asked a lecture question that the context does not cover, "
        "reply: I couldn't find that in your uploaded lectures — try rephrasing or picking a "
        "different lecture.\n\n"
        f"{_history_block(history)}"
        f"Student question: {question}\n\nContext:\n{context}"
    )


def _persist_assistant(db: Session, session: ChatSession, content: str, citations: list[Citation]):
    db.add(
        ChatMessage(
            session_id=session.id,
            role="assistant",
            content=content,
            citations_json=[c.model_dump() for c in citations],
        )
    )
    session.updated_at = utcnow()
    db.add(session)
    db.commit()


def answer_question(
    question: str, lecture_ids: list[int], session_id: int | None = None
) -> ChatResponse:
    with Session(engine) as db:
        session = _get_or_create_session(db, session_id, lecture_ids, question)
        session_pk = session.id
        effective_lecture_ids = lecture_ids or session.lecture_ids_json or []
        history = _recent_history(db, session_pk)

        db.add(ChatMessage(session_id=session_pk, role="user", content=question))
        db.commit()

        store = ChromaStore()

        # 1) Greetings / small talk → conversational reply, no retrieval, no citations.
        if is_smalltalk(question):
            has_lectures = store.count() > 0
            prompt = _greeting_prompt(question, history, has_lectures)
            try:
                answer = GeminiClient().generate_text(prompt)
            except Exception as exc:
                answer = _friendly_llm_error(exc)
            _persist_assistant(db, session, answer, [])
            return ChatResponse(answer=answer, citations=[], session_id=session_pk)

        # 2) Real question → retrieve embeddings and answer with references.
        vector = embed_texts([question])[0]
        matches = _filter_relevant(store.query(vector, lecture_ids=effective_lecture_ids))

        if not matches:
            answer = (
                "You don't have any processed lectures to search yet. Upload an audio file or paste a "
                "YouTube link on the dashboard, and once it finishes processing I can answer from it."
            )
            _persist_assistant(db, session, answer, [])
            return ChatResponse(answer=answer, citations=[], session_id=session_pk)

        citations = [
            Citation(
                lecture_id=match["metadata"]["lecture_id"],
                lecture_title=match["metadata"]["lecture_title"],
                section_id=match["metadata"].get("section_id"),
                section_title=match["metadata"].get("section_title"),
                snippet=match["document"][:240],
                start_seconds=match["metadata"].get("start_seconds"),
                end_seconds=match["metadata"].get("end_seconds"),
            )
            for match in matches
        ]
        context = "\n\n".join(
            f"[Lecture: {match['metadata']['lecture_title']} | Section: {match['metadata'].get('section_title', 'N/A')}]\n{match['document']}"
            for match in matches
        )
        prompt = _grounded_prompt(question, context, history)
        try:
            answer = GeminiClient().generate_text(prompt)
        except Exception as exc:  # keep the chat usable if the LLM call fails
            answer = _friendly_llm_error(exc)
            _persist_assistant(db, session, answer, citations)
            return ChatResponse(answer=answer, citations=citations, session_id=session_pk)

        _persist_assistant(db, session, answer, citations)
        return ChatResponse(answer=answer, citations=citations, session_id=session_pk)
