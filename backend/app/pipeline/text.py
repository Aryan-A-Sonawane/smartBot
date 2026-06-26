"""Text input handling — the plain text query becomes an extracted doc."""

from __future__ import annotations

from ..schemas import ExtractedDoc


def text_doc(query: str) -> ExtractedDoc:
    """Represent the user's typed query as an extracted document."""
    return ExtractedDoc(source="Text query", kind="text", content=query.strip())
