"""Parallel extraction dispatcher.

Routes each uploaded file to the right extractor by MIME/extension and runs
them all concurrently with ``asyncio.gather``. A failure in one file does not
abort the others (graceful partial results).
"""

from __future__ import annotations

import asyncio

from ..gemini_client import GeminiClient
from .audio_stt import extract_audio
from .base import ExtractionOutcome, InputFile, kind_for_mime
from .image_ocr import extract_image
from .pdf import extract_pdf


async def _route(file: InputFile, gemini: GeminiClient, whisper_model: str) -> ExtractionOutcome:
    kind = kind_for_mime(file.filename, file.content_type)
    try:
        if kind == "image":
            return await extract_image(file, gemini)
        if kind == "pdf":
            return await extract_pdf(file)
        if kind == "audio":
            return await extract_audio(file, whisper_model)
        # Unknown type: try to read as UTF-8 text, else flag unsupported.
        try:
            text = file.data.decode("utf-8").strip()
        except Exception:
            text = ""
        if text:
            from ..schemas import ExtractedDoc

            return ExtractionOutcome(
                doc=ExtractedDoc(source=file.filename, kind="other", content=text),
                tool="answer",
            )
        return ExtractionOutcome(
            doc=None,
            tool="answer",
            ok=False,
            error=f"Unsupported file type for '{file.filename}'.",
        )
    except Exception as exc:  # last-resort guard for graceful degradation
        return ExtractionOutcome(
            doc=None,
            tool="answer",
            ok=False,
            error=f"Extraction error for '{file.filename}': {exc}",
        )


async def extract_all(
    files: list[InputFile], gemini: GeminiClient, whisper_model: str
) -> list[ExtractionOutcome]:
    """Extract every file concurrently, preserving input order."""
    if not files:
        return []
    return list(
        await asyncio.gather(*(_route(f, gemini, whisper_model) for f in files))
    )
