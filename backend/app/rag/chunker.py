"""Split extracted text into overlapping, page-aware chunks for retrieval.

Chunks respect paragraph boundaries (and sentence boundaries inside long
paragraphs, e.g. transcripts) and carry their source + page number so the answer
can cite where a fact came from — e.g. "(report.pdf p. 3)".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PAGE_RE = re.compile(r"^\[Page (\d+)\]\s*$", re.MULTILINE)
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Chunk:
    text: str
    source: str
    page: int | None = None


def _segments(text: str, size: int) -> list[tuple[str, int | None]]:
    """(text, page) segments: paragraphs, splitting oversized ones into sentences."""
    out: list[tuple[str, int | None]] = []
    page: int | None = None
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        marker = _PAGE_RE.match(para)
        if marker:
            page = int(marker.group(1))
            para = _PAGE_RE.sub("", para).strip()
            if not para:
                continue
        if len(para) <= size:
            out.append((para, page))
        else:
            for sent in _SENT_SPLIT.split(para):
                sent = sent.strip()
                if sent:
                    out.append((sent, page))
    return out


def chunk_document(text: str, source: str, size: int = 1000, overlap: int = 150) -> list[Chunk]:
    """Pack segments into ~``size``-char chunks with ``overlap`` carried between
    them, tracking the current ``[Page N]`` marker for citations."""
    chunks: list[Chunk] = []
    buf = ""
    buf_page: int | None = None
    for seg, seg_page in _segments(text, size):
        page_break = bool(buf) and seg_page != buf_page
        size_break = bool(buf) and len(buf) + len(seg) + 1 > size
        if page_break or size_break:
            chunks.append(Chunk(buf.strip(), source, buf_page))
            # Carry an overlap tail only within the same page, so a chunk never
            # mixes pages — that keeps "(p. N)" citations accurate.
            tail = buf[-overlap:] if (overlap and size_break and not page_break) else ""
            buf = (tail + " ") if tail else ""
        if not buf:
            buf_page = seg_page
        buf += ((" " if buf else "") + seg)
    if buf.strip():
        chunks.append(Chunk(buf.strip(), source, buf_page))
    return chunks
