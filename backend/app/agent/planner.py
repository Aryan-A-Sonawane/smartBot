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
from ..utils import estimate_tokens, find_all_urls, is_cross_input, is_youtube

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
    goal: str = ""
    notes: list[str] = field(default_factory=list)


# Plain-English description of what each intent will do — shown as the agent's
# understood goal so the user sees the intent was identified, not guessed.
_INTENT_GOAL: dict[Intent, str] = {
    "summarize": "summarise it (1-line + 3 bullets + 5-sentence summary)",
    "sentiment": "classify its sentiment (label + confidence + reason)",
    "code_explain": "explain the code, flag bugs, and give its time complexity",
    "structured_extract": "extract the requested structured items (e.g. action items)",
    "answer": "answer the question — grounded in the inputs, reasoning beyond them where the question needs it",
}


def describe_goal(docs: list[ExtractedDoc], intent: Intent) -> str:
    """A prompt-specific, one-line statement of the understood goal."""
    files = [d.source for d in docs if d.source != "Text query"]
    where = ""
    if files:
        shown = ", ".join(files[:3]) + ("…" if len(files) > 3 else "")
        where = f" using {shown}"
    return f"Intent **{intent}** — {_INTENT_GOAL.get(intent, 'help with the request')}{where}."


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


def _explicit_followup_task(query: str) -> Intent | None:
    """On a follow-up, only a clearly re-requested strict-format deliverable keeps
    its specialized tool; anything else is answered conversationally."""
    q = (query or "").lower()
    if re.search(r"summar|tl;?dr|recap|\bgist\b", q):
        return "summarize"
    if re.search(r"sentiment|\btone\b", q):
        return "sentiment"
    if re.search(r"action item|\bextract\b|entit|as a table|list (all|the)", q):
        return "structured_extract"
    return None


def _names_a_file(query: str, file_docs: list[ExtractedDoc]) -> bool:
    """Whether the query references one of the files by a distinctive token from
    its name, so we don't need to ask which one."""
    q = (query or "").lower()
    for d in file_docs:
        stem = d.source.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
        for tok in re.split(r"[\s._\-]+", stem):
            if len(tok) >= 3 and tok in q:
                return True
    return False


def _is_actionable(query: str) -> bool:
    q = (query or "").strip()
    if not q:
        return False
    if "?" in q:
        return True
    if _INTENT_KEYWORDS.search(q):
        return True
    return len(q.split()) >= 3


# Intents whose output has a strict format contract → get a critic refine stage.
_REFINED_INTENTS: set[Intent] = {"summarize", "sentiment", "code_explain", "structured_extract"}


def _step(idx: int, tool: ToolName, detail: str | None = None) -> TraceStep:
    meta = TOOL_META.get(tool, {"label": tool, "rationale": ""})
    return TraceStep(
        id=f"step-{idx}",
        tool=tool,
        label=meta["label"],
        rationale=meta["rationale"],
        detail=detail,
        status=StepStatus.pending,
    )


def _understand_step(query: str, docs: list[ExtractedDoc], intent: Intent, sufficient: bool) -> TraceStep:
    """The first stage: tokenize, detect intent, and run the clarify-gate — shown
    so the reasoning (not just the tool calls) is visible."""
    tokens = estimate_tokens((query or "") + " " + " ".join(d.content for d in docs))
    n_inputs = len([d for d in docs if d.source != "Text query"])
    if sufficient:
        detail = (
            f"~{tokens} tokens · rule-based intent: {intent} · "
            f"{n_inputs} input(s) · clarify-gate: sufficient"
        )
    else:
        detail = f"~{tokens} tokens · request ambiguous · clarify-gate: insufficient → asking a follow-up"
    return _step(0, "understand", detail=detail)


