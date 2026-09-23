"""Pure validation logic -- no DB/storage/queue touched at runtime, but the
import chain (service.py -> models.py -> app.db.session) needs a
syntactically valid DATABASE_URL to construct the SQLAlchemy Engine at
import time, same as tests/integration/test_health.py already sets.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://educa:educa@localhost:55432/educa")
sys.path.insert(0, str(Path(__file__).parents[3]))

from curriculum_ai.service import MAX_UPLOAD_BYTES, _validate_upload  # noqa: E402

VALID_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\nrest of a pdf..."


@pytest.mark.unit
def test_accepts_a_well_formed_pdf():
    _validate_upload("notes.pdf", VALID_PDF, "application/pdf")  # must not raise


@pytest.mark.unit
def test_rejects_empty_file():
    with pytest.raises(ValueError, match="empty"):
        _validate_upload("notes.pdf", b"", "application/pdf")


@pytest.mark.unit
def test_rejects_oversized_file():
    oversized = VALID_PDF + b"0" * MAX_UPLOAD_BYTES
    with pytest.raises(ValueError, match="too large"):
        _validate_upload("notes.pdf", oversized, "application/pdf")


@pytest.mark.unit
def test_rejects_non_pdf_extension():
    with pytest.raises(ValueError, match="PDF"):
        _validate_upload("notes.txt", VALID_PDF, "application/pdf")


@pytest.mark.unit
def test_rejects_non_pdf_content_type():
    with pytest.raises(ValueError, match="PDF"):
        _validate_upload("notes.pdf", VALID_PDF, "text/plain")


@pytest.mark.unit
def test_rejects_pdf_extension_with_non_pdf_bytes():
    """A renamed non-PDF file (extension and content-type both lie) must
    still be caught by the magic-byte check - uploaded content is
    untrusted, so neither client-supplied field is taken on faith."""
    with pytest.raises(ValueError, match="signature"):
        _validate_upload("fake.pdf", b"This is just plain text, not a PDF.", "application/pdf")
