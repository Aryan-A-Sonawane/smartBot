"""Unit tests for the deterministic agent core (no network/LLM needed)."""

from __future__ import annotations

from app.agent.critic import validate_summary
from app.agent.planner import detect_intent, plan_request
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
    assert tools == ["pdf_extract", "summarize", "compose"]
    assert not plan.needs_clarification


def test_plan_chain_cross_input_youtube():
    content = "Meeting notes. Video: https://youtu.be/dQw4w9WgXcQ thanks."
    docs = [doc("Text query", "text", "summary please"), doc("m.pdf", "pdf", content)]
    plan = plan_request("Hit the YT URL in this PDF and give me a summary", docs, {"pdf"})
    tools = [s.tool for s in plan.steps]
    assert tools == ["pdf_extract", "youtube_transcript", "summarize", "compose"]


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
