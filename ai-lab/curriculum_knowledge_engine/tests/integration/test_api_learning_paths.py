"""API-level integration tests for /learning-paths and its gap-analysis
sibling. `ClaudeClient.extract` is monkeypatched so these exercise the
real graph traversal (the authoritative part) while replacing only the
narrative-enrichment LLM call.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cke.api.app import create_app
from cke.llm.claude_client import ClaudeClient
from cke.services.learning_path_service import _PlanNarrative


@pytest.fixture
def client(cke_env, monkeypatch):
    def fake_extract(self, prompt, *, output_model, **kwargs):
        assert output_model is _PlanNarrative
        return _PlanNarrative(steps=[], summary="stub summary")

    monkeypatch.setattr(ClaudeClient, "extract", fake_extract)
    with TestClient(create_app()) as test_client:
        test_client.post("/courses/ingest", json={})
        yield test_client


def test_learning_path_orders_prerequisites_before_dependents(client):
    response = client.post(
        "/learning-paths", json={"known_concept_ids": [], "goal_concept_id": "self-attention"}
    )
    assert response.status_code == 200

    step_ids = [step["concept"]["id"] for step in response.json()["steps"]]
    assert step_ids[-1] == "self-attention"
    assert step_ids[-2] == "transformer-architecture"
    assert step_ids[-3] == "neural-networks"
    assert set(step_ids[:-3]) == {"python-programming", "linear-algebra-basics"}


def test_learning_path_excludes_known_concepts(client):
    response = client.post(
        "/learning-paths",
        json={
            "known_concept_ids": ["python-programming", "linear-algebra-basics", "neural-networks"],
            "goal_concept_id": "transformer-architecture",
        },
    )
    assert response.status_code == 200
    step_ids = [step["concept"]["id"] for step in response.json()["steps"]]
    assert step_ids == ["transformer-architecture"]


def test_learning_path_goal_already_known_returns_empty_plan(client):
    response = client.post(
        "/learning-paths",
        json={"known_concept_ids": ["python-programming"], "goal_concept_id": "python-programming"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["steps"] == []
    assert body["total_estimated_minutes"] == 0


def test_learning_path_unknown_goal_returns_404(client):
    response = client.post(
        "/learning-paths", json={"known_concept_ids": [], "goal_concept_id": "does-not-exist"}
    )
    assert response.status_code == 404


def test_gap_analysis_reports_partial_readiness(client):
    response = client.post(
        "/learning-paths/gap-analysis",
        json={
            "known_concept_ids": ["python-programming", "linear-algebra-basics"],
            "target_concept_id": "neural-networks",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["readiness_pct"] == pytest.approx(66.7, abs=0.1)
    assert [c["id"] for c in body["missing_concepts"]] == ["neural-networks"]


def test_gap_analysis_unknown_target_returns_404(client):
    response = client.post(
        "/learning-paths/gap-analysis",
        json={"known_concept_ids": [], "target_concept_id": "does-not-exist"},
    )
    assert response.status_code == 404
