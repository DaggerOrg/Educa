import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))

from curriculum_ai.storage.local import LocalDiskStorage


@pytest.fixture
def storage(tmp_path) -> LocalDiskStorage:
    return LocalDiskStorage(root=tmp_path / "documents")


@pytest.mark.unit
def test_put_then_get_round_trips_bytes(storage):
    storage.put("projects/p1/documents/d1/file.pdf", b"%PDF-1.4 hello", "application/pdf")
    assert storage.get("projects/p1/documents/d1/file.pdf") == b"%PDF-1.4 hello"


@pytest.mark.unit
def test_put_creates_nested_directories(storage, tmp_path):
    storage.put("a/b/c/file.pdf", b"data", "application/pdf")
    assert (tmp_path / "documents" / "a" / "b" / "c" / "file.pdf").read_bytes() == b"data"


@pytest.mark.unit
def test_delete_removes_the_file(storage):
    storage.put("file.pdf", b"data", "application/pdf")
    storage.delete("file.pdf")
    with pytest.raises(FileNotFoundError):
        storage.get("file.pdf")


@pytest.mark.unit
def test_delete_of_missing_key_does_not_raise(storage):
    storage.delete("never-existed.pdf")  # must not raise


@pytest.mark.unit
def test_overwrite_replaces_content(storage):
    storage.put("file.pdf", b"first", "application/pdf")
    storage.put("file.pdf", b"second", "application/pdf")
    assert storage.get("file.pdf") == b"second"


@pytest.mark.unit
@pytest.mark.parametrize("malicious_key", ["../escape.pdf", "a/../../escape.pdf", "../../../etc/passwd"])
def test_rejects_path_traversal_keys(storage, malicious_key):
    with pytest.raises(ValueError):
        storage.put(malicious_key, b"data", "application/pdf")
