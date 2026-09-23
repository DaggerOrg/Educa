"""Agno PgVector infrastructure adapter."""

import hashlib
import os

from agno.knowledge.document.base import Document
from agno.vectordb.pgvector import PgVector, SearchType

from .domain import Chunk
from .embeddings import Embedder, build_embedder


class AgnoPgVectorStore:
    def __init__(
        self,
        table_name: str = "rag_chunks",
        db_url: str | None = None,
        embedder: Embedder | None = None,
    ):
        self.vector_db = PgVector(
            table_name=table_name,
            db_url=db_url or os.environ["DATABASE_URL"],
            search_type=SearchType.hybrid,
            embedder=embedder or build_embedder(),
        )
        self.vector_db.create()

    def add(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        content_hash = hashlib.sha256("\n".join(c.content for c in chunks).encode()).hexdigest()
        documents = [
            Document(
                content=chunk.content,
                name=chunk.metadata.get("document_title", chunk.document_id),
                meta_data={
                    **chunk.metadata,
                    "organization_id": chunk.organization_id,
                    "course_id": chunk.course_id,
                    "document_id": chunk.document_id,
                    "section_title": chunk.section_title,
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                },
            )
            for chunk in chunks
        ]
        self.vector_db.upsert(content_hash=content_hash, documents=documents)

    def search(self, query: str, organization_id: str, course_id: str | None = None, limit: int = 10) -> list[Document]:
        filters = {"organization_id": organization_id}
        if course_id:
            filters["course_id"] = course_id
        return self.vector_db.search(query=query, limit=limit, filters=filters)