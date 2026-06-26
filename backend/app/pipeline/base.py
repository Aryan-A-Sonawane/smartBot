"""Shared types for the extraction pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..schemas import ExtractedDoc, ToolName


@dataclass
class InputFile:
    """A user-uploaded file held in memory."""

    filename: str
    content_type: str
    data: bytes

    @property
    def size(self) -> int:
        return len(self.data)


@dataclass
class ExtractionOutcome:
    """Result of extracting one input, with timing and graceful error info."""

    doc: ExtractedDoc | None
    tool: ToolName
    duration_ms: int = 0
    ok: bool = True
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def kind_for_mime(filename: str, content_type: str) -> str:
    """Classify an upload into image | pdf | audio | other."""
    ct = (content_type or "").lower()
    name = (filename or "").lower()
    if ct.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff")):
        return "image"
    if ct == "application/pdf" or name.endswith(".pdf"):
        return "pdf"
    if ct.startswith("audio/") or name.endswith((".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac")):
        return "audio"
    return "other"


def tool_for_kind(kind: str) -> ToolName:
    return {
        "image": "image_ocr",
        "pdf": "pdf_extract",
        "audio": "audio_transcribe",
    }.get(kind, "answer")  # type: ignore[return-value]
