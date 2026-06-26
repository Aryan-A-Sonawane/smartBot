"""Code explanation — what it does, bugs/edge cases, and time complexity."""

from __future__ import annotations

from ..gemini_client import LLMUnavailable
from .base import ToolContext, ToolResult

SYSTEM = (
    "You are a senior engineer explaining code. Respond in this markdown format:\n"
    "**Language:** <detected language>\n\n"
    "**What it does:** <plain-English explanation>\n\n"
    "**Walkthrough**\n- <step>\n- <step>\n\n"
    "**Bugs / edge cases:** <any bugs, risks, or 'none found'>\n\n"
    "**Time complexity:** <Big-O time and space>"
)


async def run(ctx: ToolContext) -> ToolResult:
    context = ctx.combined_context() or ctx.query
    prompt = (
        f"User request: {ctx.query or 'Explain this code.'}\n\n"
        f"Code / content:\n{context}"
    )
    try:
        res = await ctx.gemini.generate(prompt, system=SYSTEM, prefer_pro=ctx.prefer_pro)
        ctx.record(res.input_tokens, res.output_tokens, res.model)
        return ToolResult(text=res.text, notes=res.notes)
    except LLMUnavailable as exc:
        if ctx.gemini.configured:
            return ToolResult(text="", ok=False, error=f"Gemini call failed: {exc}")
        return ToolResult(
            text=(
                "**Language:** (undetected — LLM unavailable)\n\n"
                "**What it does:** Unable to analyze without the LLM.\n\n"
                "**Walkthrough**\n- Configure GEMINI_API_KEY to enable code analysis.\n\n"
                "**Bugs / edge cases:** n/a\n\n"
                "**Time complexity:** n/a"
            ),
            ok=True,
            notes=["LLM unavailable"],
        )
