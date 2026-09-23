"""End-to-end coverage against real Postgres (local-disk storage swapped in
via the `local_storage` fixture - see test_s3_storage.py for the real S3
backend on its own). Exercises the actual service functions and, for the
router tests, the real FastAPI app + auth.
"""

import sys
from pathlib import Path

import pytest
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).parents[3]))

from app.db.session import SessionLocal  # noqa: E402
from curriculum_ai import service  # noqa: E402
from curriculum_ai.models import Document, DocumentChunk, DocumentSection, DocumentStatus  # noqa: E402
from curriculum_ai.processing import process_document  # noqa: E402


def _counts(document_id: str) -> tuple[int, int]:
    with SessionLocal() as session:
        sections = session.scalar(
            select(DocumentSection.id).where(DocumentSection.document_id == document_id)
        )
        section_count = len(
            list(session.scalars(select(DocumentSection).where(DocumentSection.document_id == document_id)))
        )
        chunk_count = len(list(session.scalars(select(DocumentChunk).where(DocumentChunk.document_id == document_id))))
        return section_count, chunk_count


# --- service-level pipeline -------------------------------------------------


@pytest.mark.integration
def test_upload_then_process_reaches_ready_with_sections_and_chunks(teacher, sample_pdf_bytes):
    doc = service.upload_document(
        teacher["project_id"], teacher["user_id"], "practice_reading.pdf", sample_pdf_bytes, "application/pdf"
    )
    assert doc.status == DocumentStatus.QUEUED.value
    assert doc.processing_job_id is not None
    job_id = doc.processing_job_id

    process_document(doc.id, job_id)

    with SessionLocal() as session:
        refreshed = session.get(Document, doc.id)
        assert refreshed.status == DocumentStatus.READY.value
        assert refreshed.processing_error is None

    section_count, chunk_count = _counts(doc.id)
    assert section_count > 0
    assert chunk_count > 0


@pytest.mark.integration
def test_upload_preserves_required_metadata(teacher, sample_pdf_bytes):
    doc = service.upload_document(
        teacher["project_id"], teacher["user_id"], "practice_reading.pdf", sample_pdf_bytes, "application/pdf"
    )
    assert doc.original_filename == "practice_reading.pdf"
    assert doc.mime_type == "application/pdf"
    assert doc.file_size_bytes == len(sample_pdf_bytes)
    assert len(doc.checksum_sha256) == 64  # sha256 hex digest
    assert doc.uploaded_at is not None
    assert doc.processing_attempts == 1


@pytest.mark.integration
def test_upload_to_nonexistent_project_raises_lookup_error(teacher, sample_pdf_bytes):
    with pytest.raises(LookupError):
        service.upload_document(
            "proj_does_not_exist", teacher["user_id"], "x.pdf", sample_pdf_bytes, "application/pdf"
        )


@pytest.mark.integration
def test_upload_to_someone_elses_project_raises_permission_error(teacher, sample_pdf_bytes):
    with pytest.raises(PermissionError):
        service.upload_document(teacher["project_id"], "some-other-user-id", "x.pdf", sample_pdf_bytes, "application/pdf")


# --- idempotency / job fencing ----------------------------------------------


@pytest.mark.integration
def test_processing_same_job_twice_does_not_duplicate_chunks(teacher, sample_pdf_bytes):
    doc = service.upload_document(
        teacher["project_id"], teacher["user_id"], "practice_reading.pdf", sample_pdf_bytes, "application/pdf"
    )
    job_id = doc.processing_job_id

    process_document(doc.id, job_id)
    _, chunk_count_first = _counts(doc.id)

    process_document(doc.id, job_id)  # simulates a redelivered/duplicate job
    _, chunk_count_second = _counts(doc.id)

    assert chunk_count_first == chunk_count_second
    assert chunk_count_first > 0


@pytest.mark.integration
def test_stale_job_is_superseded_by_a_newer_retry(teacher, sample_pdf_bytes):
    doc = service.upload_document(
        teacher["project_id"], teacher["user_id"], "practice_reading.pdf", sample_pdf_bytes, "application/pdf"
    )
    stale_job_id = doc.processing_job_id

    # A retry mints a new job_id and re-stamps the document before the
    # stale job ever runs (simulating: enqueue, retry, THEN the original
    # worker message finally gets processed).
    with SessionLocal() as session:
        row = session.get(Document, doc.id)
        row.status = DocumentStatus.QUEUED.value
        row.processing_job_id = "a-newer-job-id"
        session.commit()

    process_document(doc.id, stale_job_id)  # the stale job finally runs

    with SessionLocal() as session:
        refreshed = session.get(Document, doc.id)
        # Untouched by the stale job - still queued under the newer job id.
        assert refreshed.status == DocumentStatus.QUEUED.value
        assert refreshed.processing_job_id == "a-newer-job-id"


