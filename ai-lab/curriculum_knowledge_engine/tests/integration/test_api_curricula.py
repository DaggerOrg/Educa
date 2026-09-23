"""API-level integration tests for course/concept endpoints, exercised
against the real, bundled AI Engineering sample curriculum - no Claude
calls involved on this path, so no mocking is needed here.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cke.api.app import create_app


@pytest.fixture
def client(cke_env):
    with TestClient(create_app()) as test_client:
        yield test_client


def test_ingest_sample_curriculum(client):
    response = client.post("/courses/ingest", json={})
    assert response.status_code == 201

    body = response.json()
    assert body["course"]["id"] == "ai-engineering-foundations"
    assert body["course"]["module_count"] >= 5
    assert body["course"]["lesson_count"] >= 10


def test_list_and_get_course(client):
    client.post("/courses/ingest", json={})

    list_response = client.get("/courses")
    assert list_response.status_code == 200
    assert [c["id"] for c in list_response.json()] == ["ai-engineering-foundations"]

    detail_response = client.get("/courses/ai-engineering-foundations")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["modules"]) >= 5
    assert any(lesson["id"] == "the-transformer-architecture" for module in detail["modules"] for lesson in module["lessons"])


def test_get_missing_course_returns_404(client):
    response = client.get("/courses/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_concepts_listing_and_centrality(client):
    client.post("/courses/ingest", json={})

    concepts_response = client.get("/concepts")
    assert concepts_response.status_code == 200
    concept_ids = {c["id"] for c in concepts_response.json()}
    assert {"large-language-models", "transformer-architecture", "graphrag"} <= concept_ids

    central_response = client.get("/concepts/central", params={"top_n": 3})
    assert central_response.status_code == 200
    assert len(central_response.json()) == 3


def test_concept_prerequisites_and_dependents(client):
    client.post("/courses/ingest", json={})

    prereqs = client.get("/concepts/graphrag/prerequisites").json()
    assert {c["id"] for c in prereqs} == {"retrieval-augmented-generation", "knowledge-graphs"}

    dependents = client.get("/concepts/large-language-models/dependents").json()
    dependent_ids = {c["id"] for c in dependents}
    assert "prompt-engineering" in dependent_ids
    assert "fine-tuning" in dependent_ids


def test_get_missing_concept_returns_404(client):
    response = client.get("/concepts/does-not-exist")
    assert response.status_code == 404
