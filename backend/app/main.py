from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, health, lectures, subjects
from .config import get_settings
from .database import init_db


def create_app() -> FastAPI:
    settings = get_settings()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="AI Lecture Notes & Study Agent")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(subjects.router)
    app.include_router(lectures.router)
    app.include_router(chat.router)

    @app.on_event("startup")
    def on_startup():
        init_db()

    return app


app = create_app()

