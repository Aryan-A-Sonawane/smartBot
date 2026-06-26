"""Shared pytest fixtures. Tests run fully offline (no GEMINI_API_KEY) and rely
on the agent's graceful heuristic fallbacks.
"""

from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("GEMINI_API_KEY", "")  # force offline heuristics


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def parse_sse(raw: str) -> list[dict]:
    """Parse a raw SSE response body into a list of event dicts."""
    events = []
    for frame in raw.split("\n\n"):
        for line in frame.splitlines():
            if line.startswith("data:"):
                payload = line[5:].strip()
                if payload:
                    events.append(json.loads(payload))
    return events


def make_pdf(text: str) -> bytes:
    """Create a tiny one-page PDF containing the given text (via PyMuPDF)."""
    import fitz  # type: ignore

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=11)
    buf = doc.tobytes()
    doc.close()
    return buf


@pytest.fixture
def pdf_bytes_factory():
    return make_pdf
