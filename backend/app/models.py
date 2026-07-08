from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, JSON, Text
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LectureStatus(str, Enum):
    QUEUED = "queued"
    TRANSCRIBING = "transcribing"
    PROCESSING = "processing"
    INDEXING = "indexing"
    DONE = "done"
    FAILED = "failed"


class Subject(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)


class Chapter(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    subject_id: int = Field(foreign_key="subject.id", index=True)
    name: str
    created_at: datetime = Field(default_factory=utcnow)


class Lecture(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    original_filename: str
    audio_path: str
    status: LectureStatus = Field(default=LectureStatus.QUEUED)
    word_count: int | None = None
    duration_seconds: float | None = None
    error_message: str | None = None
    # Organization: Subject -> Chapter -> Subsection
    subject_id: int | None = Field(default=None, foreign_key="subject.id")
    chapter_id: int | None = Field(default=None, foreign_key="chapter.id")
    subsection: str | None = None
    # Source: an uploaded file or a YouTube link
    source_type: str = Field(default="upload")  # "upload" | "youtube"
    source_url: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

class Transcript(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    lecture_id: int = Field(foreign_key="lecture.id", unique=True)
    text: str = Field(sa_column=Column(Text, nullable=False))
    segments_json: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class Section(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    lecture_id: int = Field(foreign_key="lecture.id")
    order_index: int
    title: str
    start_seconds: float | None = None
    end_seconds: float | None = None
    text: str = Field(sa_column=Column(Text, nullable=False))
    summary: str = Field(sa_column=Column(Text, nullable=False))


class QuizItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    lecture_id: int = Field(foreign_key="lecture.id")
    question: str
    options_json: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    correct_answer: str
    explanation: str = Field(sa_column=Column(Text, nullable=False))


class ProcessingEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    lecture_id: int = Field(foreign_key="lecture.id")
    step: str
    status: str
    message: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class ChatSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    lecture_ids_json: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ChatMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chatsession.id")
    role: str  # "user" | "assistant"
    content: str = Field(sa_column=Column(Text, nullable=False))
    citations_json: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)
