"""HTTP-level coverage: real FastAPI app, real Postgres, real auth tokens,
local-disk storage (see the `local_storage` fixture). Background
processing is invoked directly (as a worker would run it) rather than
requiring a live RQ worker process during tests.
"""

import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[3]))

from app.auth import security, store  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from curriculum_ai.models import Project  # noqa: E402
from curriculum_ai.processing import process_document  # noqa: E402


@pytest.fixture
def client(local_storage):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def other_teacher(local_storage):
    email = f"other-teacher-{uuid.uuid4().hex}@example.com"
    user = store.create_user(email, "Other Teacher", security.hash_password("testpass123"), "teacher")
    token = security.create_access_token(user["id"])
    yield {"user_id": user["id"], "headers": {"Authorization": f"Bearer {token}"}}


def _upload(client, teacher, sample_pdf_bytes, filename="practice_reading.pdf"):
    return client.post(
        f"/api/curriculum/projects/{teacher['project_id']}/documents",
        headers=teacher["headers"],
        files={"file": (filename, sample_pdf_bytes, "application/pdf")},
    )


@pytest.mark.integration
def test_create_and_list_projects(client, teacher):
    response = client.post("/api/curriculum/projects", headers=teacher["headers"], json={"title": "New Project"})
    assert response.status_code == 201
    created = response.json()
    assert created["title"] == "New Project"

    listed = client.get("/api/curriculum/projects", headers=teacher["headers"])
    assert listed.status_code == 200
    assert any(p["id"] == created["id"] for p in listed.json())

    with SessionLocal() as session:
        row = session.get(Project, created["id"])
        session.delete(row)
        session.commit()


@pytest.mark.integration
def test_upload_returns_202_and_queued_status(client, teacher, sample_pdf_bytes):
    response = _upload(client, teacher, sample_pdf_bytes)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["original_filename"] == "practice_reading.pdf"
    assert body["checksum_sha256"]


@pytest.mark.integration
def test_upload_rejects_non_pdf(client, teacher):
    response = client.post(
        f"/api/curriculum/projects/{teacher['project_id']}/documents",
        headers=teacher["headers"],
        files={"file": ("notes.txt", b"just text", "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.integration
def test_status_reaches_ready_after_processing(client, teacher, sample_pdf_bytes):
    uploaded = _upload(client, teacher, sample_pdf_bytes).json()
    document_id = uploaded["id"]

    status_before = client.get(
        f"/api/curriculum/projects/{teacher['project_id']}/documents/{document_id}/status",
        headers=teacher["headers"],
    )
    assert status_before.json()["status"] == "queued"

    with SessionLocal() as session:
        from curriculum_ai.models import Document

        job_id = session.get(Document, document_id).processing_job_id

    process_document(document_id, job_id)

    status = client.get(
        f"/api/curriculum/projects/{teacher['project_id']}/documents/{document_id}/status",
        headers=teacher["headers"],
    )
    assert status.json()["status"] == "ready"

    detail = client.get(
        f"/api/curriculum/projects/{teacher['project_id']}/documents/{document_id}", headers=teacher["headers"]
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "ready"

    listed = client.get(f"/api/curriculum/projects/{teacher['project_id']}/documents", headers=teacher["headers"])
    assert any(d["id"] == document_id for d in listed.json())


@pytest.mark.integration
def test_retry_endpoint_rejects_non_failed_document(client, teacher, sample_pdf_bytes):
    uploaded = _upload(client, teacher, sample_pdf_bytes).json()
    response = client.post(
        f"/api/curriculum/projects/{teacher['project_id']}/documents/{uploaded['id']}/retry",
        headers=teacher["headers"],
    )
    assert response.status_code == 400  # still queued, not failed


@pytest.mark.integration
def test_delete_endpoint_removes_document(client, teacher, sample_pdf_bytes):
    uploaded = _upload(client, teacher, sample_pdf_bytes).json()
    response = client.delete(
        f"/api/curriculum/projects/{teacher['project_id']}/documents/{uploaded['id']}", headers=teacher["headers"]
    )
    assert response.status_code == 204

    follow_up = client.get(
        f"/api/curriculum/projects/{teacher['project_id']}/documents/{uploaded['id']}", headers=teacher["headers"]
    )
    assert follow_up.status_code == 404


# --- authorization boundaries -------------------------------------------------


@pytest.mark.integration
def test_other_teacher_cannot_upload_to_someone_elses_project(client, teacher, other_teacher, sample_pdf_bytes):
    response = client.post(
        f"/api/curriculum/projects/{teacher['project_id']}/documents",
        headers=other_teacher["headers"],
        files={"file": ("x.pdf", sample_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 403


@pytest.mark.integration
def test_other_teacher_cannot_list_someone_elses_documents(client, teacher, other_teacher, sample_pdf_bytes):
    _upload(client, teacher, sample_pdf_bytes)
    response = client.get(
        f"/api/curriculum/projects/{teacher['project_id']}/documents", headers=other_teacher["headers"]
    )
    assert response.status_code == 403


@pytest.mark.integration
def test_other_teacher_cannot_get_or_delete_a_document(client, teacher, other_teacher, sample_pdf_bytes):
    uploaded = _upload(client, teacher, sample_pdf_bytes).json()

    get_response = client.get(
        f"/api/curriculum/projects/{teacher['project_id']}/documents/{uploaded['id']}",
        headers=other_teacher["headers"],
    )
    assert get_response.status_code == 403

    delete_response = client.delete(
        f"/api/curriculum/projects/{teacher['project_id']}/documents/{uploaded['id']}",
        headers=other_teacher["headers"],
    )
    assert delete_response.status_code == 403


@pytest.mark.integration
def test_unauthenticated_request_is_rejected(client, teacher):
    response = client.get(f"/api/curriculum/projects/{teacher['project_id']}/documents")
    assert response.status_code in (401, 403)
