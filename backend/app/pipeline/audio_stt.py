"""Audio transcription via faster-whisper, with clip duration reported.

The Whisper model is loaded lazily and cached (it is expensive to construct).
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from typing import Any

from ..schemas import ExtractedDoc
from .base import ExtractionOutcome, InputFile

_MODEL_CACHE: dict[str, Any] = {}


def _base_dir() -> Path:
    """Writable base for all model + scratch files.

    We deliberately avoid the OS defaults (``~/.cache`` for models, ``C:\\Temp``
    for scratch): on Windows those can be owned by another (e.g. WSL) user and
    deny access, surfacing as ``[WinError 5]`` / ``[Errno 13] Permission
    denied``. ``WHISPER_CACHE_DIR`` overrides; otherwise everything lives under
    ``backend/.models`` — same drive as the app, always writable."""
    override = os.environ.get("WHISPER_CACHE_DIR", "").strip()
    return Path(override) if override else Path(__file__).resolve().parents[2] / ".models"


def _cache_root() -> str:
    """Guaranteed-writable directory for the Whisper model files."""
    base = _base_dir()
    whisper_dir = base / "whisper"
    whisper_dir.mkdir(parents=True, exist_ok=True)
    # Redirect any incidental HuggingFace Hub cache to the same writable base,
    # and quiet the Windows "no symlink support" warning (it falls back to copy).
    os.environ.setdefault("HF_HOME", str(base / "hf"))
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    return str(whisper_dir)


def _tmp_dir() -> str:
    """Writable directory for the short-lived uploaded-audio scratch file."""
    d = _base_dir() / "tmp"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def _get_model(size: str) -> Any:
    if size in _MODEL_CACHE:
        return _MODEL_CACHE[size]
    download_root = _cache_root()
    from faster_whisper import WhisperModel  # type: ignore

    model = WhisperModel(
        size, device="cpu", compute_type="int8", download_root=download_root
    )
    _MODEL_CACHE[size] = model
    return model


def _transcribe_sync(data: bytes, suffix: str, model_size: str) -> tuple[str, float]:
    model = _get_model(model_size)
    # Write to a project-owned dir and CLOSE the handle before Whisper opens it:
    # Windows refuses a second open of a still-open NamedTemporaryFile by path.
    fd, path = tempfile.mkstemp(suffix=suffix or ".audio", dir=_tmp_dir())
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        segments, info = model.transcribe(path, beam_size=1)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        duration = float(getattr(info, "duration", 0.0) or 0.0)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    return text, duration


def _fmt_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    return f"{seconds // 60}m {seconds % 60:02d}s"


async def extract_audio(file: InputFile, model_size: str) -> ExtractionOutcome:
    import asyncio
    import os

    started = time.time()
    suffix = os.path.splitext(file.filename)[1] or ".mp3"
    try:
        text, duration = await asyncio.to_thread(
            _transcribe_sync, file.data, suffix, model_size
        )
    except Exception as exc:
        return ExtractionOutcome(
            doc=None,
            tool="audio_transcribe",
            duration_ms=int((time.time() - started) * 1000),
            ok=False,
            error=f"Transcription failed: {exc}",
        )
    elapsed = int((time.time() - started) * 1000)
    if not text:
        return ExtractionOutcome(
            doc=None,
            tool="audio_transcribe",
            duration_ms=elapsed,
            ok=False,
            error="Audio produced no transcript.",
        )
    doc = ExtractedDoc(
        source=file.filename,
        kind="audio",
        content=f"(audio duration: {_fmt_duration(duration)})\n{text}",
    )
    return ExtractionOutcome(
        doc=doc,
        tool="audio_transcribe",
        duration_ms=elapsed,
        metadata={"duration_sec": duration, "duration_human": _fmt_duration(duration)},
    )
