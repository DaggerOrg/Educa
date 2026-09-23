import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from rag.chunking import SectionChunker
from rag.domain import ParsedDocument, ParsedSection
from rag.embeddings import build_embedder
from rag.parsers import TextDocumentParser


@pytest.mark.unit
def test_text_parser_preserves_headings_as_sections():
    document = TextDocumentParser().parse("notes.md", b"# Motors\nSlip is relative speed.\n## Formula\ns = (Ns-N)/Ns")

    assert [section.title for section in document.sections] == ["Motors", "Formula"]


@pytest.mark.unit
def test_section_chunker_preserves_tenant_and_source_metadata():
    document = ParsedDocument("Machines", [ParsedSection("Motors", "word " * 100, page_start=3)])

    chunks = SectionChunker(target_characters=80, overlap_characters=10).chunk(
        document, organization_id="org-a", course_id="course-a", document_id="doc-a"
    )

    assert len(chunks) > 1
    assert all(chunk.organization_id == "org-a" for chunk in chunks)
    assert all(chunk.course_id == "course-a" for chunk in chunks)
    assert all(chunk.document_id == "doc-a" and chunk.page_number == 3 for chunk in chunks)


@pytest.mark.unit
def test_build_embedder_openai_provider_has_expected_shape():
    # Constructing OpenAIEmbedder does no network I/O - it only builds an
    # (unauthenticated) client, so this stays a fast unit test.
    embedder = build_embedder("openai")

    assert embedder.dimensions == 1536
    assert embedder.id == "text-embedding-3-small"


@pytest.mark.unit
def test_build_embedder_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unknown RAG_EMBEDDER_PROVIDER"):
        build_embedder("not-a-real-provider")