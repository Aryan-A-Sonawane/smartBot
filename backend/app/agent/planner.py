"""The planner: intent detection, the mandatory clarify-gate, model routing,
and building the minimal ordered tool chain.

The planner is deterministic (regex + rules) so behaviour is predictable and
unit-testable without an API key. The LLM does the heavy lifting inside tools.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from ..schemas import ExtractedDoc, StepStatus, ToolName, TraceStep
from ..tools.registry import TOOL_META
from ..utils import find_all_urls, is_youtube

Intent = Literal["summarize", "sentiment", "code_explain", "structured_extract", "answer"]

_INTENT_KEYWORDS = re.compile(
    r"(summar|tl;?dr|gist|recap|sentiment|tone|feel|positive|negative|emotion|"
    r"explain|bug|complexity|code|function|refactor|action item|extract|table|"
    r"entit|key points|fields|transcrib|compare|same topic)",
    re.IGNORECASE,
)


@dataclass
class Plan:
    steps: list[TraceStep]
    intent: Intent
    prefer_pro: bool = False
    needs_clarification: bool = False
    clarify_question: str = ""
    notes: list[str] = field(default_factory=list)


def detect_intent(query: str) -> Intent:
    q = (query or "").lower()
    if re.search(r"(summar|tl;?dr|gist|recap)", q):
        return "summarize"
    if re.search(r"(sentiment|tone|feel|positive|negative|emotion)", q):
        return "sentiment"
    if re.search(r"(explain|bug|complexity|\bcode\b|function|refactor)", q):
        return "code_explain"
    if re.search(r"(action item|extract|table|entit|key points|fields)", q):
        return "structured_extract"
    return "answer"


def _is_actionable(query: str) -> bool:
    q = (query or "").strip()
    if not q:
        return False
    if "?" in q:
        return True
    if _INTENT_KEYWORDS.search(q):
        return True
    return len(q.split()) >= 3


def _step(idx: int, tool: ToolName) -> TraceStep:
    meta = TOOL_META.get(tool, {"label": tool, "rationale": ""})
    return TraceStep(
        id=f"step-{idx}",
        tool=tool,
        label=meta["label"],
        rationale=meta["rationale"],
        status=StepStatus.pending,
    )


def plan_request(query: str, docs: list[ExtractedDoc], kinds_present: set[str]) -> Plan:
    """Build the plan from the query + already-extracted documents."""
    file_docs = [d for d in docs if d.source != "Text query"]
    has_files = len(file_docs) > 0
    has_query = bool((query or "").strip())

    # ---- Mandatory follow-up rule: don't guess on ambiguous input ----
    if has_files and not has_query:
        return Plan(
            steps=[],
            intent="answer",
            needs_clarification=True,
            clarify_question=(
                "I've received your file(s). What would you like me to do — "
                "**summarize**, **analyze sentiment**, **explain code**, or "
                "**extract the text**?"
            ),
        )
    if not has_query and not has_files:
        return Plan(
            steps=[],
            intent="answer",
            needs_clarification=True,
            clarify_question="What would you like me to help you with?",
        )
    if has_files and not _is_actionable(query):
        return Plan(
            steps=[],
            intent="answer",
            needs_clarification=True,
            clarify_question=(
                "I have your file(s) and your note, but I'm not sure what task you "
                "want. Could you clarify — for example summarize, analyze, or extract?"
            ),
        )

    # ---- Build the minimal ordered tool chain ----
    steps: list[TraceStep] = []
    idx = 0
    if "image" in kinds_present:
        steps.append(_step(idx, "image_ocr"))
        idx += 1
    if "pdf" in kinds_present:
        steps.append(_step(idx, "pdf_extract"))
        idx += 1
    if "audio" in kinds_present:
        steps.append(_step(idx, "audio_transcribe"))
        idx += 1

    # URL detection across query + extracted content (cross-input references).
    haystack = (query or "") + "\n" + "\n".join(d.content for d in docs)
    urls = find_all_urls(haystack)
    if any(is_youtube(u) for u in urls):
        steps.append(_step(idx, "youtube_transcript"))
        idx += 1
    elif urls:
        steps.append(_step(idx, "url_fetch"))
        idx += 1

    intent = detect_intent(query)
    steps.append(_step(idx, intent))
    idx += 1
    steps.append(_step(idx, "compose"))

    # Confidence-aware routing: cross-input / heavy reasoning -> pro model.
    prefer_pro = len(file_docs) >= 2 or (intent == "answer" and len(file_docs) >= 1)

    return Plan(steps=steps, intent=intent, prefer_pro=prefer_pro)
