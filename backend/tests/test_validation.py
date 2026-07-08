import pytest
from pydantic import ValidationError

from app.services.validation import validate_generation_payload


def test_validate_generation_payload_success():
    payload = {
        "sections": [{"title": "Intro", "text": "Hello world", "summary": "Short summary"}],
        "quiz_items": [
            {
                "question": "What is this?",
                "options": ["A", "B"],
                "correct_answer": "A",
                "explanation": "Because it is A",
            }
        ],
    }
    validated = validate_generation_payload(payload)
    assert validated.sections[0].title == "Intro"


def test_validate_generation_payload_failure():
    payload = {"sections": [], "quiz_items": [{"question": "Q", "options": [], "correct_answer": "", "explanation": ""}]}
    with pytest.raises(ValidationError):
        validate_generation_payload(payload)
