"""The executor orchestrates a single request end-to-end and yields SSE frames.

Flow: parallel extraction -> plan -> (clarify gate) -> emit plan + cost
estimate -> run each step with live trace + timing -> critic self-correct ->
stream the final answer token-by-token -> emit actual cost -> done.

Errors in any single step degrade gracefully (the step is marked ``error`` and
the run continues) so partial results still reach the user.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator

from .. import sse
from ..config import Settings
from ..gemini_client import GeminiClient
from ..pipeline import ExtractionOutcome, InputFile, extract_all
from ..pipeline.base import kind_for_mime
from ..pipeline.text import text_doc
from ..schemas import ExtractedDoc, StepStatus, ToolName
from ..tools.base import ToolContext
from ..tools.registry import ToolRegistry
from .cost import actual_cost, estimate_cost
from .critic import critique
from .planner import plan_request

_EXTRACTION_TOOLS: set[ToolName] = {"image_ocr", "pdf_extract", "audio_transcribe"}
_FETCH_TOOLS: set[ToolName] = {"youtube_transcript", "url_fetch"}


def _visible_docs(docs: list[ExtractedDoc]) -> list[ExtractedDoc]:
    """Docs shown in the Extracted Text panel (everything except the raw query)."""
    return [d for d in docs if d.source != "Text query"]


async def run_agent(
    query: str,
    files: list[InputFile],
    *,
    gemini: GeminiClient,
    settings: Settings,
    registry: ToolRegistry,
) -> AsyncIterator[str]:
    try:
        # ---- 1. Parallel extraction of every input ----
        outcomes: list[ExtractionOutcome] = await extract_all(
            files, gemini, settings.whisper_model
        )

        docs: list[ExtractedDoc] = []
        if query.strip():
            docs.append(text_doc(query))
        for oc in outcomes:
            if oc.ok and oc.doc is not None:
                docs.append(oc.doc)

        kinds_present = {kind_for_mime(f.filename, f.content_type) for f in files}

        # Per-tool extraction duration + error info for the trace.
        ext_duration: dict[str, int] = {}
        ext_error: dict[str, str] = {}
        audio_duration_human = ""
        for oc in outcomes:
            ext_duration[oc.tool] = ext_duration.get(oc.tool, 0) + oc.duration_ms
            if not oc.ok and oc.error:
                ext_error[oc.tool] = oc.error
            if oc.tool == "audio_transcribe" and oc.metadata.get("duration_human"):
                audio_duration_human = oc.metadata["duration_human"]

        # ---- 2. Plan (with the mandatory clarify gate) ----
        plan = plan_request(query, docs, kinds_present)
        if plan.needs_clarification:
            yield sse.clarify_event(plan.clarify_question)
            yield sse.done_event()
            return

        yield sse.plan_event(plan.steps)

        # ---- 3. Cost estimate (before execution) ----
        ctx = ToolContext(
            query=query, docs=docs, gemini=gemini, prefer_pro=plan.prefer_pro
        )
        est_model = settings.gemini_model_pro if plan.prefer_pro else settings.gemini_model_fast
        yield sse.cost_estimate_event(
            estimate_cost(ctx.combined_context(), est_model)
        )

        # ---- 4. Execute the plan ----
        final_text = ""
        extracted_emitted = False
        for step in plan.steps:
            started = time.time()
            yield sse.step_event(
                step.model_copy(update={"status": StepStatus.running})
            )

            status = StepStatus.done
            duration_ms = 0

            if step.tool in _EXTRACTION_TOOLS:
                # Work already done in the pipeline; replay timing + errors.
                duration_ms = ext_duration.get(step.tool, 0)
                if step.tool in ext_error:
                    status = StepStatus.error
                    step = step.model_copy(
                        update={"rationale": f"{step.rationale} (failed: {ext_error[step.tool]})"}
                    )

            elif step.tool in _FETCH_TOOLS:
                fn = registry.get(step.tool)
                result = await fn(ctx) if fn else None
                duration_ms = int((time.time() - started) * 1000)
                if result is None or not result.ok:
                    status = StepStatus.error
                    msg = result.error if result else "tool unavailable"
                    step = step.model_copy(
                        update={"rationale": f"{step.rationale} (skipped: {msg})"}
                    )

            elif step.tool == "compose":
                # Append audio duration when relevant, then stream tokens.
                if audio_duration_human and "duration" not in final_text.lower():
                    final_text = f"{final_text}\n\n_Audio duration: {audio_duration_human}_"
                for chunk in _chunk(final_text):
                    yield sse.token_event(chunk)
                    await asyncio.sleep(0)  # cooperative flush
                duration_ms = int((time.time() - started) * 1000)

            else:  # intent tool (summarize/sentiment/code_explain/structured_extract/answer)
                fn = registry.get(step.tool)
                if fn is None:
                    status = StepStatus.error
                else:
                    result = await fn(ctx)
                    if result.ok or result.text:
                        final_text = result.text
                        final_text, notes = await critique(
                            final_text, plan.intent, gemini, plan.prefer_pro
                        )
                    else:
                        status = StepStatus.error
                        final_text = f"_Could not complete: {result.error}_"
                duration_ms = int((time.time() - started) * 1000)

            yield sse.step_event(
                step.model_copy(update={"status": status, "duration_ms": duration_ms})
            )

            # Reveal extracted text after extraction/fetch steps.
            if step.tool in _EXTRACTION_TOOLS or step.tool in _FETCH_TOOLS:
                vis = _visible_docs(ctx.docs)
                if vis:
                    yield sse.extracted_event(vis)
                    extracted_emitted = True

        if not extracted_emitted and _visible_docs(ctx.docs):
            yield sse.extracted_event(_visible_docs(ctx.docs))

        # ---- 5. Actual cost (after execution) ----
        used_model = ctx.model or est_model
        in_tok = ctx.input_tokens or estimate_cost(ctx.combined_context(), used_model).input_tokens or 0
        out_tok = ctx.output_tokens or 0
        yield sse.cost_actual_event(actual_cost(in_tok, out_tok, used_model))

        yield sse.done_event()

    except Exception as exc:  # pragma: no cover - last-resort guard
        yield sse.error_event(f"Agent failed: {exc}")
        yield sse.done_event()


def _chunk(text: str) -> list[str]:
    """Split text into word-ish chunks for token-style streaming."""
    import re

    chunks = re.findall(r"\S+\s*", text)
    return chunks or ([text] if text else [])
