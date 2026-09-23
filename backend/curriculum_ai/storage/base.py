"""Object storage boundary -- swappable backends, same shape as
rag/embeddings.py's `build_embedder()`. Nothing else in this package
should import `boto3` or touch a filesystem path directly; go through
`get_storage()` in storage/__init__.py.
"""

from typing import Protocol


class ObjectStorage(Protocol):
    def put(self, key: str, content: bytes, content_type: str) -> None:
        """Store `content` under `key`, creating or overwriting it."""

    def get(self, key: str) -> bytes:
        """Return the bytes stored under `key`. Raises if it doesn't exist."""

    def delete(self, key: str) -> None:
        """Remove `key`. Must not raise if it's already gone."""
