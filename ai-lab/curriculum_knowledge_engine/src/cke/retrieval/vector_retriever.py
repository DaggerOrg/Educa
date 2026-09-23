from __future__ import annotations

from cke.domain.models import Citation, KnowledgeChunk
from cke.repositories.interfaces import VectorRepository


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


class VectorRetriever:
    """Thin, service-facing wrapper over a `VectorRepository`: knows how to
    turn raw similarity matches into citable `Citation` objects."""

    def __init__(self, vector_repository: VectorRepository, *, default_top_k: int = 5):
        self._repository = vector_repository
        self._default_top_k = default_top_k

    def retrieve(
        self, query: str, *, top_k: int | None = None, course_id: str | None = None
    ) -> list[tuple[KnowledgeChunk, float]]:
        return self._repository.similarity_search(
            query, top_k=top_k or self._default_top_k, course_id=course_id
        )

    def retrieve_citations(
        self,
        query: str,
        *,
        top_k: int | None = None,
        course_id: str | None = None,
        snippet_length: int = 320,
    ) -> list[Citation]:
        matches = self.retrieve(query, top_k=top_k, course_id=course_id)
        return [
            Citation(
                chunk_id=chunk.id,
                lesson_id=chunk.lesson_id,
                lesson_title=chunk.lesson_title,
                snippet=_truncate(chunk.text, snippet_length),
                relevance_score=score,
            )
            for chunk, score in matches
        ]
