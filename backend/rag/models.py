"""Persistence metadata for the Phase 1 document ingestion flow."""

from datetime import datetime, timezone

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[str] = mapped_column(primary_key=True)
    organization_id: Mapped[str] = mapped_column(index=True)
    course_id: Mapped[str | None] = mapped_column(index=True, default=None)
    filename: Mapped[str]
    title: Mapped[str | None] = mapped_column(default=None)
    storage_path: Mapped[str]
    status: Mapped[str] = mapped_column(default="pending", index=True)
    chunk_count: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(default=None)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)