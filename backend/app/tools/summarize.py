"""Summarization tool — enforces the strict 1-line + 3 bullets + 5-sentence format."""

from __future__ import annotations

import re

from ..gemini_client import LLMUnavailable
from .base import ToolContext, ToolResult

SYSTEM = (
    "You are a precise summarization engine. You MUST output in EXACTLY this "
    "markdown structure and nothing else:\n"
    "**One-line summary:** <one sentence>\n\n"
    "**Key points**\n- <bullet 1>\n- <bullet 2>\n- <bullet 3>\n\n"
    "**5-sentence summary**\n<exactly five sentences>\n"
    "Use exactly three bullets and exactly five sentences."
)


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _heuristic(text: str) -> str:
    sents = _split_sentences(text) or [text.strip()[:200]]
    one = sents[0]
    bullets = (sents[:3] + ["(insufficient content)"] * 3)[:3]
    five = " ".join((sents[:5] + [""] * 5)[:5]).strip()
    return (
        f"**One-line summary:** {one}\n\n"
        f"**Key points**\n- {bullets[0]}\n- {bullets[1]}\n- {bullets[2]}\n\n"
        f"**5-sentence summary**\n{five}"
    )


async def run(ctx: ToolContext) -> ToolResult:
    context = ctx.combined_context()
    prompt = (
        f"User request: {ctx.query or 'Summarize the content.'}\n\n"
        f"Content to summarize:\n{context}"
    )
    try:
        res = await ctx.gemini.generate(prompt, system=SYSTEM, prefer_pro=ctx.prefer_pro)
        ctx.record(res.input_tokens, res.output_tokens, res.model)
        return ToolResult(text=res.text, notes=res.notes)
    except LLMUnavailable as exc:
        if ctx.gemini.configured:
            return ToolResult(text="", ok=False, error=f"Gemini call failed: {exc}")
        return ToolResult(
            text=_heuristic(context or ctx.query),
            notes=["LLM unavailable — heuristic summary"],
        )
