"""End-to-end tests against the /chat SSE endpoint (offline heuristics).

These exercise the assignment's sample test cases at the orchestration level:
the correct tool chain runs, extracted text is surfaced, and the stream ends
cleanly — all without requiring an API key.
"""

from __future__ import annotations

import json

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
    assert tools == [
        "understand", "pdf_extract", "youtube_transcript", "summarize", "refine", "compose",
    ]
    assert _types(events)[-1] == "done"


def test_trace_exposes_intent_goal_and_detail(client, pdf_bytes_factory):
    # The agent-activity trace must be prompt-specific: it carries the detected
    # intent + an understood-goal line, and each step reports what actually ran.
    pdf = pdf_bytes_factory("Action items: - ship the API - write the docs")
    r = client.post(
        "/chat",
        data={"query": "What are the action items?"},
        files=[("files", ("notes.pdf", pdf, "application/pdf"))],
    )
    events = parse_sse(r.text)
    plan = next(e for e in events if e["type"] == "plan")
    assert plan["intent"] == "structured_extract"
    assert plan["goal"]  # non-empty understood-goal statement
    done_steps = [e["step"] for e in events if e["type"] == "step" and e["step"].get("detail")]
    assert any(s["tool"] == "pdf_extract" and "PyMuPDF" in s["detail"] for s in done_steps)


def test_case_sentiment_analysis(client):
    # Sentiment task: routes to the sentiment tool and returns the
    # label + confidence + justification contract (offline heuristic here).
    r = client.post(
        "/chat",
        data={"query": "What's the sentiment of this review: I absolutely love this product, best purchase ever!"},
    )
    events = parse_sse(r.text)
    plan = next(e for e in events if e["type"] == "plan")
    assert [s["tool"] for s in plan["steps"]] == ["understand", "sentiment", "refine", "compose"]
    answer = "".join(e["text"] for e in events if e["type"] == "token")
    assert "Sentiment:" in answer and "Confidence:" in answer
    assert _types(events)[-1] == "done"


def test_cost_panel_fields(client):
    r = client.post("/chat", data={"query": "Summarize the theory of relativity briefly."})
    events = parse_sse(r.text)
    est = next(e for e in events if e["type"] == "cost_estimate")["cost"]
    assert "estimatedUsd" in est and "inputTokens" in est and "model" in est


def test_clarify_turn_surfaces_extracted(client, pdf_bytes_factory):
    # A file uploaded with no query stops to ask — but its extracted content must
    # still be surfaced (and thus remembered), not silently lost.
    pdf = pdf_bytes_factory("Document content that should still be extracted.")
    r = client.post(
        "/chat", data={"query": ""}, files=[("files", ("doc.pdf", pdf, "application/pdf"))]
    )
    events = parse_sse(r.text)
    types = _types(events)
    assert "clarify" in types
    assert "extracted" in types
    assert types[-1] == "done"


def test_new_file_is_focus_not_prior_memory(client, pdf_bytes_factory):
    # A bare command on a freshly-uploaded file must act on THAT file; an older
    # doc in memory must not be dragged in (the reported "explain hit wrong file").
    new_pdf = pdf_bytes_factory("EC2 config: t3.micro in us-east-1, security group sg-123.")
    prior = json.dumps([{"source": "meeting-notes.pdf", "kind": "pdf", "content": "[Page 1] Q3 planning notes."}])
    r = client.post(
        "/chat",
        data={"query": "summarize this", "prior_context": prior},
        files=[("files", ("aws-config.pdf", new_pdf, "application/pdf"))],
    )
    events = parse_sse(r.text)
    extracted = next(e for e in events if e["type"] == "extracted")
    sources = {d["source"] for d in extracted["docs"]}
    assert "aws-config.pdf" in sources
    assert "meeting-notes.pdf" not in sources
    assert _types(events)[-1] == "done"


def test_cross_input_query_keeps_prior_memory(client, pdf_bytes_factory):
    # A cross-input query DOES pull the earlier doc back in.
    new_pdf = pdf_bytes_factory("Doc B is about solar power adoption.")
    prior = json.dumps([{"source": "old.pdf", "kind": "pdf", "content": "[Page 1] Doc A is about wind power."}])
    r = client.post(
        "/chat",
        data={"query": "compare this with the earlier document", "prior_context": prior},
        files=[("files", ("new.pdf", new_pdf, "application/pdf"))],
    )
    events = parse_sse(r.text)
    extracted = next(e for e in events if e["type"] == "extracted")
    sources = {d["source"] for d in extracted["docs"]}
    assert {"new.pdf", "old.pdf"} <= sources
    assert _types(events)[-1] == "done"