def plan_request(query: str, docs: list[ExtractedDoc], kinds_present: set[str]) -> Plan:
    """Build the plan from the query + already-extracted documents."""
    file_docs = [d for d in docs if d.source != "Text query"]
    has_files = len(file_docs) > 0
    has_query = bool((query or "").strip())

    # ---- Mandatory follow-up rule: don't guess on ambiguous input ----
    # The clarify path still shows the "understand" stage so the sufficiency
    # decision (info insufficient -> ask a follow-up) is visible in the trace.
    def _clarify(question: str, goal: str) -> Plan:
        return Plan(
            steps=[_understand_step(query, docs, "answer", sufficient=False)],
            intent="answer",
            needs_clarification=True,
            clarify_question=question,
            goal=goal,
        )

    if has_files and not has_query:
        return _clarify(
            "I've received your file(s). What would you like me to do — "
            "**summarize**, **analyze sentiment**, **explain code**, or "
            "**extract the text**?",
            "Ask what to do with the uploaded file(s) before acting.",
        )
    if not has_query and not has_files:
        return _clarify(
            "What would you like me to help you with?",
            "Ask what the user needs.",
        )
    if has_files and not _is_actionable(query):
        return _clarify(
            "I have your file(s) and your note, but I'm not sure what task you "
            "want. Could you clarify — for example summarize, analyze, or extract?",
            "Ask the user to clarify the task before acting.",
        )

    # ---- Resolve intent (query-only) ----
    intent = detect_intent(query)

    # ---- Disambiguation: don't guess which document a bare command means ----
    # On a follow-up (no new file) with several documents in context, a short
    # whole-document command ("explain", "summarize it") is ambiguous — ask which
    # file, unless the query already names one or spans them (compare/both/…).
    distinct_files = list(dict.fromkeys(d.source for d in file_docs))
    if (
        not kinds_present
        and len(distinct_files) >= 2
        and len((query or "").split()) <= 4
        and intent in {"summarize", "sentiment", "code_explain", "structured_extract"}
        and not is_cross_input(query)
        and not _names_a_file(query, file_docs)
    ):
        names = ", ".join(f"**{s}**" for s in distinct_files)
        return _clarify(
            f"You have a few files in this chat — which one should I use: {names}?",
            "Ask which file the request refers to (several are in context).",
        )

    # Follow-up turn: earlier docs are in memory but nothing new was uploaded
    # this turn. Answer the specific question conversationally instead of
    # re-running a rigid task tool that repeats its canned format regardless of
    # what was asked — unless the user explicitly re-requests such a deliverable.
    if not kinds_present and len(file_docs) > 0:
        intent = _explicit_followup_task(query) or "answer"

    return build_pipeline(query, docs, kinds_present, intent)


def clarify_plan(query: str, docs: list[ExtractedDoc], question: str,
                 goal: str = "Clarify the request before acting.") -> Plan:
    """A plan that stops to ask a follow-up, still showing the understand stage."""
    return Plan(
        steps=[_understand_step(query, docs, "answer", sufficient=False)],
        intent="answer",
        needs_clarification=True,
        clarify_question=question,
        goal=goal,
    )


def build_pipeline(query: str, docs: list[ExtractedDoc], kinds_present: set[str],
                   intent: Intent) -> Plan:
    """Build the full ordered pipeline for a resolved intent + context docs:
    understand -> extract -> (fetch) -> generate -> refine -> compose."""
    file_docs = [d for d in docs if d.source != "Text query"]
    steps: list[TraceStep] = [_understand_step(query, docs, intent, sufficient=True)]
    idx = 1
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

    steps.append(_step(idx, intent))
    idx += 1
    if intent in _REFINED_INTENTS:
        steps.append(_step(idx, "refine"))
        idx += 1
    steps.append(_step(idx, "compose"))

    # Confidence-aware routing: cross-input / heavy reasoning -> pro model
    # (honoured only when GEMINI_USE_PRO is enabled; flash-only otherwise).
    prefer_pro = len(file_docs) >= 2 or (intent == "answer" and len(file_docs) >= 1)

    return Plan(steps=steps, intent=intent, prefer_pro=prefer_pro, goal=describe_goal(docs, intent))
