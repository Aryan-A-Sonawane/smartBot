"""Small pure helpers shared across the agent (URL detection, token math)."""

from __future__ import annotations

import re

_URL_RE = re.compile(r"https?://[^\s<>\")\]]+", re.IGNORECASE)
_YT_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


def find_url(text: str) -> str | None:
    """Return the first http(s) URL found in text, trimming trailing punctuation."""
    m = _URL_RE.search(text or "")
    if not m:
        return None
    return m.group(0).rstrip(".,);]'\"")


def find_all_urls(text: str) -> list[str]:
    return [u.rstrip(".,);]'\"") for u in _URL_RE.findall(text or "")]


def is_youtube(url: str) -> bool:
    return bool(_YT_ID_RE.search(url or ""))


_CROSS_INPUT_RE = re.compile(
    r"\b(compare|contrast|both|all files|all docs|each (file|doc|one)|difference|differ|"
    r"versus|vs\.?|relate|correlat|previous (file|doc|one)|earlier (file|doc|one)|"
    r"other (file|doc)|across|combine|combined|together|same topic)\b",
    re.IGNORECASE,
)


def is_cross_input(query: str) -> bool:
    """True when the query refers to several inputs at once (compare/both/…), so
    prior documents should be reasoned over together rather than ignored."""
    return bool(_CROSS_INPUT_RE.search(query or ""))


def youtube_id(url: str) -> str | None:
    m = _YT_ID_RE.search(url or "")
    return m.group(1) if m else None


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token)."""
    return max(1, len(text or "") // 4)
