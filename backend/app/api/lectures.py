from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from ..config import get_settings
from ..database import engine, get_session
from ..graph.workflow import workflow
from ..models import (
    Chapter,
    Lecture,
    LectureStatus,
    ProcessingEvent,
    QuizItem,
    Section,
    Subject,
    Transcript,
    utcnow,
)
from ..rag.chroma_store import ChromaStore
from ..schemas import (
    DeleteResponse,
    LectureDetailResponse,
    LectureListItem,
    ProcessingEventResponse,
    QuizItemResponse,
    RetryResponse,
    SectionResponse,
    TranscriptResponse,
    UploadResponse,
    YoutubeIngestRequest,
)
from ..services.organization import get_or_create_chapter, get_or_create_subject
from ..services.youtube import YoutubeDownloadError, download_audio, is_youtube_url


router = APIRouter(prefix="/lectures", tags=["lectures"])
SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a"}


def _subject_name(session: Session, subject_id: int | None) -> str | None:
    if not subject_id:
        return None
    subject = session.get(Subject, subject_id)
    return subject.name if subject else None


def _chapter_name(session: Session, chapter_id: int | None) -> str | None:
    if not chapter_id:
        return None
    chapter = session.get(Chapter, chapter_id)
    return chapter.name if chapter else None


def _list_item(session: Session, lecture: Lecture) -> LectureListItem:
    return LectureListItem(
        id=lecture.id,
        title=lecture.title,
        original_filename=lecture.original_filename,
        status=lecture.status,
        word_count=lecture.word_count,
        duration_seconds=lecture.duration_seconds,
        error_message=lecture.error_message,
        subject_id=lecture.subject_id,
        subject_name=_subject_name(session, lecture.subject_id),
        chapter_id=lecture.chapter_id,
        chapter_name=_chapter_name(session, lecture.chapter_id),
        subsection=lecture.subsection,
        source_type=lecture.source_type,
        source_url=lecture.source_url,
        created_at=lecture.created_at,
        updated_at=lecture.updated_at,
    )


def run_workflow(lecture_id: int) -> None:
    try:
        workflow.invoke({"lecture_id": lecture_id, "retry_count": 0})
    except Exception as exc:
        _mark_failed(lecture_id, str(exc), step="workflow")


def run_youtube_ingestion(lecture_id: int, url: str) -> None:
    """Download the audio track first, then run the normal processing workflow."""
    try:
        settings = get_settings()
        result = download_audio(url, settings.upload_dir)
        with Session(engine) as session:
            lecture = session.get(Lecture, lecture_id)
            if lecture is None:
                return
            lecture.audio_path = result["audio_path"]
            lecture.original_filename = result["title"]
            lecture.title = result["title"]
            if result.get("duration_seconds"):
                lecture.duration_seconds = float(result["duration_seconds"])
            lecture.updated_at = utcnow()
            session.add(lecture)
            session.add(ProcessingEvent(lecture_id=lecture_id, step="download", status="ok", message="Audio extracted from YouTube"))
            session.commit()
    except YoutubeDownloadError as exc:
        _mark_failed(lecture_id, str(exc), step="download")
        return
    except Exception as exc:  # noqa: BLE001
        _mark_failed(lecture_id, f"YouTube download failed: {exc}", step="download")
        return
    run_workflow(lecture_id)


def _mark_failed(lecture_id: int, message: str, step: str) -> None:
    with Session(engine) as session:
        lecture = session.get(Lecture, lecture_id)
        if lecture is not None:
            lecture.status = LectureStatus.FAILED
            lecture.error_message = message
            lecture.updated_at = utcnow()
            session.add(lecture)
            session.add(ProcessingEvent(lecture_id=lecture_id, step=step, status="error", message=message))
            session.commit()


@router.post("/upload", response_model=UploadResponse)
def upload_lecture(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    subject: str | None = Form(default=None),
    chapter: str | None = Form(default=None),
    subsection: str | None = Form(default=None),
    session: Session = Depends(get_session),
):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported audio file type")

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid4().hex}{extension}"
    destination = upload_dir / safe_name
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    subject_obj = get_or_create_subject(session, subject)
    chapter_obj = get_or_create_chapter(session, subject_obj, chapter)

    lecture = Lecture(
        title=Path(file.filename or "Lecture").stem,
        original_filename=file.filename or destination.name,
        audio_path=str(destination),
        status=LectureStatus.QUEUED,
        subject_id=subject_obj.id if subject_obj else None,
        chapter_id=chapter_obj.id if chapter_obj else None,
        subsection=(subsection or "").strip() or None,
        source_type="upload",
    )
    session.add(lecture)
    session.commit()
    session.refresh(lecture)

    session.add(ProcessingEvent(lecture_id=lecture.id, step="upload", status="ok"))
    session.commit()
    background_tasks.add_task(run_workflow, lecture.id)
    return UploadResponse(lecture_id=lecture.id, status=lecture.status)


