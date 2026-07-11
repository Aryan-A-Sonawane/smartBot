"""Unit tests for the RAG pipeline — chunking + vector search (run fully offline,
no embeddings API needed)."""

from __future__ import annotations

from app.rag.chunker import Chunk, chunk_document
from app.rag.store import VectorStore


def test_chunker_tracks_pages_and_splits():
    text = (
        "[Page 1]\n" + ("alpha sentence. " * 60).strip() + "\n\n"
        "[Page 2]\n" + ("beta sentence. " * 60).strip()
    )
    chunks = chunk_document(text, "doc.pdf", size=300, overlap=40)
    assert len(chunks) > 2  # long paragraphs were split into multiple chunks
    assert all(c.source == "doc.pdf" for c in chunks)
    pages = {c.page for c in chunks}
    assert 1 in pages and 2 in pages  # page markers tracked for citations
    assert all(len(c.text) <= 360 for c in chunks)  # ~size + a little overlap


def test_vector_store_returns_nearest():
    chunks = [Chunk("a", "d"), Chunk("b", "d"), Chunk("c", "d")]
    vectors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.92, 0.08, 0.0]]
    store = VectorStore(chunks, vectors)
    hits = store.search([1.0, 0.0, 0.0], k=2)
    assert [c.text for c, _ in hits] == ["a", "c"]  # cosine-nearest to the query
    assert hits[0][1] >= hits[1][1]  # scores sorted descending
