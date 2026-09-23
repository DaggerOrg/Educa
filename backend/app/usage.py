"""Per-user token accounting and daily caps for the agents this backend runs
directly. A student-facing chat is the obvious abuse/cost surface, so the TA
is capped; the faculty panel is recorded so a teacher's spend on book
analysis is visible.

The check is before-the-run and the record after, so concurrent requests can
overshoot a cap by one run -- fine for a cost guard, not a hard quota.
"""
import logging
import os
from datetime import datetime, timezone

from sqlalchemy import func, select

from .db import SessionLocal
from .models_db import AgentUsage

logger = logging.getLogger(__name__)


class UsageLimitExceeded(RuntimeError):
    pass


def daily_cap(env_var: str, default: int) -> int:
    """`0` (or a negative number) disables the cap."""
    try:
        return int(os.environ.get(env_var, default))
    except ValueError:
        return default


def record(user_id: str, agent: str, model_id: str | None, input_tokens: int, output_tokens: int) -> None:
    try:
        with SessionLocal() as session:
            session.add(
                AgentUsage(
                    user_id=user_id, agent=agent, model_id=model_id,
                    input_tokens=int(input_tokens or 0), output_tokens=int(output_tokens or 0),
                )
            )
            session.commit()
    except Exception:  # noqa: BLE001 - metering must never fail the user's request
        logger.exception("Could not record usage: user=%s agent=%s", user_id, agent)


def tokens_today(user_id: str, agent: str) -> int:
    midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    with SessionLocal() as session:
        total = session.scalar(
            select(func.coalesce(func.sum(AgentUsage.input_tokens + AgentUsage.output_tokens), 0)).where(
                AgentUsage.user_id == user_id, AgentUsage.agent == agent, AgentUsage.created_at >= midnight
            )
        )
        return int(total or 0)


def check_daily_cap(user_id: str, agent: str, cap: int) -> None:
    if cap > 0 and tokens_today(user_id, agent) >= cap:
        raise UsageLimitExceeded(f"Daily usage limit reached for {agent}")
