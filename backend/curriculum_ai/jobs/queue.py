"""RQ (Redis Queue) wiring -- chosen over Celery because this codebase is
synchronous top to bottom already (sync SQLAlchemy sessions, sync
sentence-transformers calls, sync Agno tools); RQ's plain-function,
synchronous-worker model needs no async rewrite to host processing.py's
pipeline. See docs/architecture/educa-ai-architecture.md SS7.
"""

from __future__ import annotations

import os

from redis import Redis
from rq import Queue

QUEUE_NAME = "curriculum_document_processing"

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    return _redis


def get_queue() -> Queue:
    return Queue(QUEUE_NAME, connection=get_redis())


def reset_redis_cache() -> None:
    """Test-only: force the next get_redis() call to reconnect."""
    global _redis
    _redis = None
