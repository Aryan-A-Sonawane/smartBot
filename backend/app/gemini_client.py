"""Thin, resilient wrapper around the Google Gemini SDK.

Responsibilities:
* lazy configuration from settings,
* retry with exponential backoff on transient errors,
* automatic ``flash`` -> ``pro`` fallback when the fast model fails,
* a uniform return type carrying text + token usage for the cost panel.

If no API key is configured (e.g. during unit tests) the client raises
``LLMUnavailable`` so callers can degrade gracefully instead of crashing.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from .config import Settings

logger = logging.getLogger("smartbot.gemini")


class LLMUnavailable(RuntimeError):
    """Raised when the LLM cannot be used (no key, SDK missing, all retries failed)."""


@dataclass
class LLMResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    fallback_used: bool = False
    notes: list[str] = field(default_factory=list)


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) used when usage metadata is absent."""
    return max(1, len(text) // 4)


class GeminiClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._genai: Any = None
        self._configured = False

    @property
    def configured(self) -> bool:
        """True when an API key is set (i.e. a failed call is a real API error,
        not just 'running offline')."""
        return self._settings.has_llm

    @property
    def embed_model(self) -> str:
        return self._settings.gemini_embed_model

    # ----- setup -----
    def _ensure(self) -> Any:
        if not self._settings.has_llm:
            raise LLMUnavailable("GEMINI_API_KEY is not set")
        if self._configured:
            return self._genai
        try:
            import google.generativeai as genai  # type: ignore
        except Exception as exc:  # pragma: no cover - import guard
            raise LLMUnavailable(f"google-generativeai not importable: {exc}") from exc
        genai.configure(api_key=self._settings.gemini_api_key)
        self._genai = genai
        self._configured = True
        return genai

    # ----- core generation (sync, run in a thread by callers) -----
    def _generate_sync(
        self,
        prompt_parts: list[Any],
        *,
        model_name: str,
        system: str | None,
        temperature: float,
    ) -> LLMResult:
        genai = self._ensure()
        model = genai.GenerativeModel(model_name, system_instruction=system)
        resp = model.generate_content(
            prompt_parts,
            generation_config={"temperature": temperature},
        )
        text = (getattr(resp, "text", "") or "").strip()
        usage = getattr(resp, "usage_metadata", None)
        in_tok = getattr(usage, "prompt_token_count", 0) or 0
        out_tok = getattr(usage, "candidates_token_count", 0) or 0
        return LLMResult(
            text=text,
            input_tokens=int(in_tok),
            output_tokens=int(out_tok),
            model=model_name,
        )

    async def generate(
        self,
        prompt: str,
        *,
        parts: list[Any] | None = None,
        system: str | None = None,
        prefer_pro: bool = False,
        temperature: float = 0.3,
        max_retries: int = 2,
    ) -> LLMResult:
        """Generate content with retry + flash->pro fallback.

        ``parts`` may include images/blobs for multimodal calls; ``prompt`` is
        always appended as the textual instruction.
        """
        prompt_parts: list[Any] = []
        if parts:
            prompt_parts.extend(parts)
        prompt_parts.append(prompt)

        # Flash-only unless GEMINI_USE_PRO is set; then hard tasks start on pro
        # and non-pro calls may escalate flash->pro on failure.
        primary = self._settings.model_for(prefer_pro)
        models = [primary]
        if self._settings.use_pro and self._settings.gemini_model_pro != primary:
            models.append(self._settings.gemini_model_pro)

        last_exc: Exception | None = None
        for idx, model_name in enumerate(models):
            for attempt in range(max_retries + 1):
                try:
                    result = await asyncio.to_thread(
                        self._generate_sync,
                        prompt_parts,
                        model_name=model_name,
                        system=system,
                        temperature=temperature,
                    )
                    result.fallback_used = idx > 0
                    if idx > 0:
                        result.notes.append(f"fell back to {model_name}")
                    if not result.input_tokens:
                        result.input_tokens = estimate_tokens(
                            (system or "") + prompt + "".join(str(p) for p in (parts or []))
                        )
                    if not result.output_tokens:
                        result.output_tokens = estimate_tokens(result.text)
                    return result
                except LLMUnavailable:
                    raise
                except Exception as exc:  # transient API error
                    last_exc = exc
                    logger.warning(
                        "Gemini call failed (model=%s attempt=%s): %s",
                        model_name,
                        attempt,
                        exc,
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(0.6 * (2**attempt))
        raise LLMUnavailable(f"all Gemini attempts failed: {last_exc}")

    # ----- embeddings (for RAG retrieval) -----
    def _embed_sync(self, texts: list[str], task_type: str) -> list[list[float]]:
        genai = self._ensure()
        res = genai.embed_content(
            model=self._settings.gemini_embed_model,
            content=texts,
            task_type=task_type,
        )
        emb = res["embedding"]
        # embed_content returns a flat list for a single string; normalise to list-of-lists.
        return emb if emb and isinstance(emb[0], list) else [emb]

    async def embed(
        self, texts: list[str], *, task_type: str = "retrieval_document"
    ) -> list[list[float]]:
        """Embed a batch of texts. Raises ``LLMUnavailable`` when no key is set."""
        if not texts:
            return []
        return await asyncio.to_thread(self._embed_sync, texts, task_type)

    @staticmethod
    def image_part(data: bytes, mime_type: str) -> dict[str, Any]:
        """Build a multimodal image part for ``generate(parts=...)``."""
        return {"mime_type": mime_type, "data": data}
