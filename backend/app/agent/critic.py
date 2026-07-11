"""Self-correcting critic (evaluator-optimizer).

After a tool produces output, the critic validates it against the format rules
for the detected intent and, if it fails, asks the LLM to reformat it once —
preserving the facts, fixing only the structure. Intents without a fixed output
contract (``answer``) are intentionally left untouched.
"""

from __future__ import annotations

import re

from ..gemini_client import LLMUnavailable
from .planner import Intent

# ---- Target structures used to repair a malformed output ----

_SUMMARY_SPEC = (
    "**One-line summary:** <one sentence>\n\n**Key points**\n- b1\n- b2\n- b3\n\n"
    "**5-sentence summary**\n<exactly five sentences>"
)
_SENTIMENT_SPEC = (
    "**Sentiment:** <Positive|Negative|Neutral|Mixed>\n**Confidence:** <0..1>\n\n"
    "**Why:** <one short sentence>"
)
_CODE_SPEC = (
    "**Language:** <detected language>\n\n**What it does:** <plain-English>\n\n"
    "**Walkthrough**\n- <step>\n- <step>\n\n**Bugs / edge cases:** <bugs or 'none found'>\n\n"
    "**Time complexity:** <Big-O time and space>"
)
_STRUCT_SPEC = (
    "The extracted items as a clean markdown bullet list (or a markdown table when "
    "the data is tabular). Do not add, remove, or invent any content."
)

_SENT_LABELS = ("positive", "negative", "neutral", "mixed")


def validate_summary(text: str) -> tuple[bool, str]:
    """Enforce the three-format summary contract."""
    has_oneline = bool(re.search(r"one-?line summary", text, re.IGNORECASE))
    bullets = re.findall(r"^\s*[-*]\s+\S", text, re.MULTILINE)
    has_five_header = bool(re.search(r"5-?sentence summary", text, re.IGNORECASE))
    if not has_oneline:
        return False, "missing one-line summary"
    if len(bullets) < 3:
        return False, f"expected 3 bullets, found {len(bullets)}"
    if not has_five_header:
        return False, "missing 5-sentence summary section"
    return True, "ok"


def validate_sentiment(text: str) -> tuple[bool, str]:
    """Require a label and a confidence value (assignment §3.5)."""
    low = text.lower()
    if not any(label in low for label in _SENT_LABELS):
        return False, "missing sentiment label"
    has_conf = "confidence" in low or bool(re.search(r"\b(0?\.\d+|1(?:\.0+)?|\d{1,3}\s*%)\b", text))
    if not has_conf:
        return False, "missing confidence value"
    return True, "ok"


def validate_code_explain(text: str) -> tuple[bool, str]:
    """Require the bug and time-complexity coverage the task calls for (§3.6)."""
    low = text.lower()
    if "complexity" not in low:
        return False, "missing time complexity"
    if not re.search(r"bug|edge case|risk|none found|no bugs", low):
        return False, "missing bugs/edge-cases coverage"
    return True, "ok"


def validate_structured(text: str) -> tuple[bool, str]:
    """Require a bullet list or a table so the extraction is actually structured."""
    has_bullet = bool(re.search(r"^\s*[-*]\s+\S", text, re.MULTILINE))
    has_table = bool(re.search(r"\|.+\|", text))
    if not (has_bullet or has_table):
        return False, "no bullet list or table found"
    return True, "ok"


# intent -> (validator, repair-target structure)
_CONTRACTS: dict[Intent, tuple] = {
    "summarize": (validate_summary, _SUMMARY_SPEC),
    "sentiment": (validate_sentiment, _SENTIMENT_SPEC),
    "code_explain": (validate_code_explain, _CODE_SPEC),
    "structured_extract": (validate_structured, _STRUCT_SPEC),
}


async def critique(text: str, intent: Intent, gemini, prefer_pro: bool = False) -> tuple[str, list[str]]:
    """Validate and, if needed, repair the output once. Returns (text, notes)."""
    notes: list[str] = []
    contract = _CONTRACTS.get(intent)
    if contract is None:  # e.g. 'answer' — no fixed output format to enforce
        return text, notes
    validate, spec = contract
    valid, reason = validate(text)
    if valid:
        notes.append("critic: format valid")
        return text, notes
    notes.append(f"critic: invalid ({reason}) — repairing")
    try:
        fix_prompt = (
            "Reformat the following into EXACTLY this structure and nothing else, "
            "preserving all factual content:\n"
            f"{spec}\n\nContent to reformat:\n{text}"
        )
        res = await gemini.generate(fix_prompt, prefer_pro=prefer_pro, temperature=0.1)
        if res.text.strip():
            notes.append("critic: repaired")
            return res.text, notes
    except LLMUnavailable:
        notes.append("critic: repair skipped (LLM unavailable)")
    return text, notes
