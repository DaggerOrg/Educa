"""Coverage for the real S3-compatible backend (requirement: store the
original PDF in S3-compatible storage). Needs MinIO running
(`docker compose up -d minio`, see backend/README or .env.example) -- the
rest of the suite uses local-disk storage instead so it isn't coupled to
MinIO being up; this file is what actually proves the S3 backend works.
"""

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))

from curriculum_ai.storage.s3 import S3ObjectStorage  # noqa: E402


@pytest.fixture
def storage() -> S3ObjectStorage:
    return S3ObjectStorage(bucket="educa-curriculum-documents-test")


@pytest.mark.integration
def test_put_then_get_round_trips_bytes(storage):
    key = f"test/{uuid.uuid4().hex}.pdf"
    storage.put(key, b"%PDF-1.4 hello", "application/pdf")
    try:
        assert storage.get(key) == b"%PDF-1.4 hello"
    finally:
        storage.delete(key)


@pytest.mark.integration
def test_delete_removes_the_object(storage):
    key = f"test/{uuid.uuid4().hex}.pdf"
    storage.put(key, b"data", "application/pdf")
    storage.delete(key)
    with pytest.raises(Exception):
        storage.get(key)


@pytest.mark.integration
def test_delete_of_missing_key_does_not_raise(storage):
    storage.delete(f"test/never-existed-{uuid.uuid4().hex}.pdf")  # must not raise


@pytest.mark.integration
def test_overwrite_replaces_content(storage):
    key = f"test/{uuid.uuid4().hex}.pdf"
    storage.put(key, b"first", "application/pdf")
    storage.put(key, b"second", "application/pdf")
    try:
        assert storage.get(key) == b"second"
    finally:
        storage.delete(key)
