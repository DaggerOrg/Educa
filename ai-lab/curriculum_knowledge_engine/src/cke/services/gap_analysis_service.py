from __future__ import annotations

from cke.domain.exceptions import NotFoundError
from cke.domain.models import GapAnalysisResult
from cke.repositories.interfaces import GraphRepository


class GapAnalysisService:
    """Compares what a learner knows against everything a target concept
    transitively requires - reuses the same graph traversal the learning
    path service uses, just called once with an empty known-set to get the
    *full* requirement set, and once with the learner's real known-set."""

    def __init__(self, graph_repository: GraphRepository):
        self._graph = graph_repository

    def analyze(self, known_concept_ids: set[str], target_concept_id: str) -> GapAnalysisResult:
        target = self._graph.get_concept(target_concept_id)
        if target is None:
            raise NotFoundError("Concept", target_concept_id)

        required_ids = self._graph.shortest_prerequisite_chain(set(), target_concept_id)
        missing_ids = self._graph.shortest_prerequisite_chain(known_concept_ids, target_concept_id)

        missing_concepts = [
            concept for cid in missing_ids if (concept := self._graph.get_concept(cid)) is not None
        ]

        total_required = len(required_ids) or 1
        known_count = total_required - len(missing_ids)
        readiness_pct = round(100.0 * known_count / total_required, 1)

        return GapAnalysisResult(
            target_id=target_concept_id,
            known_concept_ids=sorted(known_concept_ids),
            required_concept_ids=required_ids,
            missing_concepts=missing_concepts,
            readiness_pct=readiness_pct,
        )
