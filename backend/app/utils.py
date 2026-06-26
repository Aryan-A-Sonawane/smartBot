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


def youtube_id(url: str) -> str | None:
    m = _YT_ID_RE.search(url or "")
    return m.group(1) if m else None


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token)."""
    return max(1, len(text or "") // 4)
