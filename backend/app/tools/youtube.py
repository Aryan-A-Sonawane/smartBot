"""YouTube transcript fetcher.

Detects the video id from a URL found anywhere in the inputs and fetches its
transcript. Returns a graceful fallback message when no transcript exists.
The transcript is added to the context as a new extracted doc.
"""

from __future__ import annotations

import asyncio

from ..schemas import ExtractedDoc
from ..utils import find_all_urls, is_youtube, youtube_id
from .base import ToolContext, ToolResult


def _detect_url(ctx: ToolContext) -> str | None:
    haystack = ctx.query + "\n" + ctx.combined_context()
    for url in find_all_urls(haystack):
        if is_youtube(url):
            return url
    return None


def _fetch_sync(video_id: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore

    chunks = YouTubeTranscriptApi.get_transcript(video_id)
    return " ".join(c["text"] for c in chunks).strip()


async def run(ctx: ToolContext) -> ToolResult:
    url = _detect_url(ctx)
    if not url:
        return ToolResult(text="", ok=False, error="No YouTube URL detected in inputs.")
    vid = youtube_id(url)
    if not vid:
        return ToolResult(text="", ok=False, error=f"Could not parse video id from {url}.")
    try:
        transcript = await asyncio.to_thread(_fetch_sync, vid)
    except Exception as exc:
        return ToolResult(
            text="",
            ok=False,
            error=f"Transcript unavailable for {url}: {exc}",
            notes=["youtube fallback"],
        )
    if not transcript:
        return ToolResult(text="", ok=False, error=f"Empty transcript for {url}.")
    doc = ExtractedDoc(
        source=f"YouTube transcript ({vid})", kind="text", content=transcript
    )
    ctx.docs.append(doc)
    return ToolResult(text=transcript, extra_doc=doc, notes=[f"fetched {url}"])
