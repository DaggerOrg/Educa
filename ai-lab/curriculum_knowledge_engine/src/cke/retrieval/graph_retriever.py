from __future__ import annotations

from cke.domain.models import Concept
from cke.repositories.interfaces import GraphRepository


class GraphRetriever:
    """Turns raw graph edges into prompt-ready text, and finds which
    concepts a piece of free text is talking about."""

    def __init__(self, graph_repository: GraphRepository):
        self._repository = graph_repository

    def concept_context(self, concept_id: str, *, hops: int = 1) -> str:
        edges = self._repository.neighbors_context(concept_id, hops=hops)
        lines: list[str] = []
        for edge in edges:
            source = self._repository.get_concept(edge.source_id)
            target = self._repository.get_concept(edge.target_id)
            if source is None or target is None:
                continue
            lines.append(f"{source.name} --{edge.relation.value}--> {target.name}")
        return "\n".join(lines)

    def match_concepts_in_text(self, text: str) -> list[Concept]:
        """Naive substring matching of concept names/aliases against `text`.

        Good enough to seed graph context from a free-text question without
        another LLM round trip; a production system might instead have
        Claude name the concepts explicitly as part of the answer prompt.
        """
        text_lower = text.lower()
        matches: list[Concept] = []
        for concept in self._repository.all_concepts():
            candidate_names = [concept.name, *concept.aliases]
            if any(name.lower() in text_lower for name in candidate_names if name):
                matches.append(concept)
        return matches
