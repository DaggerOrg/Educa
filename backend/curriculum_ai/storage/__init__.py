"""Storage backend selection -- CURRICULUM_STORAGE_BACKEND, "s3" (default)
or "local". Same swappable-provider shape as rag/embeddings.py's
build_embedder(): one factory function, callers never import a concrete
backend class directly.
"""

import os

from .base import ObjectStorage

_storage: ObjectStorage | None = None


def build_storage(backend: str | None = None) -> ObjectStorage:
    backend = (backend or os.environ.get("CURRICULUM_STORAGE_BACKEND", "s3")).lower()
    if backend == "s3":
        from .s3 import S3ObjectStorage

        return S3ObjectStorage()
    if backend == "local":
        from .local import LocalDiskStorage

        return LocalDiskStorage()
    raise ValueError(f"Unknown CURRICULUM_STORAGE_BACKEND: {backend!r} (use 's3' or 'local')")


def get_storage() -> ObjectStorage:
    """Process-wide storage instance, built once (a fresh S3ObjectStorage
    would otherwise re-check bucket existence on every call)."""
    global _storage
    if _storage is None:
        _storage = build_storage()
    return _storage


def reset_storage_cache() -> None:
    """Test-only: force the next get_storage() call to rebuild, after
    changing CURRICULUM_STORAGE_BACKEND or monkeypatching the env."""
    global _storage
    _storage = None
