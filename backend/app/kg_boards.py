"""The collaborative knowledge-graph boards list -- the "history" sidebar's
data source (see frontend/src/knowledge-graph/live/BoardHistorySidebar.tsx).

Only board *metadata* (title, creator, timestamp) lives here; the graph
content (nodes/edges) is never persisted through this backend at all -- it
lives in Liveblocks Storage, synced directly between browsers via
`useLiveblocksFlow`, in a room named `kg-board:{board.id}` (see
liveblocks_auth.py's `KG_BOARD_ROOM_PATTERN`).
"""
import logging

from sqlalchemy import select

from .db import SessionLocal
from .models_db import KnowledgeGraphBoard, User

logger = logging.getLogger(__name__)


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


def create_board(created_by: str, title: str) -> dict:
    title = title.strip() or "Untitled graph"
    with SessionLocal() as session:
        board = KnowledgeGraphBoard(title=title, created_by=created_by)
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
