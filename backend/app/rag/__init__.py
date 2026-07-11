"""Retrieval-augmented generation: chunk → embed → index → retrieve top-k.

Used by the answer tool for question-answering over large documents. Small docs
skip retrieval entirely (they fit the context window), which keeps latency low;
large docs get focused, cited chunks, which improves accuracy and relevance.
"""
