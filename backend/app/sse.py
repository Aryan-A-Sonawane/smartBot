"""Server-Sent Events helpers.

Every event is encoded as a single SSE frame ``data: {json}\\n\\n`` exactly as
``frontend/src/lib/api.ts`` expects. The typed factory functions below are the
only place event JSON is constructed, keeping the wire contract in one spot.
"""

from __future__ import annotations

import json
from typing import Any

from .schemas import CostInfo, ExtractedDoc, TraceStep


def frame(payload: dict[str, Any]) -> str:
    """Encode a payload dict as one SSE frame."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def plan_event(steps: list[TraceStep]) -> str:
    return frame({"type": "plan", "steps": [s.model_dump(by_alias=True) for s in steps]})


def step_event(step: TraceStep) -> str:
    return frame({"type": "step", "step": step.model_dump(by_alias=True)})


def extracted_event(docs: list[ExtractedDoc]) -> str:
    return frame(
        {"type": "extracted", "docs": [d.model_dump(by_alias=True) for d in docs]}
    )


def cost_estimate_event(cost: CostInfo) -> str:
    return frame({"type": "cost_estimate", "cost": cost.model_dump(by_alias=True)})


def cost_actual_event(cost: CostInfo) -> str:
    return frame({"type": "cost_actual", "cost": cost.model_dump(by_alias=True)})


def token_event(text: str) -> str:
    return frame({"type": "token", "text": text})


def clarify_event(question: str) -> str:
    return frame({"type": "clarify", "question": question})


def error_event(message: str) -> str:
    return frame({"type": "error", "message": message})


def done_event() -> str:
    return frame({"type": "done"})
