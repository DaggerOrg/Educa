"""GraphRAG: combine unstructured context (vector similarity) with
structured context (graph relationships) into one retrieval result, so the
QA service can hand Claude both "what does the text say" and "how do these
concepts relate" for a single question.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cke.domain.models import Citation
from cke.retrieval.graph_retriever import GraphRetriever
from cke.retrieval.vector_retriever import VectorRetriever


@dataclass
class HybridContext:
    citations: list[Citation] = field(default_factory=list)
    concept_ids: list[str] = field(default_factory=list)
    graph_context: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.citations and not self.graph_context

    def to_prompt_block(self) -> str:
        parts = []
        if self.citations:
            cited_text = "\n\n".join(
                f"[{i + 1}] ({citation.lesson_title}) {citation.snippet}"
                for i, citation in enumerate(self.citations)
            )
            parts.append(f"Retrieved lesson excerpts:\n{cited_text}")
        if self.graph_context:
            parts.append(f"Concept relationships from the knowledge graph:\n{self.graph_context}")
        return "\n\n".join(parts)


class HybridRetriever:
    def __init__(self, vector_retriever: VectorRetriever, graph_retriever: GraphRetriever):
        self._vector = vector_retriever
        self._graph = graph_retriever

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        course_id: str | None = None,
        graph_hops: int = 1,
    ) -> HybridContext:
        matches = self._vector.retrieve(query, top_k=top_k, course_id=course_id)

        citations = [
            Citation(
                chunk_id=chunk.id,
                lesson_id=chunk.lesson_id,
                lesson_title=chunk.lesson_title,
                snippet=chunk.text,
                relevance_score=score,
            )
            for chunk, score in matches
        ]

        concept_ids = {concept_id for chunk, _ in matches for concept_id in chunk.concept_ids}
        concept_ids |= {concept.id for concept in self._graph.match_concepts_in_text(query)}

        context_blocks = [
            block
            for concept_id in sorted(concept_ids)
            if (block := self._graph.concept_context(concept_id, hops=graph_hops))
        ]

        return HybridContext(
            citations=citations,
            concept_ids=sorted(concept_ids),
            graph_context="\n".join(context_blocks),
        )
