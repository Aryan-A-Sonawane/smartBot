"""General conversational answering and cross-input reasoning.

Handles plain questions and unified multi-input queries (e.g. "do the audio and
the document discuss the same topic?").
"""

from __future__ import annotations

from ..gemini_client import LLMUnavailable
from .base import ToolContext, ToolResult

SYSTEM = (
    "You are SmartBot, a friendly, helpful assistant. Answer the user's question "
    "using ALL provided context. When multiple sources are present, reason across "
    "them and compare/relate them as the question requires. Be clear and concise. "
    "Output plain text/markdown only."
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
