"""LLM-based intent + relevance router.

Keyword rules are brittle ("summarize the sentiment of…" is a *sentiment* task,
not a summary; "how was that calculated?" is a follow-up question, not a new
analysis). When a Gemini key is available we let the model decide, with the full
conversation's documents in view: which task the user wants, whether we need to
ask a clarifying question, and which document(s) this message actually refers to.

Offline (no key) the caller falls back to the deterministic keyword planner, so
behaviour stays predictable and unit-testable.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ..gemini_client import GeminiClient, LLMUnavailable
from ..schemas import ExtractedDoc
from .planner import Intent

_INTENTS = ("summarize", "sentiment", "code_explain", "structured_extract", "answer")

_SYSTEM = (
    "You are the router for a multimodal assistant. Read the user's latest message and the "
    "documents available in this conversation, then decide how to handle it. "
    "Respond with ONLY a compact JSON object — no prose, no code fences."
)


@dataclass
class Route:
    intent: Intent
    needs_clarification: bool
    clarify_question: str
    relevant_sources: list[str] | None  # exact doc source names, or None = use all


def _parse_json(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


async def route_intent(
    query: str, file_docs: list[ExtractedDoc], gemini: GeminiClient
) -> Route | None:
    """Ask the LLM to route the request. Returns None when unavailable/invalid so
    the caller can fall back to the deterministic planner."""
    if not gemini.configured:
        return None

    doc_index = [
        {"source": d.source, "kind": d.kind, "preview": d.content[:200]} for d in file_docs
    ]
    prompt = (
        "Fill this JSON:\n"
        '- "intent": one of ["summarize","sentiment","code_explain","structured_extract","answer"] '
        "— the task the user actually wants. Summarising sentiments is \"sentiment\". A meta-question "
        "about a previous reply (e.g. \"how was that calculated?\") is \"answer\".\n"
        '- "needs_clarification": true ONLY if you genuinely cannot tell what to do, or which document '
        "is meant; otherwise false.\n"
        '- "clarify_question": a short question — only when needs_clarification is true.\n'
        '- "relevant_sources": exact source name(s) of the document(s) this message refers to '
        "(both for a comparison, one for a single-document request). Use [] when no document is needed.\n\n"
        f"User message: {query!r}\n"
        f"Available documents (JSON): {json.dumps(doc_index, ensure_ascii=False)}\n\n"
        'Respond with only: {"intent":"...","needs_clarification":false,"clarify_question":"","relevant_sources":[]}'
    )
    try:
        res = await gemini.generate(prompt, system=_SYSTEM, temperature=0.0)
    except LLMUnavailable:
        return None

    data = _parse_json(res.text)
    if not data:
        return None
    intent = data.get("intent")
    if intent not in _INTENTS:
        return None  # unusable — fall back to the keyword planner

    valid = {d.source for d in file_docs}
    raw_sources = data.get("relevant_sources")
    if isinstance(raw_sources, list):
        relevant: list[str] | None = [s for s in raw_sources if s in valid]
        if not relevant:
            relevant = None  # none matched -> use all rather than starve the tools
    else:
        relevant = None

    return Route(
        intent=intent,  # type: ignore[arg-type]
        needs_clarification=bool(data.get("needs_clarification")),
        clarify_question=str(data.get("clarify_question") or "").strip(),
        relevant_sources=relevant,
    )
