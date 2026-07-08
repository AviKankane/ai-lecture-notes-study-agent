from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
from sqlmodel import Session, delete, select

from ..database import engine
from ..models import Lecture, LectureStatus, ProcessingEvent, QuizItem, Section, Transcript, utcnow
from ..rag.chroma_store import ChromaStore
from ..rag.embeddings import embed_texts
from ..schemas import QuizItemGeneration, SectionGeneration
from ..services.chunking import count_words, split_text_into_chunks
from ..services.gemini_client import GeminiClient
from ..services.transcription import WhisperTranscriber
from ..services.validation import validate_generation_payload, validation_error_text


def log_event(session: Session, lecture_id: int, step: str, status: str, message: str | None = None) -> None:
    session.add(ProcessingEvent(lecture_id=lecture_id, step=step, status=status, message=message))


def update_lecture(session: Session, lecture: Lecture, status: LectureStatus, error_message: str | None = None) -> None:
    lecture.status = status
    lecture.error_message = error_message
    lecture.updated_at = utcnow()
    session.add(lecture)


def load_lecture(state):
    with Session(engine) as session:
        lecture = session.get(Lecture, state["lecture_id"])
        if lecture is None:
            raise RuntimeError("Lecture not found")
        if not Path(lecture.audio_path).exists():
            raise RuntimeError("Audio file missing")
        log_event(session, lecture.id, "load_lecture", "ok")
        session.commit()
        return {"audio_path": lecture.audio_path, "current_step": "load_lecture"}


def transcribe_audio(state):
    with Session(engine) as session:
        lecture = session.get(Lecture, state["lecture_id"])
        update_lecture(session, lecture, LectureStatus.TRANSCRIBING)
        log_event(session, lecture.id, "transcribe_audio", "started")
        session.commit()

        result = WhisperTranscriber().transcribe(lecture.audio_path)
        transcript = session.exec(select(Transcript).where(Transcript.lecture_id == lecture.id)).first()
        if transcript is None:
            transcript = Transcript(lecture_id=lecture.id, text=result["text"], segments_json=result["segments"])
        else:
            transcript.text = result["text"]
            transcript.segments_json = result["segments"]
        session.add(transcript)
        lecture.duration_seconds = result.get("duration_seconds")
        lecture.word_count = count_words(result["text"])
        lecture.updated_at = utcnow()
        log_event(session, lecture.id, "transcribe_audio", "ok")
        session.commit()
        return {
            "transcript_text": result["text"],
            "segments": result["segments"],
            "word_count": lecture.word_count or 0,
            "duration_seconds": lecture.duration_seconds,
            "current_step": "transcribe_audio",
        }


def classify_transcript_size(state):
    return {"current_step": "classify_transcript_size"}


def process_short_transcript(state):
    transcript = state["transcript_text"]
    prompt = (
        "You are processing a short lecture transcript. Return JSON with keys "
        "`sections` and `quiz_items`. Create exactly one section with title, text, and summary. "
        "Create 3 quiz items with question, options, correct_answer, and explanation. Transcript:\n\n"
        f"{transcript}"
    )
    payload = GeminiClient().generate_json(prompt)
    validated = validate_generation_payload(payload)
    return {
        "sections": [section.model_dump() for section in validated.sections],
        "quiz_items": [item.model_dump() for item in validated.quiz_items],
        "current_step": "process_short_transcript",
    }


def structure_transcript(state):
    transcript = state["transcript_text"]
    prompt = (
        "Split this lecture transcript into logical sections. "
        "Return JSON with one key: `sections`. "
        "Each section must include title, text, start_seconds, and end_seconds when inferable. "
        "Do not include summaries or quiz items.\n\nTranscript:\n"
        f"{transcript}"
    )
    payload = GeminiClient().generate_json(prompt)
    sections = payload.get("sections", [])
    return {
        "sections": sections,
        "quiz_items": [],
        "current_step": "structure_transcript",
    }


def summarize_sections(state):
    transcript_sections = state.get("sections", [])
    prompt = (
        "Generate concise summaries for each lecture section. Return JSON with key `sections`. "
        "Each item must include title, text, summary, start_seconds, and end_seconds. "
        f"Sections:\n{transcript_sections}"
    )
    payload = GeminiClient().generate_json(prompt)
    return {
        "sections": payload.get("sections", []),
        "current_step": "summarize_sections",
    }


