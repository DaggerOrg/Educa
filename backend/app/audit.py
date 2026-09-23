"""Audit trail for content-changing agent actions.

Every `requires_confirmation` tool calls `record()` once its change is saved,
so the log answers "what did the AI change, and on whose approval?" without
digging through chat transcripts. It is called *after* the change commits:
if the log write itself fails we log loudly rather than raise, because
failing the tool then would tell the teacher a change failed that in fact
happened.
"""
import logging

from sqlalchemy import select

from .auth.context import current_user_id
from .db import SessionLocal
from .models_db import AgentAuditLog

logger = logging.getLogger(__name__)


def record(action: str, target_id: str | None = None, summary: str = "") -> None:
    try:
        with SessionLocal() as session:
            session.add(
                AgentAuditLog(user_id=current_user_id(), action=action, target_id=target_id, summary=summary[:500])
            )
            session.commit()
    except Exception:  # noqa: BLE001
        logger.exception("AUDIT WRITE FAILED: action=%s target=%s", action, target_id)


def list_for_user(user_id: str, limit: int = 100) -> list[dict]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(AgentAuditLog)
            .where(AgentAuditLog.user_id == user_id)
            .order_by(AgentAuditLog.created_at.desc())
            .limit(limit)
        )
        return [
            {
                "id": r.id, "action": r.action, "targetId": r.target_id,
                "summary": r.summary, "createdAt": r.created_at.isoformat(),
            }
            for r in rows
        ]
