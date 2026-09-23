from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app import models_db  # noqa: F401  (registers modules so the FK below resolves)
from app.db.session import Base


class VideoStatus(StrEnum):
    """DRAFT (script being written/edited) -> APPROVED (teacher signed off on
    the script) -> QUEUED -> RENDERING -> READY | FAILED. Editing the script
    at any point sends it back to DRAFT and drops any in-flight render."""

    DRAFT = "draft"
    APPROVED = "approved"
    QUEUED = "queued"
    RENDERING = "rendering"
    READY = "ready"
    FAILED = "failed"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ModuleVideo(Base):
    """At most one story per module. `job_id` fences render jobs the same way
    `curriculum_ai.models.Document.processing_job_id` fences document jobs:
    only the job whose id matches may claim or finish the row."""

    __tablename__ = "module_videos"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: f"mvid_{uuid.uuid4().hex}")
    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"), unique=True, index=True)
    course_id: Mapped[str] = mapped_column(index=True)
    teacher_id: Mapped[str] = mapped_column(index=True)

    status: Mapped[str] = mapped_column(default=VideoStatus.DRAFT.value)
    style: Mapped[str] = mapped_column(default="")
    script: Mapped[dict | None] = mapped_column(JSON, default=None)
    model_id: Mapped[str | None] = mapped_column(default=None)

    provider: Mapped[str | None] = mapped_column(default=None)
    job_id: Mapped[str | None] = mapped_column(default=None)
    # {"kind": "storyboard"} or {"kind": "video", "storage_key": ..., "content_type": ...}
    result: Mapped[dict | None] = mapped_column(JSON, default=None)
    error: Mapped[str | None] = mapped_column(default=None)

    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)
