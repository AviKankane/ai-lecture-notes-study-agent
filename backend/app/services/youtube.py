from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from ..database import ensure_ffmpeg_on_path

_YOUTUBE_RE = re.compile(
    r"(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)", re.IGNORECASE
)


class YoutubeDownloadError(RuntimeError):
    pass


def is_youtube_url(url: str) -> bool:
    return bool(_YOUTUBE_RE.search(url or ""))


def download_audio(url: str, upload_dir: str) -> dict:
    """Download a YouTube video's audio track as mp3 into `upload_dir`.
    Returns {"audio_path", "title", "duration_seconds"}."""
    if not is_youtube_url(url):
        raise YoutubeDownloadError("That does not look like a YouTube link.")

    ensure_ffmpeg_on_path()  # yt-dlp needs ffmpeg to extract/convert audio
    try:
        import yt_dlp
    except ImportError as exc:  # pragma: no cover
        raise YoutubeDownloadError("yt-dlp is not installed on the server.") from exc

    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    base = uuid4().hex
    outtmpl = str(Path(upload_dir) / f"{base}.%(ext)s")

    options = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ],
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as exc:  # yt_dlp raises a variety of error types
        raise YoutubeDownloadError(f"Could not download audio: {exc}") from exc

    audio_path = Path(upload_dir) / f"{base}.mp3"
    if not audio_path.exists():
        raise YoutubeDownloadError("Audio extraction finished but no mp3 was produced.")

    return {
        "audio_path": str(audio_path),
        "title": (info.get("title") or "YouTube lecture").strip(),
        "duration_seconds": info.get("duration"),
    }
