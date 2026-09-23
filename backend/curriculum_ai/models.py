"""Persistence for the document ingestion foundation.

Same conventions as rag/models.py: SQLAlchemy models on the app's one
shared `Base` (app/db/session.py) -- no separate Postgres schema, no
Alembic, `Base.metadata.create_all()` at startup. `status` is a plain
string column (not a native Postgres enum), matching every other status
column in this codebase (`rag.models.RagDocument.status`,
`app.models_db.Lesson.published`-style flags) -- `DocumentStatus` below is
the application-level source of truth for which values are valid.

No hard ForeignKey from `Project.teacher_id` to `users.id`: this package
doesn't import `app.models_db` (avoids a cross-package import cycle risk),
so ownership is enforced in `service.py`, not by a DB constraint -- the
same choice `rag.models.RagDocument.organization_id` already makes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DocumentStatus(StrEnum):
    """The document processing state machine.

    UPLOADED -> QUEUED -> PROCESSING -> PARSED -> INDEXED -> READY
                                                           \\-> FAILED (from any of QUEUED/PROCESSING/PARSED/INDEXED)

    PARSED and INDEXED are transient/observable checkpoints inside one
    processing run (structure extracted; chunked into DocumentChunk rows),
    not places a document is expected to sit for long -- see
    processing.py. No embeddings are computed at this phase, so INDEXED
    means "chunked," not "vectorized."
    """

    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    PARSED = "parsed"
    INDEXED = "indexed"
    READY = "ready"
    FAILED = "failed"


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    """A teacher's curriculum-design workspace -- the container documents
    are uploaded into. Deliberately separate from `app.models_db.Course`
    (the live, published product): a Project is where source material is
    gathered and (in later phases) a curriculum is drafted; it may
    eventually produce a Course, but isn't one."""

    __tablename__ = "curriculum_projects"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("proj"))
    teacher_id: Mapped[str] = mapped_column(index=True)
    title: Mapped[str]
    status: Mapped[str] = mapped_column(default="active")
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)


class Document(Base):
    """One uploaded source file. `storage_key` locates the original bytes
    in object storage (storage/base.py) -- the bytes themselves are never
    in this table (requirement: don't store the PDF binary in Postgres).

    `processing_job_id` + `processing_attempts` are the idempotency/retry
    fencing mechanism -- see processing.py's module docstring for exactly
    how they prevent a redelivered or superseded job from corrupting data."""

    __tablename__ = "curriculum_documents"
    __table_args__ = (Index("ix_curriculum_documents_project_status", "project_id", "status"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("doc"))
    project_id: Mapped[str] = mapped_column(ForeignKey("curriculum_projects.id", ondelete="CASCADE"), index=True)

    original_filename: Mapped[str]
    mime_type: Mapped[str]
    file_size_bytes: Mapped[int]
    checksum_sha256: Mapped[str] = mapped_column(index=True)
    storage_key: Mapped[str]

    status: Mapped[str] = mapped_column(default=DocumentStatus.UPLOADED.value, index=True)
    processing_error: Mapped[str | None] = mapped_column(default=None)
    processing_job_id: Mapped[str | None] = mapped_column(default=None)
    processing_attempts: Mapped[int] = mapped_column(default=0)

    uploaded_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)


class DocumentSection(Base):
    """Structural metadata for one section of a parsed document (heading +
    page range) -- the text itself lives on DocumentChunk rows, not here.
    Deleting the parent Document cascades to this table at the DB level."""

    __tablename__ = "curriculum_document_sections"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("sec"))
    document_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_documents.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str]
    level: Mapped[int] = mapped_column(default=1)
    page_start: Mapped[int | None] = mapped_column(default=None)
    page_end: Mapped[int | None] = mapped_column(default=None)
    order_index: Mapped[int]


class DocumentChunk(Base):
    """One retrievable slice of section text. No embedding column yet --
    added in the retrieval phase, not this one. `document_id` is a direct
    (denormalized) FK in addition to `section_id` so deletion and
    per-document queries don't need a join through sections."""

    __tablename__ = "curriculum_document_chunks"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("chk"))
    document_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_documents.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_document_sections.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str]
    chunk_index: Mapped[int]
    page_number: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class StudyGuideRunStatus(StrEnum):
    """QUEUED -> RUNNING -> COMPLETED | FAILED. One run analyzes one
    document; `total_units`/`completed_units` drive the progress bar."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StudyGuideRun(Base):
    """One execution of the faculty panel (app/agents/faculty) over a
    document. `job_id` fences retries the same way
    `Document.processing_job_id` does -- see analysis/tasks.py."""

    __tablename__ = "curriculum_study_guide_runs"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("run"))
    document_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_documents.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(default=StudyGuideRunStatus.QUEUED.value)
    job_id: Mapped[str | None] = mapped_column(default=None)
    error: Mapped[str | None] = mapped_column(default=None)
    model_id: Mapped[str | None] = mapped_column(default=None)
    total_units: Mapped[int] = mapped_column(default=0)
    completed_units: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)


class StudyGuideUnit(Base):
    """One chapter-sized slice of a document (see analysis/units.py) and
    the Chair's write-up of it. Rebuilt on every run; the teacher-reviewed
    entries below survive a re-run, so they carry their own copy of the
    unit's title and pages rather than a foreign key to this row."""

    __tablename__ = "curriculum_study_guide_units"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("unit"))
    document_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_documents.id", ondelete="CASCADE"), index=True
    )
    order_index: Mapped[int]
    title: Mapped[str]
    page_start: Mapped[int]
    page_end: Mapped[int]
    summary: Mapped[str | None] = mapped_column(default=None)
    learning_objectives: Mapped[list | None] = mapped_column(JSON, default=None)
    status: Mapped[str] = mapped_column(default="pending")  # pending | done | failed
    error: Mapped[str | None] = mapped_column(default=None)


class StudyGuideEntry(Base):
    """One concept, theory, or exercise a specialist pulled out of a unit.
    `data` is the specialist's validated payload (app/agents/faculty/
    schemas.py); `evidence_quote` + pages are the citation, and `grounded`
    records whether that quote was actually found in the source text.

    Nothing here is authoritative until a teacher approves it
    (`review_status`), and a re-run never deletes an approved or
    teacher-edited entry -- mirrors docs/architecture's "never
    automatically delete teacher-created concepts" rule."""

    __tablename__ = "curriculum_study_guide_entries"
    __table_args__ = (Index("ix_curriculum_study_guide_entries_doc_kind", "document_id", "kind"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("entry"))
    document_id: Mapped[str] = mapped_column(
        ForeignKey("curriculum_documents.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str]  # concept | theory | exercise
    unit_order: Mapped[int]
    unit_title: Mapped[str]
    title: Mapped[str]
    data: Mapped[dict] = mapped_column(JSON)
    evidence_quote: Mapped[str | None] = mapped_column(default=None)
    page_start: Mapped[int | None] = mapped_column(default=None)
    page_end: Mapped[int | None] = mapped_column(default=None)
    grounded: Mapped[bool] = mapped_column(default=True)
    review_status: Mapped[str] = mapped_column(default="proposed")  # proposed | approved | rejected
    edited: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    updated_at: Mapped[datetime] = mapped_column(default=_now, onupdate=_now)
