import os
import shutil
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from .config import get_settings


settings = get_settings()
engine = create_engine(settings.database_url, echo=False, connect_args={"check_same_thread": False})

# Columns added to `lecture` after the table first shipped. SQLModel.create_all()
# only creates missing tables, never alters existing ones, so we add them by hand.
_LECTURE_ADDED_COLUMNS = {
    "subject_id": "INTEGER",
    "chapter_id": "INTEGER",
    "subsection": "TEXT",
    "source_type": "TEXT DEFAULT 'upload'",
    "source_url": "TEXT",
}


def ensure_ffmpeg_on_path() -> None:
    """Whisper and yt-dlp shell out to ffmpeg. When the server is started from a
    non-login shell, Homebrew's bin may be missing from PATH — add it if we can find it."""
    if shutil.which("ffmpeg"):
        return
    for candidate in ("/opt/homebrew/bin", "/usr/local/bin"):
        if Path(candidate, "ffmpeg").exists():
            os.environ["PATH"] = f"{candidate}{os.pathsep}{os.environ.get('PATH', '')}"
            return

# Statuses that mean "work was in flight". Because processing runs in an in-process
# background task, a server restart abandons anything mid-pipeline.
_STUCK_STATUSES = {"queued", "transcribing", "processing", "indexing"}


def init_db() -> None:
    ensure_ffmpeg_on_path()
    SQLModel.metadata.create_all(engine)
    _migrate_lecture_columns()
    _recover_stuck_lectures()
    _backfill_durations()


def _migrate_lecture_columns() -> None:
    with engine.begin() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(lecture)")}
        for column, ddl in _LECTURE_ADDED_COLUMNS.items():
            if column not in existing:
                conn.exec_driver_sql(f"ALTER TABLE lecture ADD COLUMN {column} {ddl}")


def _recover_stuck_lectures() -> None:
    """A restart abandons in-flight background jobs. Flip anything left mid-pipeline
    to FAILED with a clear message so the user can simply hit Retry."""
    from .models import Lecture, LectureStatus, ProcessingEvent, utcnow

    with Session(engine) as session:
        stuck = session.exec(select(Lecture)).all()
        changed = False
        for lecture in stuck:
            if lecture.status.value in _STUCK_STATUSES:
                lecture.status = LectureStatus.FAILED
                lecture.error_message = "Processing was interrupted by a server restart. Click Retry."
                lecture.updated_at = utcnow()
                session.add(lecture)
                session.add(
                    ProcessingEvent(
                        lecture_id=lecture.id,
                        step="recover",
                        status="error",
                        message="Interrupted by server restart",
                    )
                )
                changed = True
        if changed:
            session.commit()


def _backfill_durations() -> None:
    """Older lectures were saved before duration was computed; fill them in from the
    stored transcript segments so the dashboard shows real durations."""
    from .models import Lecture, Transcript, utcnow

    with Session(engine) as session:
        lectures = session.exec(select(Lecture).where(Lecture.duration_seconds.is_(None))).all()
        changed = False
        for lecture in lectures:
            transcript = session.exec(
                select(Transcript).where(Transcript.lecture_id == lecture.id)
            ).first()
            if transcript and transcript.segments_json:
                last_end = transcript.segments_json[-1].get("end")
                if last_end is not None:
                    lecture.duration_seconds = float(last_end)
                    lecture.updated_at = utcnow()
                    session.add(lecture)
                    changed = True
        if changed:
            session.commit()


def get_session():
    with Session(engine) as session:
        yield session

