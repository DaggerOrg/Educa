import pytest

from cke.domain.enums import RelationType
from cke.domain.exceptions import NotFoundError
from cke.domain.models import Concept, PrerequisiteEdge
from cke.repositories.graph.networkx_repository import NetworkXGraphRepository
from cke.services.gap_analysis_service import GapAnalysisService


@pytest.fixture
def graph():
    repo = NetworkXGraphRepository()
    for name in ["foundations", "vectors", "retrieval", "graphrag"]:
        repo.upsert_concept(Concept.from_name(name))
    repo.upsert_edge(
        PrerequisiteEdge(source_id="vectors", target_id="foundations", relation=RelationType.REQUIRES)
    )
    repo.upsert_edge(
        PrerequisiteEdge(source_id="retrieval", target_id="vectors", relation=RelationType.REQUIRES)
    )
    repo.upsert_edge(
        PrerequisiteEdge(source_id="graphrag", target_id="retrieval", relation=RelationType.REQUIRES)
    )
    return repo


def test_analyze_target_with_no_prior_knowledge(graph):
    service = GapAnalysisService(graph)
    result = service.analyze(known_concept_ids=set(), target_concept_id="graphrag")

    assert result.required_concept_ids == ["foundations", "vectors", "retrieval", "graphrag"]
    assert {c.id for c in result.missing_concepts} == {"foundations", "vectors", "retrieval", "graphrag"}
    assert result.readiness_pct == 0.0


def test_analyze_target_with_partial_knowledge(graph):
    service = GapAnalysisService(graph)
    result = service.analyze(known_concept_ids={"foundations", "vectors"}, target_concept_id="graphrag")

    assert {c.id for c in result.missing_concepts} == {"retrieval", "graphrag"}
    assert result.readiness_pct == 50.0


def test_analyze_target_already_fully_known(graph):
    service = GapAnalysisService(graph)
    result = service.analyze(
        known_concept_ids={"foundations", "vectors", "retrieval", "graphrag"},
        target_concept_id="graphrag",
    )

    assert result.missing_concepts == []
    assert result.readiness_pct == 100.0


def test_analyze_unknown_target_raises_not_found(graph):
    service = GapAnalysisService(graph)
    with pytest.raises(NotFoundError):
        service.analyze(set(), "does-not-exist")


def test_analyze_leaf_concept_with_no_prerequisites(graph):
    service = GapAnalysisService(graph)
    result = service.analyze(set(), "foundations")

    assert result.required_concept_ids == ["foundations"]
    assert {c.id for c in result.missing_concepts} == {"foundations"}
    assert result.readiness_pct == 0.0
