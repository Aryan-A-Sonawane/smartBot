"""Structured extraction — action items, tables, or entities from the content.

Cites the page when the source PDF used ``[Page N]`` markers.
"""

from __future__ import annotations

import re

from ..gemini_client import LLMUnavailable
from .base import ToolContext, ToolResult

SYSTEM = (
    "You extract structured information from documents. Determine what the user "
    "wants (action items, a table, key entities, fields) and return ONLY that, as "
    "clean markdown. For action items use a bullet list. If the source has "
    "[Page N] markers, cite the page in parentheses. Be faithful — do not invent."
)


def _heuristic(text: str, query: str) -> str:
    lines = [ln.strip() for ln in text.splitlines()]
    items = []
    capture = False
    for ln in lines:
        low = ln.lower()
        if "action item" in low:
            capture = True
            continue
        if capture:
            if ln.startswith(("-", "*", "•")) or re.match(r"^\d+[.)]", ln):
                items.append("- " + re.sub(r"^[-*•\d.)\s]+", "", ln))
            elif ln == "":
                continue
            else:
                # stop at a new section header
                if ln.endswith(":"):
                    break
    if not items:
        items = ["- " + ln.lstrip("-*• ") for ln in lines if ln.startswith(("-", "*", "•"))][:10]
    body = "\n".join(items) if items else "(no structured items detected)"
    return f"**Extracted items**\n{body}"


async def run(ctx: ToolContext) -> ToolResult:
    context = ctx.combined_context()
    prompt = (
        f"User request: {ctx.query or 'Extract the key structured items.'}\n\n"
        f"Document content:\n{context}"
    )
    try:
        res = await ctx.gemini.generate(prompt, system=SYSTEM, prefer_pro=ctx.prefer_pro)
        ctx.record(res.input_tokens, res.output_tokens, res.model)
        return ToolResult(text=res.text, notes=res.notes)
    except LLMUnavailable as exc:
        if ctx.gemini.configured:
            return ToolResult(text="", ok=False, error=f"Gemini call failed: {exc}")
        return ToolResult(
            text=_heuristic(context, ctx.query), notes=["LLM unavailable — regex heuristic"]
        )
