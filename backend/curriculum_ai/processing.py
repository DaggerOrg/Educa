"""The actual parse-and-persist pipeline -- called from a background job
(jobs/tasks.py) but has no RQ/Redis dependency itself, so it's directly
unit/integration-testable by just calling `process_document(...)`.

Reuses rag/parsers.py (format-specific parsing) and rag/chunking.py's
`SectionChunker` (the tested character-window chunking algorithm) rather
than reimplementing either -- this package only owns the NEW persistence
model (Document/DocumentSection/DocumentChunk) and the job-fencing/status
machine below.

--- Idempotency and retry-safety (requirements 7 and 8) ---

Every enqueue (initial upload or a manual retry) mints a fresh
`job_id` and stamps it onto `Document.processing_job_id` *before* the job
is enqueued (see service.py's `_enqueue_processing`). This function then:

1. Atomically claims the document with a single conditional UPDATE
   (`status='queued' AND processing_job_id=:job_id` -> `status='processing'`).
   Exactly one execution of exactly one job can ever win this race --
   RQ's at-least-once delivery, a duplicate enqueue, or two workers
   picking up the same message all lose cleanly (0 rows updated) instead
   of double-processing.
2. Re-reads the document before every side effect. If it's gone
   (deleted mid-processing) or its `processing_job_id` no longer matches
   (superseded by a newer retry that already finished), the run aborts
   without writing anything further.
3. Deletes any prior attempt's DocumentSection/DocumentChunk rows before
   inserting fresh ones -- reprocessing is a destructive replace, not an
   append, so a retry can never leave duplicate or stale chunks behind.

This makes the whole function safe to invoke twice with the same
(document_id, job_id) -- the second call finds status no longer "queued"
and exits at step 1 -- and safe to invoke concurrently for the same
document under two different job_ids -- only the one matching the
document's *current* `processing_job_id` (the most recent enqueue) ever
does work.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, update

from app.db.session import SessionLocal
from rag.chunking import SectionChunker
from rag.domain import ParsedDocument as RagParsedDocument
from rag.parsers import parser_for

from .logging_config import get_logger
from .models import Document, DocumentChunk, DocumentSection, DocumentStatus
from .storage import get_storage

logger = get_logger(__name__)

_chunker = SectionChunker()


def _claim_for_processing(document_id: str, job_id: str) -> bool:
    """Atomically transition queued->processing for this exact job. Returns
    True iff this call won the race (see module docstring, step 1)."""
    with SessionLocal() as session:
        result = session.execute(
            update(Document)
            .where(
                Document.id == document_id,
                Document.processing_job_id == job_id,
                Document.status == DocumentStatus.QUEUED.value,
            )
            .values(status=DocumentStatus.PROCESSING.value)
        )
        session.commit()
        return result.rowcount == 1


def _mark_failed(document_id: str, job_id: str, error: str) -> None:
    with SessionLocal() as session:
        doc = session.get(Document, document_id)
        if doc is None or doc.processing_job_id != job_id:
            # Deleted, or superseded by a newer job -- don't overwrite
            # whatever state that newer job (or the delete) left behind.
            return
        doc.status = DocumentStatus.FAILED.value
        doc.processing_error = error[:2000]
        session.commit()


def process_document(document_id: str, job_id: str) -> None:
    if not _claim_for_processing(document_id, job_id):
        logger.info(
            "process_document(document_id=%s, job_id=%s): not claimed "
            "(already processed, in progress, or superseded) -- skipping",
            document_id,
            job_id,
        )
        return

    logger.info("process_document(document_id=%s, job_id=%s): claimed, starting", document_id, job_id)
    try:
        _run_pipeline(document_id, job_id)
    except Exception as exc:  # noqa: BLE001 - always land in FAILED with the real error, never crash the worker
        logger.exception("process_document(document_id=%s, job_id=%s): failed", document_id, job_id)
        _mark_failed(document_id, job_id, f"{type(exc).__name__}: {exc}")


def _run_pipeline(document_id: str, job_id: str) -> None:
    with SessionLocal() as session:
        doc = session.get(Document, document_id)
        if doc is None:
            logger.warning("Document %s deleted mid-processing (job %s); aborting", document_id, job_id)
            return
        filename, storage_key, project_id = doc.original_filename, doc.storage_key, doc.project_id

    content = get_storage().get(storage_key)
    parsed = parser_for(filename).parse(filename, content)
    if not parsed.sections or not any(section.content.strip() for section in parsed.sections):
        raise ValueError("No readable text found in document (scanned PDFs need OCR, not yet supported)")

    with SessionLocal() as session:
        doc = session.get(Document, document_id)
        if doc is None or doc.processing_job_id != job_id:
            logger.info("Document %s superseded before write (job %s); aborting", document_id, job_id)
            return

        # Idempotent replace: clear any prior attempt's rows first (step 3
        # in the module docstring) so a retry never leaves duplicates.
        session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        session.execute(delete(DocumentSection).where(DocumentSection.document_id == document_id))

        section_rows = []
        for order_index, section in enumerate(parsed.sections):
            row = DocumentSection(
                id=f"sec_{uuid.uuid4().hex}",
                document_id=document_id,
                title=section.title,
                level=section.level,
                page_start=section.page_start,
                page_end=section.page_end,
                order_index=order_index,
            )
            session.add(row)
            section_rows.append(row)
        session.flush()  # assign section ids before chunks reference them

        doc.status = DocumentStatus.PARSED.value
        session.commit()
    logger.info("Document %s (job %s): parsed into %d sections", document_id, job_id, len(section_rows))

    with SessionLocal() as session:
        doc = session.get(Document, document_id)
        if doc is None or doc.processing_job_id != job_id:
            logger.info("Document %s superseded after parse (job %s); aborting", document_id, job_id)
            return

        chunk_index = 0
        for section_row, section in zip(section_rows, parsed.sections):
            single = RagParsedDocument(title=parsed.title, sections=[section])
            for chunk in _chunker.chunk(single, organization_id=project_id, document_id=document_id, course_id=None):
                session.add(
                    DocumentChunk(
                        id=f"chk_{uuid.uuid4().hex}",
                        document_id=document_id,
                        section_id=section_row.id,
                        content=chunk.content,
                        chunk_index=chunk_index,
                        page_number=chunk.page_number,
                    )
                )
                chunk_index += 1

        doc.status = DocumentStatus.INDEXED.value
        session.commit()
    logger.info("Document %s (job %s): indexed into %d chunks", document_id, job_id, chunk_index)

    with SessionLocal() as session:
        doc = session.get(Document, document_id)
        if doc is None or doc.processing_job_id != job_id:
            logger.info("Document %s superseded before ready (job %s); aborting", document_id, job_id)
            return
        doc.status = DocumentStatus.READY.value
        session.commit()
    logger.info("Document %s (job %s): ready", document_id, job_id)

    # Hand the finished document to the faculty panel (analysis/). Best
    # effort: the document is already READY and searchable, so a queue
    # hiccup here must not turn a successful ingestion into a failed one --
    # the teacher can start the analysis manually from the study guide.
    from .analysis.service import auto_analyze_enabled, enqueue_analysis

    if auto_analyze_enabled():
        try:
            enqueue_analysis(document_id)
        except Exception:  # noqa: BLE001
            logger.exception("Document %s: could not enqueue study-guide analysis", document_id)
