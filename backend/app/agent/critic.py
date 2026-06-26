"""Self-correcting critic.

After a tool produces output, the critic validates it against the format rules
for the detected goal. For summaries it checks the strict 1-line + 3 bullets +
5-sentence structure and asks the LLM to fix it once if it fails.
"""

from __future__ import annotations

import re

from ..gemini_client import LLMUnavailable
from .planner import Intent


def validate_summary(text: str) -> tuple[bool, str]:
    """Return (is_valid, reason). Enforces the three-format summary contract."""
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


async def critique(text: str, intent: Intent, gemini, prefer_pro: bool = False) -> tuple[str, list[str]]:
    """Validate and, if needed, repair the output once. Returns (text, notes)."""
    notes: list[str] = []
    if intent != "summarize":
        return text, notes
    valid, reason = validate_summary(text)
    if valid:
        notes.append("critic: format valid")
        return text, notes
    notes.append(f"critic: invalid ({reason}) — repairing")
    try:
        fix_prompt = (
            "Reformat the following into EXACTLY this structure and nothing else:\n"
            "**One-line summary:** <one sentence>\n\n**Key points**\n- b1\n- b2\n- b3\n\n"
            "**5-sentence summary**\n<exactly five sentences>\n\n"
            f"Content to reformat:\n{text}"
        )
        res = await gemini.generate(fix_prompt, prefer_pro=prefer_pro, temperature=0.1)
        if res.text.strip():
            notes.append("critic: repaired")
            return res.text, notes
    except LLMUnavailable:
        notes.append("critic: repair skipped (LLM unavailable)")
    return text, notes
