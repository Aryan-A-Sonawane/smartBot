"""YouTube transcript fetcher with a yt-dlp + Whisper fallback.

Primary path: ``youtube-transcript-api`` (fast, no download). If that fails —
no captions, or the caller's IP is blocked — fall back to downloading the audio
with ``yt-dlp`` and transcribing it locally with faster-whisper. If both fail,
return a graceful error so the run continues from the rest of the context.
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


def _fetch_transcript(video_id: str) -> tuple[str, str]:
    """Return (text, language_code) for the caption track that best matches the
    SPOKEN audio.

    ``get_transcript`` defaults to English, so a non-English video with no English
    captions fell through to the Whisper fallback and got mis-transcribed. Instead
    we list the tracks and prefer a human caption in the video's spoken language
    (the auto-generated track's language), then the auto-generated track itself —
    never a translated track that wouldn't match what was actually said.
    """
    from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore

    tracks = list(YouTubeTranscriptApi.list_transcripts(video_id))
    if not tracks:
        return "", ""
    generated = [t for t in tracks if t.is_generated]
    manual = [t for t in tracks if not t.is_generated]
    spoken = generated[0].language_code if generated else None
    if spoken:
        chosen = next((t for t in manual if t.language_code == spoken), None) or generated[0]
    else:
        chosen = (manual or tracks)[0]

    data = chosen.fetch()
    text = " ".join(
        (seg["text"] if isinstance(seg, dict) else getattr(seg, "text", "")) for seg in data
    ).strip()
    return text, getattr(chosen, "language_code", "")


def _download_audio(url: str) -> tuple[bytes, str]:
    """Download the best audio track with yt-dlp → (bytes, file_suffix)."""
    import glob
    import os
    import tempfile

    import yt_dlp  # type: ignore

    tmpdir = tempfile.mkdtemp(prefix="yt_")
    template = os.path.join(tmpdir, "audio.%(ext)s")
    opts = {
        "format": "bestaudio/best",
        "outtmpl": template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    files = glob.glob(os.path.join(tmpdir, "audio.*"))
    if not files:
        return b"", ""
    path = files[0]
    with open(path, "rb") as fh:
        data = fh.read()
    return data, os.path.splitext(path)[1] or ".m4a"


async def _ytdlp_whisper(url: str, whisper_model: str) -> str:
    """Best-effort fallback: yt-dlp download + Whisper transcription."""
    from ..pipeline.audio_stt import _transcribe_sync

    data, suffix = await asyncio.to_thread(_download_audio, url)
    if not data:
        return ""
    text, _duration = await asyncio.to_thread(_transcribe_sync, data, suffix, whisper_model)
    return text.strip()


async def run(ctx: ToolContext) -> ToolResult:
    url = _detect_url(ctx)
    if not url:
        return ToolResult(text="", ok=False, error="No YouTube URL detected in inputs.")
    vid = youtube_id(url)
    if not vid:
        return ToolResult(text="", ok=False, error=f"Could not parse video id from {url}.")

    source = "captions"
    lang = ""
    transcript = ""
    try:
        transcript, lang = await asyncio.to_thread(_fetch_transcript, vid)
    except Exception:
        transcript = ""

    if not transcript:
        # No usable captions — transcribe the actual audio as a last resort.
        try:
            transcript = await _ytdlp_whisper(url, ctx.whisper_model)
            source = "yt-dlp+whisper"
        except Exception as exc:
            return ToolResult(
                text="",
                ok=False,
                error=f"Transcript unavailable for {url}: {exc}",
                notes=["youtube: captions + yt-dlp fallback both failed"],
            )

    if not transcript:
        return ToolResult(text="", ok=False, error=f"No transcript available for {url}.")

    label = f"captions ({lang})" if source == "captions" and lang else source
    doc = ExtractedDoc(source=f"YouTube transcript ({vid})", kind="text", content=transcript)
    ctx.docs.append(doc)
    return ToolResult(text=transcript, extra_doc=doc, notes=[f"fetched {url} via {label}"])
