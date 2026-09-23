"""One private note document per (student, lesson): a rich-text document
(Tiptap JSON) and a sketch (Excalidraw elements), both stored as JSON --
never visible to teachers or other students.

Same conventions as curriculum_ai/models.py and rag/models.py: plain
SQLAlchemy models on the app's shared `Base`, created by `init_db()`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app import models_db  # noqa: F401  (registers users/lessons so the FKs below resolve)
from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class StudentNote(Base):
    __tablename__ = "student_notes"
    __table_args__ = (UniqueConstraint("student_id", "lesson_id", name="uq_student_note_student_lesson"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: f"note_{uuid.uuid4().hex}")
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str] = mapped_column(index=True)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    doc: Mapped[dict | None] = mapped_column(JSON, default=None)
    sketch: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)
