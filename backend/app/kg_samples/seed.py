import json
import logging
import secrets
from pathlib import Path

from sqlalchemy import select

from .. import kg_boards
from ..auth.security import hash_password
from ..db import SessionLocal
from ..models_db import KnowledgeGraphBoard, User
from .catalog import SAMPLES

logger = logging.getLogger(__name__)

# Boards need an owner (`created_by` is a foreign key to users), and the sample
# boards belong to nobody in particular -- so they belong to this account. It
# has a random password nobody is given, so it can't be logged into.
SAMPLES_USER_EMAIL = "samples@educa.local"
SAMPLES_USER_NAME = "Educa Samples"


def _samples_user_id() -> str:
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == SAMPLES_USER_EMAIL))
        if user:
            return user.id
        user = User(
            email=SAMPLES_USER_EMAIL,
            name=SAMPLES_USER_NAME,
            role="teacher",
            password_hash=hash_password(secrets.token_urlsafe(32)),
        )
        session.add(user)
        session.commit()
        return user.id


def seed_samples() -> list[str]:
    """Create every sample board that doesn't exist yet. Existing boards are
    left alone (never re-seeded, never overwritten). Returns the titles created."""
    created = []
    for sample in SAMPLES:
        with SessionLocal() as session:
            if session.get(KnowledgeGraphBoard, sample.board_id):
                logger.info("kg_samples: %s already exists, skipping", sample.board_id)
                continue
        template = json.loads((Path(__file__).parent / sample.file).read_text())
        kg_boards.create_board(_samples_user_id(), template["title"], board_id=sample.board_id)
        try:
            kg_boards.write_graph(sample.board_id, template["nodes"], template["relationships"])
        except Exception:
            # Storage failed (e.g. Liveblocks unreachable): drop the row too, so a failed run leaves nothing half-made.
            kg_boards.delete_board(sample.board_id)
            raise
        created.append(template["title"])
    return created
