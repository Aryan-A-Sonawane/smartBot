"""In-memory dense-vector index with cosine top-k search.

This is a "proper" vector store for the corpus sizes here — exact nearest-neighbour
over L2-normalised embeddings (cosine == dot product), vectorised with numpy. No
external vector DB, no index-build latency: optimal for accuracy and latency on
small/medium documents.
"""

from __future__ import annotations

import numpy as np

from .chunker import Chunk


class VectorStore:
    def __init__(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        self.chunks = chunks
        mat = np.asarray(vectors, dtype="float32")
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        self._vectors = mat / np.clip(norms, 1e-9, None)  # L2-normalise for cosine

    def search(self, query_vector: list[float], k: int) -> list[tuple[Chunk, float]]:
        """Return the top-``k`` (chunk, cosine_score) pairs, highest first."""
        q = np.asarray(query_vector, dtype="float32")
        q = q / max(float(np.linalg.norm(q)), 1e-9)
        scores = self._vectors @ q
        top = np.argsort(-scores)[: max(1, k)]
        return [(self.chunks[i], float(scores[i])) for i in top]
