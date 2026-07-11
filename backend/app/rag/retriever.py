"""Gated RAG retrieval over the current documents.

Returns focused, cited chunks for large documents; returns ``None`` for small
ones (they fit the context window, so full context is more accurate and just as
fast) or when embeddings are unavailable (offline) — callers then use full text.
"""

from __future__ import annotations

from ..gemini_client import GeminiClient, LLMUnavailable
from ..schemas import ExtractedDoc
from .chunker import Chunk, chunk_document
from .store import VectorStore

# Retrieval only kicks in above this much text — below it, full context wins on
# both accuracy (nothing dropped) and latency (no embedding round-trips).
_MIN_CHARS = 6000
_TOP_K = 6


def cite(chunk: Chunk) -> str:
    page = f" p. {chunk.page}" if chunk.page else ""
    return f"[{chunk.source}{page}]\n{chunk.text}"


async def retrieve(
    query: str,
    docs: list[ExtractedDoc],
    gemini: GeminiClient,
    *,
    top_k: int = _TOP_K,
    min_chars: int = _MIN_CHARS,
) -> list[Chunk] | None:
    """Retrieve the top-k relevant chunks, or None when retrieval isn't used."""
    corpus = [d for d in docs if d.source != "Text query" and d.content]
    total = sum(len(d.content) for d in corpus)
    if not query.strip() or total < min_chars:
        return None  # small enough — skip retrieval (latency)

    chunks: list[Chunk] = []
    for d in corpus:
        chunks.extend(chunk_document(d.content, d.source))
    if len(chunks) <= top_k:
        return None  # not enough chunks to be worth retrieving

    try:
        doc_vecs = await gemini.embed([c.text for c in chunks], task_type="retrieval_document")
        q_vec = await gemini.embed([query], task_type="retrieval_query")
    except LLMUnavailable:
        return None  # offline — caller falls back to full context

    store = VectorStore(chunks, doc_vecs)
    hits = store.search(q_vec[0], top_k)
    return [chunk for chunk, _score in hits]
