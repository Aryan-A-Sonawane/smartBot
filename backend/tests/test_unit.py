"""Unit tests for the deterministic agent core (no network/LLM needed)."""

from __future__ import annotations

import asyncio

from app.agent.critic import validate_summary
from app.agent.planner import detect_intent, plan_request
from app.agent.router import route_intent
from app.schemas import ExtractedDoc
from app.utils import find_url, is_youtube, youtube_id


def doc(source, kind, content):
    return ExtractedDoc(source=source, kind=kind, content=content)


def test_url_and_youtube_detection():
    assert find_url("see https://example.com/page.") == "https://example.com/page"
    assert is_youtube("https://youtu.be/dQw4w9WgXcQ")
    assert youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert not is_youtube("https://example.com")


def test_intent_detection():
    assert detect_intent("please summarize this") == "summarize"
    assert detect_intent("what's the sentiment here") == "sentiment"
    assert detect_intent("explain this code") == "code_explain"
    assert detect_intent("what are the action items") == "structured_extract"
    assert detect_intent("who won the world cup") == "answer"


def test_clarify_gate_files_no_query():
    docs = [doc("notes.pdf", "pdf", "some content")]
    plan = plan_request("", docs, {"pdf"})
    assert plan.needs_clarification
    assert "summarize" in plan.clarify_question.lower()


def test_clarify_gate_ambiguous_short_query():
    docs = [doc("notes.pdf", "pdf", "content")]
    plan = plan_request("this", docs, {"pdf"})
    assert plan.needs_clarification


def test_plan_chain_pdf_summarize():
    docs = [doc("Text query", "text", "summarize this"), doc("a.pdf", "pdf", "x" * 50)]
    plan = plan_request("summarize this", docs, {"pdf"})
    tools = [s.tool for s in plan.steps]
    assert tools == ["understand", "pdf_extract", "summarize", "refine", "compose"]
    assert not plan.needs_clarification


def test_plan_chain_cross_input_youtube():
    content = "Meeting notes. Video: https://youtu.be/dQw4w9WgXcQ thanks."
    docs = [doc("Text query", "text", "summary please"), doc("m.pdf", "pdf", content)]
    plan = plan_request("Hit the YT URL in this PDF and give me a summary", docs, {"pdf"})
    tools = [s.tool for s in plan.steps]
    assert tools == ["understand", "pdf_extract", "youtube_transcript", "summarize", "refine", "compose"]


def test_followup_code_question_routes_to_answer():
    # Prior code doc in memory, no new file this turn: a specific follow-up must
    # be answered conversationally, not re-run through the canned code_explain.
    docs = [
        doc("Text query", "text", "what is the time complexity?"),
        doc("snippet.png", "image", "def f(nums):\n    return sum(nums)/len(nums)"),
    ]
    plan = plan_request("what is the time complexity?", docs, set())
    assert not plan.needs_clarification
    assert [s.tool for s in plan.steps] == ["understand", "answer", "compose"]


def test_initial_code_image_still_uses_code_explain():
    # A freshly uploaded code screenshot keeps the formatted code_explain task.
    docs = [doc("Text query", "text", "explain"), doc("snippet.png", "image", "def f(): pass")]
    plan = plan_request("explain", docs, {"image"})
    tools = [s.tool for s in plan.steps]
    assert "image_ocr" in tools and "code_explain" in tools


def test_explicit_summary_followup_still_summarizes():
    # An explicit strict-format request on a follow-up keeps its tool.
    docs = [doc("Text query", "text", "summarize it"), doc("a.pdf", "pdf", "x" * 80)]
    plan = plan_request("summarize it", docs, set())
    assert [s.tool for s in plan.steps] == ["understand", "summarize", "refine", "compose"]


def test_disambiguation_asks_which_file():
    # Follow-up (no new file) with two docs + a bare command -> ask which file.
    docs = [
        doc("Text query", "text", "explain"),
        doc("a.pdf", "pdf", "x" * 80),
        doc("b.pdf", "pdf", "y" * 80),
    ]
    plan = plan_request("explain", docs, set())
    assert plan.needs_clarification
    assert "a.pdf" in plan.clarify_question and "b.pdf" in plan.clarify_question


def test_named_file_skips_disambiguation():
    # If the query names a file, we don't need to ask which one.
    docs = [
        doc("Text query", "text", "summarize the report"),
        doc("report.pdf", "pdf", "x" * 80),
        doc("notes.pdf", "pdf", "y" * 80),
    ]
    plan = plan_request("summarize the report", docs, set())
    assert not plan.needs_clarification


def test_router_falls_back_when_offline():
    # No API key -> the LLM router returns None so callers use the keyword planner.
    class _Offline:
        configured = False

    assert asyncio.run(route_intent("summarize this", [], _Offline())) is None


def test_youtube_picks_spoken_language_not_translation(monkeypatch):
    # Reported bug: a Hindi video with a Tamil (translated) caption track present
    # was transcribed as Tamil. We must pick the SPOKEN language (the generated
    # track's language), not a translated track.
    import youtube_transcript_api as yta

    from app.tools.youtube import _fetch_transcript

    class _Track:
        def __init__(self, lang, generated, text):
            self.language_code, self.is_generated, self._t = lang, generated, text

        def fetch(self):
            return [{"text": self._t}]

    tracks = [_Track("ta", False, "tamil translation"), _Track("hi", True, "asli hindi")]
    monkeypatch.setattr(yta.YouTubeTranscriptApi, "list_transcripts", staticmethod(lambda v: tracks))

    text, lang = _fetch_transcript("vid12345678")
    assert lang == "hi"
    assert "hindi" in text and "tamil" not in text


def test_summary_validator():
    good = (
        "**One-line summary:** It works.\n\n**Key points**\n- a\n- b\n- c\n\n"
        "**5-sentence summary**\nOne. Two. Three. Four. Five."
    )
    ok, _ = validate_summary(good)
    assert ok
    bad = "**One-line summary:** It works.\n\n- a\n- b"
    ok2, _ = validate_summary(bad)
    assert not ok2
