"""Application service independent from FastAPI and Agno agents."""

from .chunking import SectionChunker
from .domain import Chunk
from .parsers import parser_for
from .store import AgnoPgVectorStore


class DocumentService:
    def __init__(self, store: AgnoPgVectorStore, chunker: SectionChunker | None = None):
        self.store = store
        self.chunker = chunker or SectionChunker()

    def ingest(
        self,
        filename: str,
        content: bytes,
        organization_id: str,
        document_id: str,
        course_id: str | None = None,
    ) -> dict:
        parsed = parser_for(filename).parse(filename, content)
        chunks = self.chunker.chunk(parsed, organization_id, document_id, course_id)
        if not chunks:
            raise ValueError("No readable text found in document")
        self.store.add(chunks)
        return {"document_id": document_id, "title": parsed.title, "chunk_count": len(chunks)}

    def search(self, query: str, organization_id: str, course_id: str | None = None, limit: int = 10) -> list[dict]:
        return [
            {
                "content": document.content,
                "document": document.name,
                "section": (document.meta_data or {}).get("section_title"),
                "page": (document.meta_data or {}).get("page_number"),
                "metadata": document.meta_data or {},
            }
            for document in self.store.search(query, organization_id, course_id, limit)
        ]