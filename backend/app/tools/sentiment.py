"""Sentiment analysis — label + confidence + one-line justification.

Uses a 3-vote majority for robustness when the LLM is available.
"""

from __future__ import annotations

import asyncio
import re
from collections import Counter

from ..gemini_client import LLMUnavailable
from .base import ToolContext, ToolResult

SYSTEM = (
    "You are a sentiment classifier. Respond in EXACTLY this format:\n"
    "**Sentiment:** <Positive|Negative|Neutral|Mixed>\n"
    "**Confidence:** <0..1>\n\n"
    "**Why:** <one short sentence>"
)

_POS = {"good", "great", "love", "excellent", "happy", "win", "success", "amazing", "best", "positive", "wonderful"}
_NEG = {"bad", "terrible", "hate", "awful", "sad", "fail", "worst", "angry", "negative", "poor", "broken"}


def _label_from(text: str) -> str:
    m = re.search(r"\*\*Sentiment:\*\*\s*([A-Za-z]+)", text)
    return (m.group(1).capitalize() if m else "Neutral")


def _heuristic(text: str) -> str:
    words = re.findall(r"[a-z']+", text.lower())
    pos = sum(w in _POS for w in words)
    neg = sum(w in _NEG for w in words)
    if pos == neg:
        label, conf = "Neutral", 0.5
    elif pos > neg:
        label, conf = "Positive", min(0.95, 0.5 + 0.1 * (pos - neg))
    else:
        label, conf = "Negative", min(0.95, 0.5 + 0.1 * (neg - pos))
    return (
        f"**Sentiment:** {label}\n**Confidence:** {round(conf, 2)}\n\n"
        f"**Why:** Lexical balance of positive ({pos}) vs negative ({neg}) cues."
    )


async def run(ctx: ToolContext) -> ToolResult:
    context = ctx.combined_context() or ctx.query
    prompt = f"Classify the sentiment of the following text:\n\n{context}"
    try:
        # Three independent votes; majority label wins, first matching response returned.
        results = await asyncio.gather(
            *(
                ctx.gemini.generate(prompt, system=SYSTEM, temperature=0.4)
                for _ in range(3)
            )
        )
        for r in results:
            ctx.record(r.input_tokens, r.output_tokens, r.model)
        labels = [_label_from(r.text) for r in results]
        winner = Counter(labels).most_common(1)[0][0]
        chosen = next((r for r in results if _label_from(r.text) == winner), results[0])
        return ToolResult(text=chosen.text, notes=[f"majority vote: {labels}"])
    except LLMUnavailable as exc:
        if ctx.gemini.configured:
            return ToolResult(text="", ok=False, error=f"Gemini call failed: {exc}")
        return ToolResult(
            text=_heuristic(context), notes=["LLM unavailable — lexicon heuristic"]
        )
