from __future__ import annotations

from typing import Optional, TypedDict


class LectureGraphState(TypedDict, total=False):
    lecture_id: int
    audio_path: str
    transcript_text: str
    segments: list[dict]
    word_count: int
    duration_seconds: Optional[float]
    sections: list[dict]
    quiz_items: list[dict]
    error: Optional[str]
    retry_count: int
    current_step: str

