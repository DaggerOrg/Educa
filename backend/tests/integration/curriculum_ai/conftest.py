import os
import sys
import uuid
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://educa:educa@localhost:55432/educa")
os.environ.setdefault("CURRICULUM_STORAGE_BACKEND", "local")
sys.path.insert(0, str(Path(__file__).parents[3]))

from app.db.session import SessionLocal  # noqa: E402
from curriculum_ai.models import Project  # noqa: E402
from curriculum_ai.storage import reset_storage_cache  # noqa: E402

SAMPLE_PDF_PATH = Path(__file__).parents[3] / "rag" / "samples" / "esl_practice_reading.pdf"


@pytest.fixture
def local_storage(tmp_path, monkeypatch):
    """Point curriculum_ai's storage factory at a throwaway local-disk
    directory instead of S3/MinIO, for tests that exercise the
    service/router/processing logic rather than the storage backend
    itself (see test_s3_storage.py for that)."""
    monkeypatch.setenv("CURRICULUM_STORAGE_BACKEND", "local")
    # Processing would otherwise enqueue a real study-guide job into Redis for every test document.
    monkeypatch.setenv("STUDY_GUIDE_AUTO_ANALYZE", "false")
    reset_storage_cache()
    from curriculum_ai.storage.local import LocalDiskStorage

    import curriculum_ai.storage as storage_module

    storage_module._storage = LocalDiskStorage(root=tmp_path / "documents")
    yield storage_module._storage
    reset_storage_cache()


@pytest.fixture
def teacher(local_storage):
    """A fresh, real teacher account (via the actual signup flow) plus a
    project owned by it. Tears down by deleting the project, which
    cascades to any documents/sections/chunks the test created."""
    from app.auth import security, store

    email = f"curriculum-test-{uuid.uuid4().hex}@example.com"
    user = store.create_user(email, "Curriculum Test Teacher", security.hash_password("testpass123"), "teacher")
    token = security.create_access_token(user["id"])

    with SessionLocal() as session:
        project = Project(teacher_id=user["id"], title="Test Project")
        session.add(project)
        session.commit()
        session.refresh(project)
        project_id = project.id

    yield {"user_id": user["id"], "headers": {"Authorization": f"Bearer {token}"}, "project_id": project_id}

    with SessionLocal() as session:
        row = session.get(Project, project_id)
        if row is not None:
            session.delete(row)
            session.commit()


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    return SAMPLE_PDF_PATH.read_bytes()
