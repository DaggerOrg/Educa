"""Local vector backend: Chroma, with embeddings computed explicitly via
`sentence-transformers` rather than Chroma's built-in default embedder, so
the embedding model is always the one named in `Settings.embedding_model_name`
- the same guarantee `PgVectorRepository` gives for the production backend.
"""

from __future__ import annotations

from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from cke.domain.models import KnowledgeChunk
from cke.logging_config import get_logger
from cke.repositories.interfaces import VectorRepository

logger = get_logger(__name__)


class ChromaVectorRepository(VectorRepository):
    def __init__(self, persist_dir: Path, collection_name: str, embedding_model_name: str):
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            collection_name, metadata={"hnsw:space": "cosine"}
        )
        self._embedder = SentenceTransformer(embedding_model_name)
        logger.info(
            "ChromaVectorRepository ready: collection=%s persist_dir=%s embedding_model=%s",
            collection_name,
            persist_dir,
            embedding_model_name,
        )

    def _embed(self, texts: list[str]) -> list[list[float]]:
        return self._embedder.encode(list(texts), normalize_embeddings=True).tolist()

    def upsert_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        if not chunks:
            return
        embeddings = self._embed([chunk.text for chunk in chunks])
        self._collection.upsert(
            ids=[chunk.id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=embeddings,
            metadatas=[chunk.to_metadata() for chunk in chunks],
        )
        logger.info("Upserted %d chunks into Chroma", len(chunks))

    def similarity_search(
        self, query: str, *, top_k: int = 5, course_id: str | None = None
    ) -> list[tuple[KnowledgeChunk, float]]:
        query_embedding = self._embed([query])[0]
        where = {"course_id": course_id} if course_id else None

        result = self._collection.query(
            query_embeddings=[query_embedding], n_results=top_k, where=where
        )

        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]

        matches: list[tuple[KnowledgeChunk, float]] = []
        for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            raw_concept_ids = metadata.get("concept_ids", "") or ""
            chunk = KnowledgeChunk(
                id=chunk_id,
                text=document,
                lesson_id=metadata["lesson_id"],
                lesson_title=metadata["lesson_title"],
                module_id=metadata["module_id"],
                course_id=metadata["course_id"],
                chunk_index=metadata["chunk_index"],
                concept_ids=[c for c in raw_concept_ids.split(",") if c],
            )
            # Cosine distance -> a rough [0, 1] relevance score for display/ranking.
            score = max(0.0, min(1.0, 1.0 - distance))
            matches.append((chunk, score))
        return matches

    def delete_by_course(self, course_id: str) -> None:
        self._collection.delete(where={"course_id": course_id})

    def count(self) -> int:
        return self._collection.count()
