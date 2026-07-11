"""FastAPI application: CORS, health, and the streaming ``/chat`` endpoint.

``POST /chat`` accepts multipart ``query`` + ``files[]`` and returns a
``text/event-stream`` of typed events that the Next.js frontend consumes
(see ``frontend/src/lib/api.ts``).
"""

from __future__ import annotations

import json
import logging

from fastapi import Depends, FastAPI, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .agent.executor import run_agent
from .config import Settings, get_settings
from .deps import get_gemini_client, get_registry, get_settings_dep
from .gemini_client import GeminiClient
from .pipeline.base import InputFile
from .schemas import ExtractedDoc
from .tools.registry import ToolRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smartbot")

app = FastAPI(
    title="SmartBot Agent API",
    version="1.0.0",
    description="Agentic multimodal app: Text + Image + PDF + Audio -> autonomous tasks.",
)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health(settings: Settings = Depends(get_settings_dep)) -> dict:
    return {
        "status": "ok",
        "llm_configured": settings.has_llm,
        "model_fast": settings.gemini_model_fast,
        "model_pro": settings.gemini_model_pro,
        "whisper_model": settings.whisper_model,
    }


@app.get("/")
async def root() -> dict:
    return {"service": "smartbot", "docs": "/docs", "health": "/health"}


def _parse_prior_context(raw: str) -> list[ExtractedDoc]:
    """Parse the follow-up ``prior_context`` JSON into docs, tolerating junk."""
    if not raw.strip():
        return []
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Ignoring malformed prior_context payload")
        return []
    docs: list[ExtractedDoc] = []
    for item in items if isinstance(items, list) else []:
        try:
            docs.append(ExtractedDoc.model_validate(item))
        except Exception:
            continue
    return docs


@app.post("/chat")
async def chat(
    query: str = Form(default=""),
    prior_context: str = Form(default=""),
    files: list[UploadFile] | None = None,
    settings: Settings = Depends(get_settings_dep),
    gemini: GeminiClient = Depends(get_gemini_client),
    registry: ToolRegistry = Depends(get_registry),
) -> StreamingResponse:
    # Read uploads into memory (with a size guard for robustness).
    inputs: list[InputFile] = []
    max_bytes = settings.max_file_mb * 1024 * 1024
    for uf in files or []:
        data = await uf.read()
        if len(data) > max_bytes:
            logger.warning("Rejecting oversized upload: %s (%d bytes)", uf.filename, len(data))
            continue
        inputs.append(
            InputFile(
                filename=uf.filename or "upload",
                content_type=uf.content_type or "",
                data=data,
            )
        )

    # Follow-up turns replay previously extracted docs so the user need not
    # re-upload (in-session memory). Malformed entries are skipped, not fatal.
    prior_docs = _parse_prior_context(prior_context)

    async def event_stream():
        async for frame in run_agent(
            query,
            inputs,
            gemini=gemini,
            settings=settings,
            registry=registry,
            prior_docs=prior_docs,
        ):
            yield frame

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