@router.post("/youtube", response_model=UploadResponse)
def ingest_youtube(
    payload: YoutubeIngestRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    if not is_youtube_url(payload.url):
        raise HTTPException(status_code=400, detail="Please provide a valid YouTube link.")

    subject_obj = get_or_create_subject(session, payload.subject)
    chapter_obj = get_or_create_chapter(session, subject_obj, payload.chapter)

    lecture = Lecture(
        title="YouTube lecture (downloading…)",
        original_filename=payload.url,
        audio_path="",
        status=LectureStatus.QUEUED,
        subject_id=subject_obj.id if subject_obj else None,
        chapter_id=chapter_obj.id if chapter_obj else None,
        subsection=(payload.subsection or "").strip() or None,
        source_type="youtube",
        source_url=payload.url,
    )
    session.add(lecture)
    session.commit()
    session.refresh(lecture)

    session.add(ProcessingEvent(lecture_id=lecture.id, step="upload", status="ok", message="YouTube link queued"))
    session.commit()
    background_tasks.add_task(run_youtube_ingestion, lecture.id, payload.url)
    return UploadResponse(lecture_id=lecture.id, status=lecture.status)


@router.get("", response_model=list[LectureListItem])
def list_lectures(subject_id: int | None = None, session: Session = Depends(get_session)):
    statement = select(Lecture).order_by(Lecture.created_at.desc())
    if subject_id is not None:
        statement = statement.where(Lecture.subject_id == subject_id)
    lectures = session.exec(statement).all()
    return [_list_item(session, lecture) for lecture in lectures]


@router.get("/{lecture_id}", response_model=LectureDetailResponse)
def get_lecture(lecture_id: int, session: Session = Depends(get_session)):
    lecture = session.get(Lecture, lecture_id)
    if lecture is None:
        raise HTTPException(status_code=404, detail="Lecture not found")
    transcript = session.exec(select(Transcript).where(Transcript.lecture_id == lecture_id)).first()
    sections = session.exec(select(Section).where(Section.lecture_id == lecture_id).order_by(Section.order_index)).all()
    quiz_items = session.exec(select(QuizItem).where(QuizItem.lecture_id == lecture_id)).all()
    events = session.exec(select(ProcessingEvent).where(ProcessingEvent.lecture_id == lecture_id).order_by(ProcessingEvent.created_at)).all()
    return LectureDetailResponse(
        id=lecture.id,
        title=lecture.title,
        original_filename=lecture.original_filename,
        status=lecture.status,
        word_count=lecture.word_count,
        duration_seconds=lecture.duration_seconds,
        error_message=lecture.error_message,
        subject_id=lecture.subject_id,
        subject_name=_subject_name(session, lecture.subject_id),
        chapter_id=lecture.chapter_id,
        chapter_name=_chapter_name(session, lecture.chapter_id),
        subsection=lecture.subsection,
        source_type=lecture.source_type,
        source_url=lecture.source_url,
        created_at=lecture.created_at,
        updated_at=lecture.updated_at,
        transcript=TranscriptResponse.model_validate(transcript, from_attributes=True) if transcript else None,
        sections=[SectionResponse.model_validate(section, from_attributes=True) for section in sections],
        quiz_items=[QuizItemResponse.model_validate(item, from_attributes=True) for item in quiz_items],
        events=[ProcessingEventResponse.model_validate(event, from_attributes=True) for event in events],
    )


@router.post("/{lecture_id}/retry", response_model=RetryResponse)
def retry_lecture(lecture_id: int, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    lecture = session.get(Lecture, lecture_id)
    if lecture is None:
        raise HTTPException(status_code=404, detail="Lecture not found")
    lecture.status = LectureStatus.QUEUED
    lecture.error_message = None
    lecture.updated_at = utcnow()
    session.add(lecture)
    session.commit()
    # Re-download for YouTube lectures whose audio was never fetched.
    if lecture.source_type == "youtube" and not (lecture.audio_path and Path(lecture.audio_path).exists()):
        background_tasks.add_task(run_youtube_ingestion, lecture_id, lecture.source_url or "")
    else:
        background_tasks.add_task(run_workflow, lecture_id)
    return RetryResponse(lecture_id=lecture.id, status=lecture.status)


@router.delete("/{lecture_id}", response_model=DeleteResponse)
def delete_lecture(lecture_id: int, session: Session = Depends(get_session)):
    lecture = session.get(Lecture, lecture_id)
    if lecture is None:
        raise HTTPException(status_code=404, detail="Lecture not found")
    ChromaStore().delete_lecture(lecture_id)
    audio_path = Path(lecture.audio_path) if lecture.audio_path else None
    if audio_path and audio_path.exists():
        audio_path.unlink()
    transcript = session.exec(select(Transcript).where(Transcript.lecture_id == lecture_id)).first()
    if transcript:
        session.delete(transcript)
    for section in session.exec(select(Section).where(Section.lecture_id == lecture_id)).all():
        session.delete(section)
    for quiz_item in session.exec(select(QuizItem).where(QuizItem.lecture_id == lecture_id)).all():
        session.delete(quiz_item)
    for event in session.exec(select(ProcessingEvent).where(ProcessingEvent.lecture_id == lecture_id)).all():
        session.delete(event)
    session.delete(lecture)
    session.commit()
    return DeleteResponse(deleted=True)
