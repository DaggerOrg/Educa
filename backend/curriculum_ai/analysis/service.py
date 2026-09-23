"""Orchestration for the study guide: start a run, read the result, let a
teacher review it. Same conventions as curriculum_ai/service.py -- plain
exceptions the router maps to HTTP codes (LookupError 404, PermissionError
403, ValueError 400) and an ownership check on every project-scoped call.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.db.session import SessionLocal

from ..jobs.queue import get_queue
from ..logging_config import get_logger
from ..models import Document, DocumentStatus, StudyGuideEntry, StudyGuideRun, StudyGuideRunStatus, StudyGuideUnit
from ..service import _assert_owner, _get_document_in_project_or_404, _get_project_or_404
from .tasks import analyze_document

logger = get_logger(__name__)

# A run whose worker died stays "running" forever; past this it may be restarted.
STALE_AFTER = timedelta(minutes=30)
JOB_TIMEOUT_SECONDS = 3600
REVIEW_STATUSES = {"proposed", "approved", "rejected"}


def auto_analyze_enabled() -> bool:
    return os.environ.get("STUDY_GUIDE_AUTO_ANALYZE", "true").lower() not in {"0", "false", "no"}


def _is_active(run: StudyGuideRun) -> bool:
    if run.status not in (StudyGuideRunStatus.QUEUED.value, StudyGuideRunStatus.RUNNING.value):
        return False
    updated = run.updated_at if run.updated_at.tzinfo else run.updated_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - updated < STALE_AFTER


def enqueue_analysis(document_id: str) -> StudyGuideRun:
    """Create a fresh run for a READY document and enqueue it. Internal --
    callers check ownership first (start_analysis) or are the pipeline
    itself (processing.py)."""
    with SessionLocal() as session:
        doc = session.get(Document, document_id)
        if doc is None:
            raise LookupError(f"Document '{document_id}' not found")
        if doc.status != DocumentStatus.READY.value:
            raise ValueError(f"Document must be ready to analyze (current status: {doc.status})")
        existing = list(session.scalars(select(StudyGuideRun).where(StudyGuideRun.document_id == document_id)))
        if any(_is_active(run) for run in existing):
            raise ValueError("Analysis is already in progress for this document")
        session.execute(delete(StudyGuideRun).where(StudyGuideRun.document_id == document_id))
        job_id = uuid.uuid4().hex
        run = StudyGuideRun(document_id=document_id, job_id=job_id)
        session.add(run)
        session.commit()
        run_id = run.id

    try:
        get_queue().enqueue(analyze_document, run_id, job_id, job_id=job_id, job_timeout=JOB_TIMEOUT_SECONDS)
    except Exception:
        logger.exception("Failed to enqueue analysis: run=%s", run_id)
        with SessionLocal() as session:
            run = session.get(StudyGuideRun, run_id)
            if run is not None:
                run.status = StudyGuideRunStatus.FAILED.value
                run.error = "Failed to enqueue analysis job (queue unavailable)."
                session.commit()
        raise
    logger.info("Enqueued analysis: document=%s run=%s", document_id, run_id)
    with SessionLocal() as session:
        return session.get(StudyGuideRun, run_id)


def start_analysis(project_id: str, document_id: str, teacher_id: str) -> StudyGuideRun:
    with SessionLocal() as session:
        _assert_owner(_get_project_or_404(session, project_id), teacher_id)
        _get_document_in_project_or_404(session, project_id, document_id)
    return enqueue_analysis(document_id)


def get_study_guide(project_id: str, document_id: str, teacher_id: str) -> dict:
    with SessionLocal() as session:
        _assert_owner(_get_project_or_404(session, project_id), teacher_id)
        _get_document_in_project_or_404(session, project_id, document_id)
        run = session.scalar(
            select(StudyGuideRun).where(StudyGuideRun.document_id == document_id).order_by(StudyGuideRun.created_at.desc())
        )
        units = list(
            session.scalars(
                select(StudyGuideUnit).where(StudyGuideUnit.document_id == document_id).order_by(StudyGuideUnit.order_index)
            )
        )
        entries = list(
            session.scalars(
                select(StudyGuideEntry)
                .where(StudyGuideEntry.document_id == document_id)
                .order_by(StudyGuideEntry.unit_order, StudyGuideEntry.created_at)
            )
        )
        return {"run": run, "units": units, "entries": entries}


def update_entry(
    project_id: str,
    document_id: str,
    entry_id: str,
    teacher_id: str,
    review_status: str | None = None,
    title: str | None = None,
    data: dict | None = None,
) -> StudyGuideEntry:
    if review_status is not None and review_status not in REVIEW_STATUSES:
        raise ValueError(f"review_status must be one of {sorted(REVIEW_STATUSES)}")
    with SessionLocal() as session:
        _assert_owner(_get_project_or_404(session, project_id), teacher_id)
        _get_document_in_project_or_404(session, project_id, document_id)
        entry = session.get(StudyGuideEntry, entry_id)
        if entry is None or entry.document_id != document_id:
            raise LookupError(f"Entry '{entry_id}' not found in document '{document_id}'")

        if review_status is not None:
            entry.review_status = review_status
        if title is not None:
            if not title.strip():
                raise ValueError("title cannot be empty")
            entry.title = title.strip()
            entry.edited = True
        if data is not None:
            # Edit the fields the specialist produced; don't let a PATCH invent new ones or change a field's type.
            unknown = set(data) - set(entry.data)
            if unknown:
                raise ValueError(f"Unknown field(s) for a {entry.kind}: {sorted(unknown)}")
            for key, value in data.items():
                if type(value) is not type(entry.data[key]):
                    raise ValueError(f"Field '{key}' must be a {type(entry.data[key]).__name__}")
            entry.data = {**entry.data, **data}
            entry.edited = True
        session.commit()
        return entry