def test_followup_uses_prior_context(client):
    # A follow-up turn ships the previously extracted doc back as prior_context;
    # the agent must reuse it (no re-upload, no clarify) and act on it.
    prior = json.dumps(
        [{"source": "report.pdf", "kind": "pdf", "content": "[Page 1]\nRevenue grew 20% in Q3."}]
    )
    r = client.post("/chat", data={"query": "Summarize it.", "prior_context": prior})
    events = parse_sse(r.text)
    types = _types(events)
    assert "clarify" not in types
    plan = next(e for e in events if e["type"] == "plan")
    assert [s["tool"] for s in plan["steps"]] == ["understand", "summarize", "refine", "compose"]
    extracted = next(e for e in events if e["type"] == "extracted")
    assert any(d["source"] == "report.pdf" for d in extracted["docs"])
    assert types[-1] == "done"


def _stub_extractor(monkeypatch, name, kind, content, **meta):
    """Replace a pipeline extractor with a deterministic stub.

    Audio/image extraction needs Whisper/Tesseract/Gemini, none of which run in
    the offline test env, so we inject a fixed transcript to exercise the full
    orchestration (plan -> execute -> extracted panel -> stream) end to end.
    """
    from app.pipeline import dispatch
    from app.pipeline.base import ExtractionOutcome
    from app.schemas import ExtractedDoc

    async def stub(file, *_args, **_kwargs):
        doc = ExtractedDoc(source=file.filename, kind=kind, content=content)
        return ExtractionOutcome(doc=doc, tool=meta.pop("tool"), metadata=meta)

    monkeypatch.setattr(dispatch, name, stub)


def test_case1_audio_transcription_summary(client, monkeypatch):
    _stub_extractor(
        monkeypatch,
        "extract_audio",
        "audio",
        "(audio duration: 5m 00s)\nToday's lecture covers photosynthesis and its two stages.",
        tool="audio_transcribe",
        duration_human="5m 00s",
    )
    r = client.post(
        "/chat",
        data={"query": "Transcribe and summarize this lecture."},
        files=[("files", ("lecture.mp3", b"fake-audio", "audio/mpeg"))],
    )
    events = parse_sse(r.text)
    plan = next(e for e in events if e["type"] == "plan")
    assert [s["tool"] for s in plan["steps"]] == [
        "understand", "audio_transcribe", "summarize", "refine", "compose",
    ]
    extracted = next(e for e in events if e["type"] == "extracted")
    assert any("photosynthesis" in d["content"] for d in extracted["docs"])
    assert _types(events)[-1] == "done"


def test_case3_image_code_explain(client, monkeypatch):
    _stub_extractor(
        monkeypatch,
        "extract_image",
        "image",
        "def add(a, b):\n    return a + b",
        tool="image_ocr",
    )
    r = client.post(
        "/chat",
        data={"query": "Explain this code and flag any bugs."},
        files=[("files", ("snippet.png", b"fake-image", "image/png"))],
    )
    events = parse_sse(r.text)
    plan = next(e for e in events if e["type"] == "plan")
    assert [s["tool"] for s in plan["steps"]] == [
        "understand", "image_ocr", "code_explain", "refine", "compose",
    ]
    extracted = next(e for e in events if e["type"] == "extracted")
    assert any("def add" in d["content"] for d in extracted["docs"])
    assert _types(events)[-1] == "done"


def test_case5_multi_input_cross_reasoning(client, monkeypatch, pdf_bytes_factory):
    _stub_extractor(
        monkeypatch,
        "extract_audio",
        "audio",
        "(audio duration: 3m 10s)\nThe talk is about renewable solar energy adoption.",
        tool="audio_transcribe",
        duration_human="3m 10s",
    )
    pdf = pdf_bytes_factory("This report analyses solar energy adoption across regions.")
    r = client.post(
        "/chat",
        data={"query": "Do the audio and the document discuss the same topic?"},
        files=[
            ("files", ("report.pdf", pdf, "application/pdf")),
            ("files", ("talk.mp3", b"fake-audio", "audio/mpeg")),
        ],
    )
    events = parse_sse(r.text)
    plan = next(e for e in events if e["type"] == "plan")
    tools = [s["tool"] for s in plan["steps"]]
    # both inputs are extracted, then a single reasoning tool answers across them
    assert "pdf_extract" in tools and "audio_transcribe" in tools
    assert "answer" in tools and tools[-1] == "compose"
    extracted = next(e for e in events if e["type"] == "extracted")
    sources = {d["kind"] for d in extracted["docs"]}
    assert {"pdf", "audio"} <= sources
    assert _types(events)[-1] == "done"
