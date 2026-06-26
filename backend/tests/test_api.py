"""End-to-end tests against the /chat SSE endpoint (offline heuristics).

These exercise the assignment's sample test cases at the orchestration level:
the correct tool chain runs, extracted text is surfaced, and the stream ends
cleanly — all without requiring an API key.
"""

from __future__ import annotations

from tests.conftest import parse_sse


def _types(events):
    return [e["type"] for e in events]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_chat_text_only_answer(client):
    r = client.post("/chat", data={"query": "Tell me a fun fact about the moon."})
    assert r.status_code == 200
    events = parse_sse(r.text)
    types = _types(events)
    assert "plan" in types
    assert "cost_estimate" in types
    assert "cost_actual" in types
    assert types[-1] == "done"
    # tokens were streamed
    assert any(e["type"] == "token" for e in events)


def test_chat_clarify_when_file_no_query(client, pdf_bytes_factory):
    pdf = pdf_bytes_factory("Hello world content for the document.")
    r = client.post(
        "/chat",
        data={"query": ""},
        files=[("files", ("doc.pdf", pdf, "application/pdf"))],
    )
    events = parse_sse(r.text)
    types = _types(events)
    assert "clarify" in types
    assert types[-1] == "done"


def test_case2_pdf_action_items(client, pdf_bytes_factory):
    body = (
        "Q3 Planning Meeting Notes. Attendees: team. "
        "Action items: "
        "- Aryan to finalize the agent design by Friday "
        "- Team to review the deployment plan "
        "- Schedule a follow-up next week"
    )
    pdf = pdf_bytes_factory(body)
    r = client.post(
        "/chat",
        data={"query": "What are the action items?"},
        files=[("files", ("notes.pdf", pdf, "application/pdf"))],
    )
    events = parse_sse(r.text)
    plan = next(e for e in events if e["type"] == "plan")
    tools = [s["tool"] for s in plan["steps"]]
    assert "pdf_extract" in tools
    assert "structured_extract" in tools
    # extracted text from the PDF is surfaced
    assert any(e["type"] == "extracted" for e in events)
    extracted = next(e for e in events if e["type"] == "extracted")
    assert any("action" in d["content"].lower() for d in extracted["docs"])
    assert _types(events)[-1] == "done"


def test_case4_pdf_with_youtube_url_chain(client, pdf_bytes_factory):
    body = "Project recap. Watch the demo: https://youtu.be/dQw4w9WgXcQ for details."
    pdf = pdf_bytes_factory(body)
    r = client.post(
        "/chat",
        data={"query": "Hit the YT URL in this PDF and give me a summary of it"},
        files=[("files", ("recap.pdf", pdf, "application/pdf"))],
    )
    events = parse_sse(r.text)
    plan = next(e for e in events if e["type"] == "plan")
    tools = [s["tool"] for s in plan["steps"]]
    assert tools[:2] == ["pdf_extract", "youtube_transcript"]
    assert "summarize" in tools
    assert _types(events)[-1] == "done"


def test_cost_panel_fields(client):
    r = client.post("/chat", data={"query": "Summarize the theory of relativity briefly."})
    events = parse_sse(r.text)
    est = next(e for e in events if e["type"] == "cost_estimate")["cost"]
    assert "estimatedUsd" in est and "inputTokens" in est and "model" in est
