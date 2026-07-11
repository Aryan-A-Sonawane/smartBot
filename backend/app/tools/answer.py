"""General conversational answering and cross-input reasoning.

Handles plain questions and unified multi-input queries (e.g. "do the audio and
the document discuss the same topic?").
"""

from __future__ import annotations

from ..gemini_client import LLMUnavailable
from .base import ToolContext, ToolResult

SYSTEM = (
    "You are SmartBot, a friendly, helpful assistant. Treat the provided context "
    "as the PRIMARY source and ground your answer in it. But the user's question "
    "may go BEYOND what the document literally states — asking you to analyse, "
    "estimate, plan, critique, or reason about it. In that case, use the context "
    "as input and bring in your own general knowledge and judgement to give a "
    "genuinely useful answer; state key assumptions briefly rather than refusing "
    "because the document doesn't spell it out. When several sources are present, "
    "reason across them and compare/relate them as the question requires. If the "
    "context has [Page N] markers (from a PDF), cite the page(s) a fact came from "
    "in parentheses, e.g. (p. 2). Be clear and concise; output plain text/markdown."
)


async def run(ctx: ToolContext) -> ToolResult:
    context = ctx.combined_context()
    if context:
        prompt = f"Question: {ctx.query}\n\nContext from the user's inputs:\n{context}"
    else:
        prompt = ctx.query
    try:
        res = await ctx.gemini.generate(prompt, system=SYSTEM, prefer_pro=ctx.prefer_pro)
        ctx.record(res.input_tokens, res.output_tokens, res.model)
        return ToolResult(text=res.text, notes=res.notes)
    except LLMUnavailable as exc:
        if ctx.gemini.configured:
            return ToolResult(text="", ok=False, error=f"Gemini call failed: {exc}")
        snippet = (context or ctx.query)[:500]
        return ToolResult(
            text=(
                "I can't reach the language model right now, but here's the context "
                f"I gathered:\n\n{snippet}"
            ),
            notes=["LLM unavailable"],
        )
