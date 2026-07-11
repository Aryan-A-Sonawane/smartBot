"""Pydantic models shared across the agent.

The field names that cross the wire to the frontend use camelCase aliases so
the SSE payloads match ``frontend/src/lib/types.ts`` exactly. We serialise with
``by_alias=True`` everywhere an event is sent.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Machine names of the tools/stages the agent can chain. Must match the frontend.
# "understand" and "refine" are orchestration stages (not tools) surfaced in the
# trace so the full pipeline is visible.
ToolName = Literal[
    "understand",
    "image_ocr",
    "pdf_extract",
    "audio_transcribe",
    "youtube_transcript",
    "url_fetch",
    "summarize",
    "sentiment",
    "code_explain",
    "structured_extract",
    "answer",
    "refine",
    "compose",
]

AttachmentKind = Literal["image", "pdf", "audio", "other"]


class StepStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"


class _CamelModel(BaseModel):
    """Base that allows population by field name but serialises by alias."""

    model_config = ConfigDict(populate_by_name=True)


class TraceStep(_CamelModel):
    """One step in the agent's tool chain — powers the trace list and graph."""

    id: str
    tool: ToolName
    label: str
    rationale: str | None = None  # static "why this tool" hint
    detail: str | None = None  # runtime "what actually happened" (engine, fallback, result)
    status: StepStatus = StepStatus.pending
    duration_ms: int | None = Field(default=None, alias="durationMs")


class ExtractedDoc(_CamelModel):
    """Text pulled from a single input — shown in the Extracted Text panel."""

    source: str
    kind: str  # AttachmentKind | "text"
    content: str
    ocr_confidence: float | None = Field(default=None, alias="ocrConfidence")


class CostInfo(_CamelModel):
    """Cost estimate vs. actuals — shown in the Cost panel."""

    estimated_usd: float | None = Field(default=None, alias="estimatedUsd")
    actual_usd: float | None = Field(default=None, alias="actualUsd")
    input_tokens: int | None = Field(default=None, alias="inputTokens")
    output_tokens: int | None = Field(default=None, alias="outputTokens")
    model: str | None = None