def generate_quiz(state):
    prompt = (
        "Generate 5 quiz items from this lecture content. Return JSON with key `quiz_items`. "
        "Each item must include question, options, correct_answer, and explanation. "
        f"Sections:\n{state.get('sections', [])}"
    )
    payload = GeminiClient().generate_json(prompt)
    return {
        "quiz_items": payload.get("quiz_items", []),
        "current_step": "generate_quiz",
    }


def validate_outputs(state):
    try:
        payload = {
            "sections": [SectionGeneration.model_validate(section).model_dump() for section in state.get("sections", [])],
            "quiz_items": [QuizItemGeneration.model_validate(item).model_dump() for item in state.get("quiz_items", [])],
        }
        validate_generation_payload(payload)
        return {"current_step": "validate_outputs"}
    except ValidationError as exc:
        return {"error": validation_error_text(exc), "current_step": "validate_outputs"}


def repair_outputs(state):
    prompt = (
        "Repair this malformed lecture processing JSON. Return valid JSON with keys "
        "`sections` and `quiz_items`. Keep the original meaning. Validation error:\n"
        f"{state.get('error', '')}\n\nOriginal sections:\n{state.get('sections', [])}\n\n"
        f"Original quiz items:\n{state.get('quiz_items', [])}"
    )
    payload = GeminiClient().generate_json(prompt)
    validated = validate_generation_payload(payload)
    return {
        "sections": [section.model_dump() for section in validated.sections],
        "quiz_items": [item.model_dump() for item in validated.quiz_items],
        "error": None,
        "retry_count": state.get("retry_count", 0) + 1,
        "current_step": "repair_outputs",
    }


def index_chunks(state):
    with Session(engine) as session:
        lecture = session.get(Lecture, state["lecture_id"])
        update_lecture(session, lecture, LectureStatus.INDEXING)
        log_event(session, lecture.id, "index_chunks", "started")
        session.exec(delete(Section).where(Section.lecture_id == lecture.id))
        session.exec(delete(QuizItem).where(QuizItem.lecture_id == lecture.id))
        session.commit()

        persisted_sections: list[Section] = []
        for idx, section_payload in enumerate(state.get("sections", [])):
            section = Section(
                lecture_id=lecture.id,
                order_index=idx,
                title=section_payload["title"],
                start_seconds=section_payload.get("start_seconds"),
                end_seconds=section_payload.get("end_seconds"),
                text=section_payload["text"],
                summary=section_payload["summary"],
            )
            session.add(section)
            persisted_sections.append(section)

        for item_payload in state.get("quiz_items", []):
            session.add(
                QuizItem(
                    lecture_id=lecture.id,
                    question=item_payload["question"],
                    options_json=item_payload["options"],
                    correct_answer=item_payload["correct_answer"],
                    explanation=item_payload["explanation"],
                )
            )

        session.commit()

        store = ChromaStore()
        store.delete_lecture(lecture.id)
        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict] = []
        for section in persisted_sections:
            session.refresh(section)
            chunks = split_text_into_chunks(section.text)
            for chunk in chunks:
                ids.append(f"lecture-{lecture.id}-section-{section.id}-chunk-{chunk.chunk_index}")
                texts.append(chunk.text)
                # Chroma rejects None metadata values, so only include timestamps when present
                # (short transcripts have no inferred start/end).
                metadata = {
                    "lecture_id": lecture.id,
                    "lecture_title": lecture.title,
                    "section_id": section.id,
                    "section_title": section.title,
                }
                if section.start_seconds is not None:
                    metadata["start_seconds"] = section.start_seconds
                if section.end_seconds is not None:
                    metadata["end_seconds"] = section.end_seconds
                metadatas.append(metadata)
        if texts:
            embeddings = embed_texts(texts)
            store.upsert_chunks(ids=ids, texts=texts, embeddings=embeddings, metadatas=metadatas)

        lecture.updated_at = utcnow()
        log_event(session, lecture.id, "index_chunks", "ok")
        session.commit()
        return {"current_step": "index_chunks"}


def mark_done(state):
    with Session(engine) as session:
        lecture = session.get(Lecture, state["lecture_id"])
        update_lecture(session, lecture, LectureStatus.DONE)
        log_event(session, lecture.id, "mark_done", "ok")
        session.commit()
    return {"current_step": "mark_done"}


def mark_failed(state):
    with Session(engine) as session:
        lecture = session.get(Lecture, state["lecture_id"])
        update_lecture(session, lecture, LectureStatus.FAILED, error_message=state.get("error", "Processing failed"))
        log_event(session, lecture.id, "mark_failed", "error", state.get("error"))
        session.commit()
    return {"current_step": "mark_failed"}
