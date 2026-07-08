from __future__ import annotations

from ..services.gemini_client import GeminiClient


def embed_texts(texts: list[str]) -> list[list[float]]:
    return GeminiClient().embed_texts(texts)

