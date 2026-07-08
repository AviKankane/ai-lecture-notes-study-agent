from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class Chunk:
    text: str
    chunk_index: int
    word_count: int


def count_words(text: str) -> int:
    return len([token for token in text.split() if token.strip()])


def split_text_into_chunks(text: str, target_words: int = 300, min_words: int = 200, max_words: int = 400) -> list[Chunk]:
    words = text.split()
    if not words:
        return []

    if len(words) <= max_words:
        return [Chunk(text=" ".join(words), chunk_index=0, word_count=len(words))]

    chunks: list[Chunk] = []
    start = 0
    chunk_index = 0
    while start < len(words):
        end = min(start + target_words, len(words))
        remaining = len(words) - end
        if 0 < remaining < min_words:
            end = len(words)
        end = min(max(start + min_words, end), min(start + max_words, len(words)))
        chunk_words = words[start:end]
        chunks.append(Chunk(text=" ".join(chunk_words), chunk_index=chunk_index, word_count=len(chunk_words)))
        start = end
        chunk_index += 1
    return chunks


def join_texts(texts: Iterable[str]) -> str:
    return "\n\n".join(text for text in texts if text.strip())