@pytest.mark.integration
def test_reprocessing_an_already_ready_document_replaces_rather_than_duplicates(teacher, sample_pdf_bytes):
    doc = service.upload_document(
        teacher["project_id"], teacher["user_id"], "practice_reading.pdf", sample_pdf_bytes, "application/pdf"
    )
    process_document(doc.id, doc.processing_job_id)
    section_count_first, chunk_count_first = _counts(doc.id)
    assert chunk_count_first > 0

    # Simulate reprocessing being triggered again for a document that
    # already completed once (e.g. an operator re-running the pipeline) --
    # whatever the trigger, a second full run must replace, not append to,
    # the first attempt's sections/chunks.
    new_job_id = "a-second-processing-run"
    with SessionLocal() as session:
        row = session.get(Document, doc.id)
        row.status = DocumentStatus.QUEUED.value
        row.processing_job_id = new_job_id
        session.commit()

    process_document(doc.id, new_job_id)
    section_count_second, chunk_count_second = _counts(doc.id)

    assert section_count_second == section_count_first
    assert chunk_count_second == chunk_count_first


@pytest.mark.integration
def test_processing_missing_document_is_a_safe_noop():
    process_document("doc_does_not_exist", "some-job-id")  # must not raise


# --- deletion ----------------------------------------------------------------


@pytest.mark.integration
def test_deleting_document_cascades_to_sections_and_chunks(teacher, sample_pdf_bytes):
    doc = service.upload_document(
        teacher["project_id"], teacher["user_id"], "practice_reading.pdf", sample_pdf_bytes, "application/pdf"
    )
    process_document(doc.id, doc.processing_job_id)
    section_count, chunk_count = _counts(doc.id)
    assert section_count > 0 and chunk_count > 0

    service.delete_document(teacher["project_id"], doc.id, teacher["user_id"])

    with SessionLocal() as session:
        assert session.get(Document, doc.id) is None
    section_count_after, chunk_count_after = _counts(doc.id)
    assert section_count_after == 0
    assert chunk_count_after == 0


@pytest.mark.integration
def test_delete_by_non_owner_raises_permission_error(teacher, sample_pdf_bytes):
    doc = service.upload_document(
        teacher["project_id"], teacher["user_id"], "practice_reading.pdf", sample_pdf_bytes, "application/pdf"
    )
    with pytest.raises(PermissionError):
        service.delete_document(teacher["project_id"], doc.id, "some-other-user-id")


# --- retry semantics -----------------------------------------------------------


@pytest.mark.integration
def test_retry_is_rejected_unless_document_failed(teacher, sample_pdf_bytes):
    doc = service.upload_document(
        teacher["project_id"], teacher["user_id"], "practice_reading.pdf", sample_pdf_bytes, "application/pdf"
    )
    process_document(doc.id, doc.processing_job_id)  # -> READY
    with pytest.raises(ValueError, match="failed documents"):
        service.retry_processing(teacher["project_id"], doc.id, teacher["user_id"])


@pytest.mark.integration
def test_retry_after_failure_can_succeed(teacher, sample_pdf_bytes, monkeypatch):
    doc = service.upload_document(
        teacher["project_id"], teacher["user_id"], "practice_reading.pdf", sample_pdf_bytes, "application/pdf"
    )

    # Force a failure the way a real one would surface: point the storage
    # object at a key that doesn't exist, so processing.py's `get()` raises.
    with SessionLocal() as session:
        row = session.get(Document, doc.id)
        row.storage_key = "this/key/does/not/exist.pdf"
        session.commit()

    process_document(doc.id, doc.processing_job_id)
    with SessionLocal() as session:
        failed = session.get(Document, doc.id)
        assert failed.status == DocumentStatus.FAILED.value
        assert failed.processing_error

    # Fix the storage key back and retry.
    with SessionLocal() as session:
        row = session.get(Document, doc.id)
        row.storage_key = doc.storage_key
        session.commit()

    retried = service.retry_processing(teacher["project_id"], doc.id, teacher["user_id"])
    assert retried.status == DocumentStatus.QUEUED.value
    process_document(doc.id, retried.processing_job_id)

    with SessionLocal() as session:
        final = session.get(Document, doc.id)
        assert final.status == DocumentStatus.READY.value
        assert final.processing_error is None
