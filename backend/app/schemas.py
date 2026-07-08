from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .models import LectureStatus


class SectionGeneration(BaseModel):
    title: str
    text: str
    summary: str
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None


class QuizItemGeneration(BaseModel):
    question: str
    options: list[str] = Field(min_length=2)
    correct_answer: str
    explanation: str


class ChapterResponse(BaseModel):
    id: int
    subject_id: int
    name: str


class SubjectResponse(BaseModel):
    id: int
    name: str
    chapters: list[ChapterResponse] = Field(default_factory=list)
    lecture_count: int = 0


class SubjectCreate(BaseModel):
    name: str


class ChapterCreate(BaseModel):
    name: str


class YoutubeIngestRequest(BaseModel):
    url: str
    subject: Optional[str] = None
    chapter: Optional[str] = None
    subsection: Optional[str] = None


class LectureListItem(BaseModel):
    id: int
    title: str
    original_filename: str
    status: LectureStatus
    word_count: Optional[int]
    duration_seconds: Optional[float]
    error_message: Optional[str]
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    chapter_id: Optional[int] = None
    chapter_name: Optional[str] = None
    subsection: Optional[str] = None
    source_type: str = "upload"
    source_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TranscriptResponse(BaseModel):
    id: int
    text: str
    segments_json: list[dict]


class SectionResponse(BaseModel):
    id: int
    order_index: int
    title: str
    start_seconds: Optional[float]
    end_seconds: Optional[float]
    text: str
    summary: str


class QuizItemResponse(BaseModel):
    id: int
    question: str
    options_json: list[str]
    correct_answer: str
    explanation: str


class ProcessingEventResponse(BaseModel):
    id: int
    step: str
    status: str
    message: Optional[str]
    created_at: datetime


class LectureDetailResponse(BaseModel):
    id: int
    title: str
    original_filename: str
    status: LectureStatus
    word_count: Optional[int]
    duration_seconds: Optional[float]
    error_message: Optional[str]
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    chapter_id: Optional[int] = None
    chapter_name: Optional[str] = None
    subsection: Optional[str] = None
    source_type: str = "upload"
    source_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    transcript: Optional[TranscriptResponse]
    sections: list[SectionResponse]
    quiz_items: list[QuizItemResponse]
    events: list[ProcessingEventResponse]


class UploadResponse(BaseModel):
    lecture_id: int
    status: LectureStatus


class RetryResponse(BaseModel):
    lecture_id: int
    status: LectureStatus


class DeleteResponse(BaseModel):
    deleted: bool


class ChatRequest(BaseModel):
    question: str
    lecture_ids: list[int] = Field(default_factory=list)
    session_id: Optional[int] = None


class Citation(BaseModel):
    lecture_id: int
    lecture_title: str
    section_id: Optional[int]
    section_title: Optional[str]
    snippet: str
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    session_id: Optional[int] = None


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    citations: list[Citation] = Field(default_factory=list)
    created_at: datetime


class ChatSessionListItem(BaseModel):
    id: int
    title: str
    lecture_ids: list[int] = Field(default_factory=list)
    message_count: int
    created_at: datetime
    updated_at: datetime


class ChatSessionDetail(BaseModel):
    id: int
    title: str
    lecture_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse] = Field(default_factory=list)


class DeleteSessionResponse(BaseModel):
    deleted: bool

