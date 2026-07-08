from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT_DIR / ".env"), extra="ignore")

    gemini_api_key: str = Field(default="")
    gemini_api_key_2: str = Field(default="")
    gemini_model: str = Field(default="gemini-3.5-flash")
    gemini_embedding_model: str = Field(default="gemini-embedding-2")
    database_url: str = Field(default="sqlite:///./data/app.db")
    chroma_path: str = Field(default="./data/chroma")
    upload_dir: str = Field(default="./data/uploads")
    whisper_model: str = Field(default="base")
    backend_cors_origins: str = Field(default="http://localhost:3000")

    def model_post_init(self, __context) -> None:
        self.database_url = _resolve_database_url(self.database_url)
        self.chroma_path = str(_resolve_repo_path(self.chroma_path))
        self.upload_dir = str(_resolve_repo_path(self.upload_dir))

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def gemini_api_keys(self) -> list[str]:
        """All configured Gemini keys, in priority order, de-duplicated.
        `GEMINI_API_KEY` may itself be a comma-separated list; `GEMINI_API_KEY_2`
        is appended for convenience. Used for automatic failover on quota limits."""
        raw = [k.strip() for k in self.gemini_api_key.split(",")]
        raw.append(self.gemini_api_key_2.strip())
        keys: list[str] = []
        for key in raw:
            if key and key not in keys:
                keys.append(key)
        return keys


def _resolve_repo_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (ROOT_DIR / path).resolve()


def _resolve_database_url(value: str) -> str:
    prefix = "sqlite:///"
    if value.startswith(prefix):
        raw_path = value[len(prefix):]
        if raw_path.startswith("/"):
            return value
        resolved = (ROOT_DIR / raw_path).resolve()
        return f"{prefix}/{resolved}"
    return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
