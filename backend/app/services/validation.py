from __future__ import annotations

from pydantic import BaseModel, ValidationError

from ..schemas import QuizItemGeneration, SectionGeneration


class GenerationPayload(BaseModel):
    sections: list[SectionGeneration]
    quiz_items: list[QuizItemGeneration]


def validate_generation_payload(payload: dict) -> GenerationPayload:
    return GenerationPayload.model_validate(payload)


def validation_error_text(exc: ValidationError) -> str:
    return exc.json()

