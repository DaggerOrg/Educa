"""The collaborative knowledge-graph boards list -- the "history" sidebar's
data source (see frontend/src/knowledge-graph/live/BoardHistorySidebar.tsx).

Only board *metadata* (title, creator, timestamp) lives here; the graph
content (nodes/edges) is never persisted through this backend at all -- it
lives in Liveblocks Storage, synced directly between browsers via
`useLiveblocksFlow`, in a room named `kg-board:{board.id}` (see
liveblocks_auth.py's `KG_BOARD_ROOM_PATTERN`).
"""
import logging
import os

import httpx
from sqlalchemy import select

from .db import SessionLocal
from .models_db import KnowledgeGraphBoard, User

logger = logging.getLogger(__name__)

# Matches liveblocks_auth.py's KG_BOARD_ROOM_PATTERN ("kg-board:*") -- every
# board's room is named with this prefix plus the board's own id.
ROOM_PREFIX = "kg-board:"
_GRID_COLUMNS = 4
_GRID_SPACING_X = 260
_GRID_SPACING_Y = 160


def _serialize(board: KnowledgeGraphBoard, author: User) -> dict:
    return {
        "id": board.id,
        "title": board.title,
        "createdBy": board.created_by,
        "createdByName": author.name,
        "createdAt": board.created_at.isoformat(),
    }


def list_boards() -> list[dict]:
    with SessionLocal() as session:
        boards = session.scalars(
            select(KnowledgeGraphBoard).order_by(KnowledgeGraphBoard.created_at.desc())
        ).all()
        author_ids = {b.created_by for b in boards}
        authors = {u.id: u for u in session.scalars(select(User).where(User.id.in_(author_ids)))} if author_ids else {}
        return [_serialize(b, authors[b.created_by]) for b in boards]


def create_board(created_by: str, title: str, board_id: str | None = None) -> dict:
    title = title.strip() or "Untitled graph"
    with SessionLocal() as session:
        board = KnowledgeGraphBoard(title=title, created_by=created_by)
        if board_id:
            board.id = board_id
        session.add(board)
        session.commit()
        author = session.get(User, created_by)
        logger.info("create_board: author=%s board=%s", created_by, board.id)
        return _serialize(board, author)


def rename_board(board_id: str, title: str) -> dict | None:
    title = title.strip()
    if not title:
        raise ValueError("Title can't be empty")
    with SessionLocal() as session:
        board = session.get(KnowledgeGraphBoard, board_id)
        if not board:
            return None
        board.title = title
        session.commit()
        author = session.get(User, board.created_by)
        return _serialize(board, author)


def delete_board(board_id: str) -> bool:
    with SessionLocal() as session:
        board = session.get(KnowledgeGraphBoard, board_id)
        if not board:
            return False
        session.delete(board)
        session.commit()
        logger.info("delete_board: board=%s", board_id)
        return True


def _liveblocks_headers() -> dict:
    return {"Authorization": f"Bearer {os.environ['LIVEBLOCKS_API_KEY']}"}


def _live_object(data: dict) -> dict:
    return {"liveblocksType": "LiveObject", "data": data}


def _live_map(data: dict) -> dict:
    return {"liveblocksType": "LiveMap", "data": data}


