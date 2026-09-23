"""Orchestration layer: validation, ownership checks, and the upload/list/
get/status/retry/delete flows. Raises plain exceptions the router
translates to HTTP status codes (LookupError -> 404, PermissionError ->
403, ValueError -> 400) -- the same convention rag/service.py already
uses.
"""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select

from app.db.session import SessionLocal

from .jobs.queue import get_queue
from .logging_config import get_logger
from .models import Document, DocumentStatus, Project
from .processing import process_document
from .storage import get_storage

logger = get_logger(__name__)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # matches app/knowledge.py's existing limit
ALLOWED_CONTENT_TYPES = {"application/pdf"}
ALLOWED_EXTENSIONS = {".pdf"}
_PDF_MAGIC = b"%PDF-"


# --- projects -----------------------------------------------------------


def create_project(teacher_id: str, title: str) -> Project:
    with SessionLocal() as session:
        project = Project(teacher_id=teacher_id, title=title)
        session.add(project)
        session.commit()
        session.refresh(project)
        return project


def list_projects(teacher_id: str) -> list[Project]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(Project).where(Project.teacher_id == teacher_id).order_by(Project.created_at.desc())
            )
        )


def _get_project_or_404(session, project_id: str) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise LookupError(f"Project '{project_id}' not found")
    return project


def _assert_owner(project: Project, teacher_id: str) -> None:
    if project.teacher_id != teacher_id:
        raise PermissionError("You don't own this project")


# --- documents ------------------------------------------------------------


def _validate_upload(filename: str, content: bytes, content_type: str) -> None:
    if not content:
        raise ValueError("Uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)}MB)")
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS or content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Only PDF uploads are supported (.pdf, application/pdf)")
    # Trust neither the client-supplied extension nor Content-Type header --
    # uploaded content is untrusted; check the actual file signature.
    if not content.startswith(_PDF_MAGIC):
        raise ValueError("File does not look like a valid PDF (bad file signature)")


def _safe_filename(filename: str) -> str:
    from pathlib import Path

    return Path(filename).name or "document.pdf"


def upload_document(project_id: str, teacher_id: str, filename: str, content: bytes, content_type: str) -> Document:
    with SessionLocal() as session:
        project = _get_project_or_404(session, project_id)
        _assert_owner(project, teacher_id)

    _validate_upload(filename, content, content_type)
    safe_name = _safe_filename(filename)
    checksum = hashlib.sha256(content).hexdigest()

    document_id = f"doc_{uuid.uuid4().hex}"
    storage_key = f"projects/{project_id}/documents/{document_id}/{safe_name}"
    get_storage().put(storage_key, content, content_type)
    logger.info(
        "Stored upload: project=%s document=%s filename=%r size=%d checksum=%s",
        project_id,
        document_id,
        safe_name,
        len(content),
        checksum,
    )

    with SessionLocal() as session:
        doc = Document(
            id=document_id,
            project_id=project_id,
            original_filename=safe_name,
            mime_type=content_type,
            file_size_bytes=len(content),
            checksum_sha256=checksum,
            storage_key=storage_key,
            status=DocumentStatus.UPLOADED.value,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)

    _enqueue_processing(document_id)

    with SessionLocal() as session:
        return session.get(Document, document_id)


def _enqueue_processing(document_id: str) -> str:
    job_id = uuid.uuid4().hex
    with SessionLocal() as session:
        doc = session.get(Document, document_id)
        if doc is None:
            raise LookupError(f"Document '{document_id}' not found")
        doc.status = DocumentStatus.QUEUED.value
        doc.processing_job_id = job_id
        doc.processing_error = None
        doc.processing_attempts += 1
        session.commit()

    try:
        get_queue().enqueue(process_document, document_id, job_id, job_id=job_id, job_timeout=600)
    except Exception:
        # Don't leave the document stuck at QUEUED with no job behind it --
        # land it in FAILED (retryable) instead of an unrecoverable limbo
        # state. Only touch the row if we're still the current job (a
        # concurrent retry could have already superseded this one).
        logger.exception("Failed to enqueue processing job: document=%s job=%s", document_id, job_id)
        with SessionLocal() as session:
            doc = session.get(Document, document_id)
            if doc is not None and doc.processing_job_id == job_id:
                doc.status = DocumentStatus.FAILED.value
                doc.processing_error = "Failed to enqueue processing job (queue unavailable)."
                session.commit()
        raise

    logger.info("Enqueued processing: document=%s job=%s", document_id, job_id)
    return job_id


def _get_document_in_project_or_404(session, project_id: str, document_id: str) -> Document:
    doc = session.get(Document, document_id)
    if doc is None or doc.project_id != project_id:
        raise LookupError(f"Document '{document_id}' not found in project '{project_id}'")
    return doc


def list_documents(project_id: str, teacher_id: str) -> list[Document]:
    with SessionLocal() as session:
        project = _get_project_or_404(session, project_id)
        _assert_owner(project, teacher_id)
        return list(
            session.scalars(
                select(Document).where(Document.project_id == project_id).order_by(Document.uploaded_at.desc())
            )
        )


def get_document(project_id: str, document_id: str, teacher_id: str) -> Document:
    with SessionLocal() as session:
        project = _get_project_or_404(session, project_id)
        _assert_owner(project, teacher_id)
        return _get_document_in_project_or_404(session, project_id, document_id)


def retry_processing(project_id: str, document_id: str, teacher_id: str) -> Document:
    with SessionLocal() as session:
        project = _get_project_or_404(session, project_id)
        _assert_owner(project, teacher_id)
        doc = _get_document_in_project_or_404(session, project_id, document_id)
        if doc.status != DocumentStatus.FAILED.value:
            raise ValueError(f"Only failed documents can be retried (current status: {doc.status})")

    _enqueue_processing(document_id)
    with SessionLocal() as session:
        return session.get(Document, document_id)


def delete_document(project_id: str, document_id: str, teacher_id: str) -> None:
    with SessionLocal() as session:
        project = _get_project_or_404(session, project_id)
        _assert_owner(project, teacher_id)
        doc = _get_document_in_project_or_404(session, project_id, document_id)
        storage_key = doc.storage_key
        # ON DELETE CASCADE (models.py) removes DocumentSection/DocumentChunk
        # rows at the DB level -- satisfies requirement 11 for what exists
        # today; later phases' concept/embedding tables add their own
        # cascading FKs onto documents/chunks rather than this function
        # needing to know about them.
        session.delete(doc)
        session.commit()

    try:
        get_storage().delete(storage_key)
    except Exception:
        # The DB row is already gone -- no user-visible state depends on
        # this succeeding immediately; log for cleanup/alerting instead of
        # failing a delete the user already saw succeed.
        logger.exception("Failed to delete storage object %s for document %s", storage_key, document_id)
    logger.info("Deleted document: project=%s document=%s", project_id, document_id)
