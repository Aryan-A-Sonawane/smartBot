"""Generic URL fetcher — fetches a page found in any input and extracts readable
text. Generalises the YouTube task to arbitrary links (assignment §2A).
"""

from __future__ import annotations

import httpx

from ..schemas import ExtractedDoc
from ..utils import find_all_urls, is_youtube
from .base import ToolContext, ToolResult

_HEADERS = {"User-Agent": "Mozilla/5.0 (SmartBot agent; +https://github.com)"}
_MAX_CHARS = 12000


def _detect_url(ctx: ToolContext) -> str | None:
    haystack = ctx.query + "\n" + ctx.combined_context()
    for url in find_all_urls(haystack):
        if not is_youtube(url):  # YouTube handled by its own tool
            return url
    return None


def _readable(html: str) -> str:
    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        text = soup.get_text("\n")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return "\n".join(lines)
    except Exception:
        return html


async def run(ctx: ToolContext) -> ToolResult:
    url = _detect_url(ctx)
    if not url:
        return ToolResult(text="", ok=False, error="No fetchable URL detected in inputs.")
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=15.0, headers=_HEADERS
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content = _readable(resp.text)[:_MAX_CHARS]
    except Exception as exc:
        return ToolResult(text="", ok=False, error=f"Failed to fetch {url}: {exc}")
    if not content.strip():
        return ToolResult(text="", ok=False, error=f"No readable content at {url}.")
    doc = ExtractedDoc(source=f"Fetched page: {url}", kind="text", content=content)
    ctx.docs.append(doc)
    return ToolResult(text=content, extra_doc=doc, notes=[f"fetched {url}"])
