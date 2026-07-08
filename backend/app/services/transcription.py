from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import get_settings


class WhisperTranscriber:
    def __init__(self) -> None:
        self._model = None
        self._settings = get_settings()

    def _load_model(self):
        if self._model is None:
            import whisper

            self._model = whisper.load_model(self._settings.whisper_model)
        return self._model

    def transcribe(self, audio_path: str) -> dict[str, Any]:
        model = self._load_model()
        result = model.transcribe(str(Path(audio_path)))
        segments = result.get("segments", [])
        return {
            "text": result.get("text", "").strip(),
            "segments": segments,
            "duration_seconds": _resolve_duration(result, segments),
        }


def _resolve_duration(result: dict[str, Any], segments: list[dict]) -> float | None:
    """Whisper does not always populate a top-level `duration`; fall back to the
    end timestamp of the last transcribed segment so the UI can show a real value."""
    duration = result.get("duration")
    if duration is not None:
        return float(duration)
    if segments:
        last_end = segments[-1].get("end")
        if last_end is not None:
            return float(last_end)
    return None

