"""Local-disk storage -- a test double for the `ObjectStorage` protocol,
used by unit tests so they don't need MinIO running. Not the default for
the live upload endpoint (see storage/__init__.py); available via
CURRICULUM_STORAGE_BACKEND=local for anyone who wants a zero-service dev
loop anyway.
"""

from __future__ import annotations

from pathlib import Path


class LocalDiskStorage:
    def __init__(self, root: Path | str = "tmp/curriculum_documents"):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Reject any key that would escape `root` (e.g. via "../..") --
        # storage keys are built from server-generated ids, never raw user
        # input, but this is a cheap, worthwhile guard regardless.
        candidate = (self.root / key).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError(f"Invalid storage key: {key!r}")
        return candidate

    def put(self, key: str, content: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()
