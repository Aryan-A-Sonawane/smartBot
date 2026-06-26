"""Shared context and result types for tools.

A ``ToolContext`` carries everything a tool needs (the query, all extracted
docs, the LLM client, routing preference) and accumulates token usage so the
cost panel can report real numbers. Tools are pure async callables that return
a ``ToolResult`` — easy to unit test and to register via DI.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..gemini_client import GeminiClient
from ..schemas import ExtractedDoc


@dataclass
class ToolContext:
    query: str
    docs: list[ExtractedDoc]
    gemini: GeminiClient
    prefer_pro: bool = False
    # Running token totals across every LLM call in this request.
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""

    def combined_context(self) -> str:
        """All extracted text, labelled by source, for prompting."""
        blocks = []
        for d in self.docs:
            header = f"--- Source: {d.source} ({d.kind}) ---"
            blocks.append(f"{header}\n{d.content}")
        return "\n\n".join(blocks).strip()

    def record(self, in_tok: int, out_tok: int, model: str) -> None:
        self.input_tokens += in_tok
        self.output_tokens += out_tok
        if model:
            self.model = model


@dataclass
class ToolResult:
    text: str
    ok: bool = True
    error: str | None = None
    # A new document this tool produced (e.g. fetched page / transcript) to add
    # to the Extracted Text panel.
    extra_doc: ExtractedDoc | None = None
    notes: list[str] = field(default_factory=list)
