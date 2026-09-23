"""The sample knowledge-graph boards and the Liveblocks writer they share with
the AI agent. No network or database: httpx is faked, the JSON is read from disk."""
import json
import os
import sys
from pathlib import Path

import pytest

# app.kg_boards creates its DB engine at import time (no connection is made here).
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://educa:educa@localhost:55432/educa")
sys.path.insert(0, str(Path(__file__).parents[3]))

from app import kg_boards  # noqa: E402
from app.kg_samples import catalog  # noqa: E402

pytestmark = pytest.mark.unit

SAMPLES_DIR = Path(catalog.__file__).parent
NODE_TYPES = {"concept", "skill", "learning_objective", "exercise", "resource", "level"}


@pytest.fixture(params=catalog.SAMPLES, ids=lambda s: s.board_id)
def template(request):
    return json.loads((SAMPLES_DIR / request.param.file).read_text())


def test_sample_ids_are_unique():
    assert len({s.board_id for s in catalog.SAMPLES}) == len(catalog.SAMPLES)


def test_template_is_a_well_formed_graph(template):
    node_ids = [n["id"] for n in template["nodes"]]
    assert len(node_ids) == len(set(node_ids))
    assert all(n["type"] in NODE_TYPES for n in template["nodes"])
    assert all(isinstance(n["position"]["x"], int | float) and isinstance(n["position"]["y"], int | float) for n in template["nodes"])
    rel_ids = [r["id"] for r in template["relationships"]]
    assert len(rel_ids) == len(set(rel_ids))
    known = set(node_ids)
    assert all(r["sourceId"] in known and r["targetId"] in known for r in template["relationships"])


def test_template_claims_no_review_or_sources_it_does_not_have(template):
    # A starter template must not present invented citations/scores or pre-approved review state.
    assert all(n["status"] == "needs_review" for n in template["nodes"])
    assert all("sources" not in n and "confidence" not in n for n in template["nodes"])
    assert all(r["teacherApproved"] is False for r in template["relationships"])


class _FakeResponse:
    status_code = 200
    text = ""


@pytest.fixture
def liveblocks(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs["json"]))
        return _FakeResponse()

    monkeypatch.setenv("LIVEBLOCKS_API_KEY", "test-key")
    monkeypatch.setattr(kg_boards.httpx, "post", fake_post)
    return calls


def test_write_graph_creates_the_room_then_writes_storage(liveblocks):
    nodes = [
        {"id": "a", "type": "concept", "name": "A", "status": "needs_review", "position": {"x": 0, "y": 0}, "aliases": ["Alpha"]},
        {"id": "b", "type": "concept", "name": "B", "status": "needs_review", "position": {"x": 260, "y": 0}},
    ]
    relationships = [
        {"id": "r1", "sourceId": "a", "targetId": "b", "type": "prerequisite_of", "evidenceType": "teacher_created", "teacherApproved": False},
        {"id": "dangling", "sourceId": "a", "targetId": "missing", "type": "part_of", "evidenceType": "teacher_created", "teacherApproved": False},
    ]

    kg_boards.write_graph("board1", nodes, relationships)

    (room_url, room_body), (storage_url, storage_body) = liveblocks
    assert room_url.endswith("/v2/rooms") and room_body["id"] == "kg-board:board1"
    assert storage_url.endswith("/v2/rooms/kg-board:board1/storage")
    flow = storage_body["data"]["flow"]["data"]
    stored_nodes = flow["nodes"]["data"]
    assert set(stored_nodes) == {"a", "b"}
    node = stored_nodes["a"]["data"]
    assert node["position"] == {"x": 0, "y": 0}  # position sits beside the node's data, not inside it
    node_data = node["data"]["data"]["node"]["data"]
    assert node_data["aliases"] == ["Alpha"] and "position" not in node_data
    assert set(flow["edges"]["data"]) == {"r1"}  # the edge to a missing node is dropped


def test_seed_graph_marks_ai_proposals_as_needing_review(liveblocks):
    kg_boards.seed_graph(
        "board2",
        [{"id": "x", "type": "concept", "name": "X", "cefr_level": "B1"}, {"id": "y", "type": "skill", "name": "Y"}],
        [{"source_id": "x", "target_id": "y", "type": "teaches"}],
    )

    flow = liveblocks[1][1]["data"]["flow"]["data"]
    node = flow["nodes"]["data"]["x"]["data"]["data"]["data"]["node"]["data"]
    assert node["status"] == "ai_generated" and node["cefrLevel"] == "B1"
    relationship = flow["edges"]["data"]["x->y"]["data"]["data"]["data"]["relationship"]["data"]
    assert relationship["evidenceType"] == "llm_inferred" and relationship["teacherApproved"] is False
