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

SAMPLE_PAGE_COUNT = 21
_SAMPLE_SENTENCES = [
    "Velocity is the rate of change of position with respect to time.",
    "Acceleration is the rate of change of velocity with respect to time.",
    "An object at rest stays at rest unless a net external force acts on it.",
    "The net force on an object equals its mass multiplied by its acceleration.",
    "For every action there is an equal and opposite reaction between two bodies.",
    "Worked example: a cart accelerates uniformly from rest to 12 m/s in 4 seconds.",
    "Practice problem: find the distance covered by the cart during those 4 seconds.",
]


def make_text_pdf(pages: list[list[str]]) -> bytes:
    """A minimal valid PDF with one Helvetica text block per page. Generated
    rather than read from rag/samples/, which is gitignored -- a fixture that
    needs an untracked file passes locally and errors on a fresh CI checkout."""

    def esc(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    count = len(pages)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(count))
    bodies = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {count} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for i, lines in enumerate(pages):
        bodies.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * i} 0 R >>"
            ).encode()
        )
        stream = ("BT /F1 11 Tf 14 TL 72 720 Td " + " ".join(f"({esc(line)}) Tj T*" for line in lines) + " ET").encode()
        bodies.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(bodies, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(bodies) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(bodies) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    return bytes(out)


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
    """21 pages of ~1,000 characters each -- enough text per page that the
    faculty pipeline's page-window fallback yields three chapters (1-10, 11-20, 21)."""
    pages = [
        [f"[{page}.{line}] {_SAMPLE_SENTENCES[(page + line) % len(_SAMPLE_SENTENCES)]}" for line in range(1, 15)]
        for page in range(1, SAMPLE_PAGE_COUNT + 1)
    ]
    return make_text_pdf(pages)
