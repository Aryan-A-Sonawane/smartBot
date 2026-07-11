"""The executor orchestrates a single request end-to-end and yields SSE frames.

Flow: parallel extraction -> plan -> (clarify gate) -> emit plan + cost
estimate -> run each step with live trace + timing -> critic self-correct ->
stream the final answer token-by-token -> emit actual cost -> done.

Errors in any single step degrade gracefully (the step is marked ``error`` and
the run continues) so partial results still reach the user.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import AsyncIterator

from .. import sse
from ..config import Settings
from ..gemini_client import GeminiClient, LLMUnavailable
from ..pipeline import ExtractionOutcome, InputFile, extract_all
from ..pipeline.base import kind_for_mime
from ..pipeline.text import text_doc
from ..schemas import ExtractedDoc, StepStatus, ToolName
from ..tools.base import ToolContext
from ..tools.registry import ToolRegistry
from ..utils import is_cross_input
from .cost import actual_cost, estimate_cost
from .critic import critique
from .planner import build_pipeline, clarify_plan, plan_request
from .router import route_intent

_EXTRACTION_TOOLS: set[ToolName] = {"image_ocr", "pdf_extract", "audio_transcribe"}
_FETCH_TOOLS: set[ToolName] = {"youtube_transcript", "url_fetch"}

# The prompt-engineering strategy each intent tool applies — surfaced in the
# trace so it's clear the agent constructs task-specific prompts (with format
# contracts, ensembles, citations) rather than forwarding the raw query.
_STRATEGY: dict[str, str] = {
    "summarize": "format-constrained prompt (1-line/3-bullet/5-sentence contract)",
    "sentiment": "3-vote ensemble + label/confidence contract",
    "code_explain": "structured code-analysis prompt (bugs + complexity)",
    "structured_extract": "extraction prompt with page-citation instruction",
    "answer": "context-grounded reasoning prompt",
}


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
    prior_docs: list[ExtractedDoc] | None = None,
) -> AsyncIterator[str]:
    try:
        # ---- 1. Parallel extraction of every input ----
        outcomes: list[ExtractionOutcome] = await extract_all(
            files, gemini, settings.whisper_model
        )

        query_doc = [text_doc(query)] if query.strip() else []
        current_docs = [oc.doc for oc in outcomes if oc.ok and oc.doc is not None]
        kinds_present = {kind_for_mime(f.filename, f.content_type) for f in files}

        # Keep the WHOLE chat's documents available (query + just-extracted +
        # everything from earlier). The router decides per-message which are
        # actually relevant — we no longer drop context by keyword guesswork.
        all_docs: list[ExtractedDoc] = query_doc + current_docs
        seen = {d.source for d in all_docs}
        for pd in prior_docs or []:
            if pd.source not in seen:
                all_docs.append(pd)
                seen.add(pd.source)
        all_file_docs = [d for d in all_docs if d.source != "Text query"]

        # Per-tool extraction timing, errors, and a human "what happened" detail.
        ext_duration: dict[str, int] = {}
        ext_error: dict[str, str] = {}
        ext_detail: dict[str, list[str]] = {}
        audio_duration_human = ""
        for oc in outcomes:
            ext_duration[oc.tool] = ext_duration.get(oc.tool, 0) + oc.duration_ms
            ext_detail.setdefault(oc.tool, []).append(_describe_extraction(oc))
            if not oc.ok and oc.error:
                ext_error[oc.tool] = oc.error
            if oc.tool == "audio_transcribe" and oc.metadata.get("duration_human"):
                audio_duration_human = oc.metadata["duration_human"]

        # ---- 2. Route: an LLM decides intent + which documents are relevant.
        # Offline (no key) or empty query -> deterministic keyword planner. ----
        route = await route_intent(query, all_file_docs, gemini) if query.strip() else None
        if route is not None:
            if route.relevant_sources is None:
                docs = all_docs
            else:
                rel = set(route.relevant_sources)
                docs = [d for d in all_docs if d.source == "Text query" or d.source in rel]
            if route.needs_clarification and route.clarify_question:
                plan = clarify_plan(query, docs, route.clarify_question)
            else:
                plan = build_pipeline(query, docs, kinds_present, route.intent)
        else:
            # Keyword planner: fold prior docs in only for follow-ups / cross-input;
            # a single-target request on a fresh upload focuses on that file.
            if (not kinds_present) or is_cross_input(query):
                docs = all_docs
            else:
                docs = query_doc + current_docs
            plan = plan_request(query, docs, kinds_present)

        yield sse.plan_event(plan.steps, intent=plan.intent, goal=plan.goal)

        if plan.needs_clarification:
            # Still surface the "understand" stage so the sufficiency decision
            # (info insufficient -> ask a follow-up) is visible before we ask.
            for step in plan.steps:
                yield sse.step_event(step.model_copy(update={"status": StepStatus.running}))
                yield sse.step_event(step.model_copy(update={"status": StepStatus.done, "duration_ms": 0}))
            # Surface any text we already extracted so the file's content isn't
            # lost while we wait for the user's answer.
            vis = _visible_docs(docs)
            if vis:
                yield sse.extracted_event(vis)
            yield sse.clarify_event(plan.clarify_question)
            yield sse.done_event()
            return

        # ---- 3. Cost estimate (before execution) ----
        ctx = ToolContext(
            query=query,
            docs=docs,
            gemini=gemini,
            prefer_pro=plan.prefer_pro,
            whisper_model=settings.whisper_model,
        )
        est_model = settings.model_for(plan.prefer_pro)
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
            detail: str | None = None

            if step.tool == "understand":
                # Deterministic reasoning stage — the planner already computed
                # its detail (token count, detected intent, clarify-gate result).
                detail = step.detail
                duration_ms = 0

            elif step.tool == "refine":
                # Self-correcting critic pass over the generated output.
                final_text, critic_notes = await critique(
                    final_text, plan.intent, gemini, plan.prefer_pro
                )
                detail = " · ".join(critic_notes) or "validated against format contract"
                duration_ms = int((time.time() - started) * 1000)

            elif step.tool in _EXTRACTION_TOOLS:
                # Work already done in the pipeline; replay timing + result.
                duration_ms = ext_duration.get(step.tool, 0)
                detail = " · ".join(ext_detail.get(step.tool, []))
                if step.tool in ext_error:
                    status = StepStatus.error

            elif step.tool in _FETCH_TOOLS:
                fn = registry.get(step.tool)
                result = await fn(ctx) if fn else None
                duration_ms = int((time.time() - started) * 1000)
                if result is None or not result.ok:
                    status = StepStatus.error
                    detail = (result.error if result else "tool unavailable")
                else:
                    detail = " · ".join(result.notes) or "fetched"

            elif step.tool == "compose":
                # Append audio duration when relevant, then stream tokens.
                if audio_duration_human and "duration" not in final_text.lower():
                    final_text = f"{final_text}\n\n_Audio duration: {audio_duration_human}_"
                for chunk in _chunk(final_text):
                    yield sse.token_event(chunk)
                    await asyncio.sleep(0)  # cooperative flush
                duration_ms = int((time.time() - started) * 1000)
                detail = f"streamed {len(final_text)} chars to the output"

            else:  # intent tool (summarize/sentiment/code_explain/structured_extract/answer)
                fn = registry.get(step.tool)
                if fn is None:
                    status = StepStatus.error
                    detail = "no handler registered"
                else:
                    result = await fn(ctx)
                    notes: list[str] = [_STRATEGY.get(step.tool, "structured prompt")]
                    notes += list(result.notes)
                    if result.ok or result.text:
                        final_text = result.text
                    else:
                        status = StepStatus.error
                        final_text = f"_Could not complete: {result.error}_"
                        notes.append(result.error or "failed")
                    if ctx.model:
                        notes.append(f"model: {ctx.model}")
                    detail = " · ".join(n for n in notes if n)
                duration_ms = int((time.time() - started) * 1000)

            yield sse.step_event(
                step.model_copy(
                    update={"status": status, "duration_ms": duration_ms, "detail": detail}
                )
            )

            # Reveal extracted text after extraction/fetch steps.
            if step.tool in _EXTRACTION_TOOLS or step.tool in _FETCH_TOOLS:
                vis = _visible_docs(ctx.docs)
                if vis:
                    yield sse.extracted_event(vis)
                    extracted_emitted = True

        if not extracted_emitted and _visible_docs(ctx.docs):
            yield sse.extracted_event(_visible_docs(ctx.docs))

        # ---- 5. Suggested follow-up questions (like a modern chat UI) ----
        suggestions = await _suggest_followups(ctx, final_text)
        if suggestions:
            yield sse.suggestions_event(suggestions)

        # ---- 6. Actual cost (after execution) ----
        used_model = ctx.model or est_model
        in_tok = ctx.input_tokens or estimate_cost(ctx.combined_context(), used_model).input_tokens or 0
        out_tok = ctx.output_tokens or 0
        yield sse.cost_actual_event(actual_cost(in_tok, out_tok, used_model))

        yield sse.done_event()

    except Exception as exc:  # pragma: no cover - last-resort guard
        yield sse.error_event(f"Agent failed: {exc}")
        yield sse.done_event()


def _describe_extraction(oc: ExtractionOutcome) -> str:
    """One-line 'what actually happened' for an extraction step's trace detail."""
    if not oc.ok:
        return f"failed: {oc.error}"
    m = oc.metadata
    if oc.tool == "pdf_extract":
        parts = [f"{m.get('pages', '?')} page(s) via PyMuPDF"]
        if m.get("ocr_pages"):
            pages = ", ".join(str(p) for p in m["ocr_pages"])
            parts.append(f"OCR on page(s) {pages} via {m.get('ocr_engine', 'ocr')}")
        if m.get("failed_pages"):
            parts.append(f"{len(m['failed_pages'])} page(s) unreadable")
        return " · ".join(parts)
    if oc.tool == "image_ocr":
        engine = m.get("engine", "ocr")
        conf = oc.doc.ocr_confidence if oc.doc else None
        return f"transcribed via {engine}" + (f" ({round(conf * 100)}% conf)" if conf is not None else "")
    if oc.tool == "audio_transcribe":
        return f"faster-whisper · {m.get('duration_human', '?')}"
    return "extracted"


async def _suggest_followups(ctx: ToolContext, answer: str) -> list[str]:
    """Ask the LLM for 3 likely next questions. Best-effort; [] if unavailable."""
    if not answer or answer.startswith("_Could not"):
        return []
    prompt = (
        "Given the user's request and the assistant's answer, suggest exactly 3 "
        "short, specific follow-up questions the user is likely to ask next. "
        "Return ONLY the questions, one per line, no numbering or bullets.\n\n"
        f"User request: {ctx.query}\n\nAssistant answer:\n{answer[:1500]}"
    )
    try:
        res = await ctx.gemini.generate(prompt, temperature=0.6)
    except LLMUnavailable:
        return []
    ctx.record(res.input_tokens, res.output_tokens, res.model)
    out: list[str] = []
    for line in res.text.splitlines():
        q = re.sub(r"^[\s\-\d.)*•]+", "", line).strip()
        if len(q) > 8:
            out.append(q)
    return out[:3]


def _chunk(text: str) -> list[str]:
    """Split text into word-ish chunks for token-style streaming."""
    chunks = re.findall(r"\S+\s*", text)
    return chunks or ([text] if text else [])
