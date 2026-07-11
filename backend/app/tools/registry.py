"""Tool registry — maps tool names to their async ``run`` callables.

This is the single injection point the executor uses, keeping the agent core
decoupled from individual tool implementations (dependency inversion).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from ..schemas import ToolName
from . import (
    answer,
    code_explain,
    sentiment,
    structured_extract,
    summarize,
    urlfetch,
    youtube,
)
from .base import ToolContext, ToolResult

ToolFn = Callable[[ToolContext], Awaitable[ToolResult]]

# Human-readable labels + one-line "why this tool" rationales for the trace.
TOOL_META: dict[str, dict[str, str]] = {
    "understand": {"label": "Understand request", "rationale": "Tokenize, detect intent, and check the request is answerable."},
    "image_ocr": {"label": "OCR image", "rationale": "Image attached — extract text via OCR."},
    "pdf_extract": {"label": "Parse PDF", "rationale": "PDF attached — extract text (OCR fallback if scanned)."},
    "audio_transcribe": {"label": "Transcribe audio", "rationale": "Audio attached — run speech-to-text."},
    "youtube_transcript": {"label": "Fetch YouTube transcript", "rationale": "YouTube link detected — fetch its transcript."},
    "url_fetch": {"label": "Fetch URL", "rationale": "Link detected — fetch and read the page."},
    "summarize": {"label": "Summarize", "rationale": "Produce 1-line + 3 bullets + 5-sentence summary."},
    "sentiment": {"label": "Analyze sentiment", "rationale": "Label + confidence + one-line justification."},
    "code_explain": {"label": "Explain code", "rationale": "Explain, flag bugs, note time complexity."},
    "structured_extract": {"label": "Extract structured data", "rationale": "Pull action items / tables / entities."},
    "answer": {"label": "Answer", "rationale": "Answer using the combined context."},
    "refine": {"label": "Refine / self-check", "rationale": "Critic validates the output format and repairs it if needed."},
    "compose": {"label": "Compose response", "rationale": "Format the final text-only answer."},
}


class ToolRegistry:
    def __init__(self, tools: dict[str, ToolFn]) -> None:
        self._tools = tools

    def get(self, name: ToolName) -> ToolFn | None:
        return self._tools.get(name)

    def meta(self, name: ToolName) -> dict[str, str]:
        return TOOL_META.get(name, {"label": name, "rationale": ""})

    def __contains__(self, name: str) -> bool:
        return name in self._tools


def build_registry() -> ToolRegistry:
    """Construct the registry of executable (LLM/IO) tools.

    Extraction tools (image_ocr/pdf_extract/audio_transcribe) run in the
    pipeline rather than here, so they are represented in the trace but not as
    executable registry entries.
    """
    return ToolRegistry(
        {
            "summarize": summarize.run,
            "sentiment": sentiment.run,
            "code_explain": code_explain.run,
            "structured_extract": structured_extract.run,
            "answer": answer.run,
            "youtube_transcript": youtube.run,
            "url_fetch": urlfetch.run,
        }
    )
