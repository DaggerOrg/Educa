"""API-level integration tests for /qa/ask. `ClaudeClient.complete` is
monkeypatched at the class level (no API key exists in this environment)
so these tests exercise the full retrieval pipeline and only replace the
final generation call.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cke.api.app import create_app
from cke.llm.claude_client import ClaudeClient


@pytest.fixture
def client(cke_env, monkeypatch):
    monkeypatch.setattr(ClaudeClient, "complete", lambda self, prompt, **kw: "Canned grounded answer. [1]")
    with TestClient(create_app()) as test_client:
        yield test_client


def test_ask_with_indexed_content_returns_grounded_answer(client):
    client.post("/courses/ingest", json={})

    response = client.post("/qa/ask", json={"question": "What does self-attention compute?"})
    assert response.status_code == 200

    body = response.json()
    assert body["answer"] == "Canned grounded answer. [1]"
    assert len(body["citations"]) > 0
    assert all(0.0 <= c["relevance_score"] <= 1.0 for c in body["citations"])


def test_ask_with_no_indexed_content_skips_llm_and_returns_canned_answer(client):
    response = client.post("/qa/ask", json={"question": "anything at all"})
    assert response.status_code == 200
    assert "indexed curriculum content" in response.json()["answer"]
    assert response.json()["citations"] == []


def test_ask_rejects_empty_question(client):
    response = client.post("/qa/ask", json={"question": ""})
    assert response.status_code == 422


def test_ask_can_scope_to_a_course(client):
    client.post("/courses/ingest", json={})

    response = client.post(
        "/qa/ask",
        json={"question": "What is a transformer?", "course_id": "a-course-that-does-not-exist"},
    )
    assert response.status_code == 200
    assert response.json()["citations"] == []
