from __future__ import annotations

import json
from typing import Any, Callable

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from ..config import get_settings


def is_quota_error(exc: Exception) -> bool:
    """A quota/rate-limit failure that another key might not have."""
    text = str(exc)
    return "429" in text or "RESOURCE_EXHAUSTED" in text or "quota" in text.lower()


class AllKeysExhaustedError(RuntimeError):
    pass


# Retry transient failures per key, but do NOT waste retries on quota errors —
# those propagate immediately so the caller can fail over to the next key.
_per_key_retry = retry(
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(3),
    retry=retry_if_exception(lambda exc: not is_quota_error(exc)),
    reraise=True,
)


class GeminiClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._clients: dict[str, Any] = {}

    def _keys(self) -> list[str]:
        keys = self.settings.gemini_api_keys
        if not keys:
            raise RuntimeError("GEMINI_API_KEY is not set")
        return keys

    def _client_for(self, key: str):
        if key not in self._clients:
            from google import genai

            self._clients[key] = genai.Client(api_key=key)
        return self._clients[key]

    @_per_key_retry
    def _attempt(self, key: str, call: Callable[[Any], Any]) -> Any:
        return call(self._client_for(key))

    def _run_with_failover(self, call: Callable[[Any], Any]) -> Any:
        """Try each configured key in order. On a quota/rate-limit error, roll over
        to the next key; on the last key (or a non-quota error) the error is raised."""
        keys = self._keys()
        last_exc: Exception | None = None
        for index, key in enumerate(keys):
            try:
                return self._attempt(key, call)
            except Exception as exc:  # noqa: BLE001 - we classify below
                last_exc = exc
                if is_quota_error(exc) and index < len(keys) - 1:
                    continue
                if is_quota_error(exc):
                    raise AllKeysExhaustedError(
                        f"All {len(keys)} Gemini API key(s) are rate-limited. Last error: {exc}"
                    ) from exc
                raise
        assert last_exc is not None
        raise last_exc

    def generate_json(self, prompt: str) -> dict[str, Any]:
        def call(client) -> dict[str, Any]:
            response = client.models.generate_content(
                model=self.settings.gemini_model,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            text = getattr(response, "text", None)
            if not text:
                raise RuntimeError("Gemini returned an empty response")
            return json.loads(text)

        return self._run_with_failover(call)

    def generate_text(self, prompt: str) -> str:
        def call(client) -> str:
            response = client.models.generate_content(
                model=self.settings.gemini_model,
                contents=prompt,
            )
            text = getattr(response, "text", None)
            if not text:
                raise RuntimeError("Gemini returned an empty response")
            return text.strip()

        return self._run_with_failover(call)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        def call(client) -> list[list[float]]:
            vectors: list[list[float]] = []
            for text in texts:
                response = client.models.embed_content(
                    model=self.settings.gemini_embedding_model,
                    contents=text,
                )
                embeddings = getattr(response, "embeddings", None)
                if not embeddings:
                    raise RuntimeError("Gemini returned empty embeddings")
                vectors.append(list(embeddings[0].values))
            return vectors

        return self._run_with_failover(call)