def write_graph(board_id: str, nodes: list[dict], relationships: list[dict]) -> None:
    """Populate a board's Liveblocks room with a graph, so it opens already
    showing one instead of a blank canvas. Shared by everything that seeds a
    board (the AI agent's proposals via `seed_graph`, and the sample boards in
    `kg_samples/`).

    `nodes` / `relationships` are `KnowledgeNode` / `KnowledgeRelationship`
    dicts exactly as the frontend reads them (camelCase; see
    frontend/src/knowledge-graph/types/knowledgeGraph.ts). Each node also
    carries a `position` {x, y}, which React Flow keeps beside the node
    rather than inside it. Relationships whose endpoints aren't in `nodes`
    are skipped.

    Talks to Liveblocks' REST API directly (no Python SDK exists): first
    creates the room (the frontend's RoomProvider would do this on first
    connect, but nobody's connected yet), then initializes its Storage in
    one shot via `POST .../storage`, using the exact LSON shape
    `@liveblocks/react-flow`'s `useLiveblocksFlow` expects under its
    default storage key `"flow"` -- a LiveObject with `nodes`/`edges`
    LiveMaps, each keyed by node/relationship id. Only the *envelope*
    objects -- the flow root, each node, each node's `data`, each
    `data.node` -- need the `liveblocksType` wrapper; everything inside them
    is plain JSON, and `position`/`markerEnd` are React Flow "atomic" fields
    that stay plain JSON too, never wrapped.
    """
    room_id = f"{ROOM_PREFIX}{board_id}"
    create_resp = httpx.post(
        "https://api.liveblocks.io/v2/rooms",
        headers=_liveblocks_headers(),
        json={"id": room_id, "defaultAccesses": []},
        timeout=10,
    )
    if create_resp.status_code not in (200, 201) and "already exists" not in create_resp.text.lower():
        raise RuntimeError(f"Failed to create Liveblocks room for board: {create_resp.text}")

    node_ids = {n["id"] for n in nodes}
    node_map = {}
    for n in nodes:
        node_data = {k: v for k, v in n.items() if k != "position"}
        node_map[n["id"]] = _live_object({
            "id": n["id"],
            "type": "knowledge",
            "position": n["position"],
            "data": _live_object({"node": _live_object(node_data)}),
        })

    edge_map = {}
    for r in relationships:
        if r["sourceId"] not in node_ids or r["targetId"] not in node_ids:
            continue
        edge_map[r["id"]] = _live_object({
            "id": r["id"],
            "type": "knowledge",
            "source": r["sourceId"],
            "target": r["targetId"],
            "markerEnd": {"type": "arrowclosed"},
            "data": _live_object({"relationship": _live_object(r)}),
        })

    storage_body = _live_object({
        "flow": _live_object({
            "nodes": _live_map(node_map),
            "edges": _live_map(edge_map),
        }),
    })
    storage_resp = httpx.post(
        f"https://api.liveblocks.io/v2/rooms/{room_id}/storage",
        headers=_liveblocks_headers(),
        json=storage_body,
        timeout=15,
    )
    if storage_resp.status_code >= 300:
        raise RuntimeError(f"Failed to seed knowledge graph storage: {storage_resp.text}")
    logger.info("write_graph: board=%s nodes=%d relationships=%d", board_id, len(node_map), len(edge_map))


def seed_graph(board_id: str, nodes: list[dict], relationships: list[dict]) -> None:
    """Seed a freshly-created board with AI-proposed nodes/relationships --
    called right after `create_board` by agents/knowledge_graph/tools.py.

    These are proposed AI content, not a teacher's own work -- `status:
    "ai_generated"` and `evidenceType: "llm_inferred"` /
    `teacherApproved: False` reuse the same review-state vocabulary
    KnowledgeNodeCard/KnowledgeEdgeLine already render (blue "AI Generated"
    dot, dashed amber pending edges) for the mock example graph, so a
    freshly-generated board visibly reads as "needs review", same as there.
    """
    graph_nodes = []
    for i, n in enumerate(nodes):
        node = {"id": n["id"], "type": n["type"], "name": n["name"], "status": "ai_generated"}
        if n.get("cefr_level"):
            node["cefrLevel"] = n["cefr_level"]
        node["position"] = {"x": (i % _GRID_COLUMNS) * _GRID_SPACING_X, "y": (i // _GRID_COLUMNS) * _GRID_SPACING_Y}
        graph_nodes.append(node)

    graph_relationships = [
        {
            "id": f"{r['source_id']}->{r['target_id']}",
            "sourceId": r["source_id"],
            "targetId": r["target_id"],
            "type": r["type"],
            "evidenceType": "llm_inferred",
            "teacherApproved": False,
        }
        for r in relationships
    ]
    write_graph(board_id, graph_nodes, graph_relationships)
