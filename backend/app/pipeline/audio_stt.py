"""Audio transcription via faster-whisper, with clip duration reported.

The Whisper model is loaded lazily and cached (it is expensive to construct).
"""

from __future__ import annotations

import tempfile
import time
from typing import Any

from ..schemas import ExtractedDoc
from .base import ExtractionOutcome, InputFile

_MODEL_CACHE: dict[str, Any] = {}


def _get_model(size: str) -> Any:
    if size in _MODEL_CACHE:
        return _MODEL_CACHE[size]
    from faster_whisper import WhisperModel  # type: ignore

    model = WhisperModel(size, device="cpu", compute_type="int8")
    _MODEL_CACHE[size] = model
    return model


def _transcribe_sync(data: bytes, suffix: str, model_size: str) -> tuple[str, float]:
    model = _get_model(model_size)
    with tempfile.NamedTemporaryFile(suffix=suffix or ".audio", delete=True) as tmp:
        tmp.write(data)
        tmp.flush()
        segments, info = model.transcribe(tmp.name, beam_size=1)
        text = " ".join(seg.text.strip() for seg in segments).strip()
    duration = float(getattr(info, "duration", 0.0) or 0.0)
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
