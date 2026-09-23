import pytest

from cke.domain.enums import RelationType
from cke.domain.exceptions import LLMGenerationError, NotFoundError
from cke.domain.models import Concept, PrerequisiteEdge
from cke.repositories.graph.networkx_repository import NetworkXGraphRepository
from cke.retrieval.vector_retriever import VectorRetriever
from cke.services.learning_path_service import LearningPathService, _PlanNarrative, _StepNarrative


@pytest.fixture
def graph():
    repo = NetworkXGraphRepository()
    for name in ["foundations", "vectors", "retrieval"]:
        repo.upsert_concept(Concept.from_name(name))
    repo.upsert_edge(
        PrerequisiteEdge(source_id="vectors", target_id="foundations", relation=RelationType.REQUIRES)
    )
    repo.upsert_edge(
        PrerequisiteEdge(source_id="retrieval", target_id="vectors", relation=RelationType.REQUIRES)
    )
    return repo


@pytest.fixture
def vector_retriever(stub_vector_repository):
    return VectorRetriever(stub_vector_repository)


def test_build_plan_uses_graph_order_and_claude_narrative(graph, vector_retriever, fake_claude_client):
    fake_claude_client.extract_response = _PlanNarrative(
        steps=[
            _StepNarrative(concept_name="foundations", rationale="Start here.", estimated_minutes=20),
            _StepNarrative(concept_name="vectors", rationale="Needs foundations.", estimated_minutes=30),
            _StepNarrative(concept_name="retrieval", rationale="Needs vectors.", estimated_minutes=25),
        ],
        summary="A three-step path.",
    )
    service = LearningPathService(graph, vector_retriever, fake_claude_client)

    plan = service.build_plan(known_concept_ids=set(), goal_concept_id="retrieval")

    assert [step.concept.id for step in plan.steps] == ["foundations", "vectors", "retrieval"]
    assert plan.steps[0].rationale == "Start here."
    assert plan.steps[1].estimated_minutes == 30
    assert plan.summary == "A three-step path."
    assert plan.total_estimated_minutes == 20 + 30 + 25


def test_build_plan_goal_already_known_skips_claude(graph, vector_retriever, fake_claude_client):
    service = LearningPathService(graph, vector_retriever, fake_claude_client)

    plan = service.build_plan(known_concept_ids={"retrieval"}, goal_concept_id="retrieval")

    assert plan.steps == []
    assert plan.total_estimated_minutes == 0
    assert fake_claude_client.extract_calls == []


def test_build_plan_unknown_goal_raises_not_found(graph, vector_retriever, fake_claude_client):
    service = LearningPathService(graph, vector_retriever, fake_claude_client)
    with pytest.raises(NotFoundError):
        service.build_plan(set(), "does-not-exist")


def test_build_plan_falls_back_when_narrative_omits_a_concept(graph, vector_retriever, fake_claude_client):
    fake_claude_client.extract_response = _PlanNarrative(
        steps=[
            _StepNarrative(concept_name="foundations", rationale="Start here.", estimated_minutes=20),
            # "vectors" is missing entirely.
            _StepNarrative(concept_name="retrieval", rationale="Needs vectors.", estimated_minutes=25),
        ],
        summary="Partial narrative.",
    )
    service = LearningPathService(graph, vector_retriever, fake_claude_client)

    plan = service.build_plan(set(), "retrieval")

    vectors_step = next(s for s in plan.steps if s.concept.id == "vectors")
    assert "retrieval" in vectors_step.rationale  # goal-name fallback rationale
    assert vectors_step.estimated_minutes == 30  # _FALLBACK_MINUTES


def test_build_plan_falls_back_entirely_when_claude_call_fails(graph, vector_retriever, fake_claude_client):
    fake_claude_client.extract_exception = LLMGenerationError("boom")
    service = LearningPathService(graph, vector_retriever, fake_claude_client)

    plan = service.build_plan(set(), "retrieval")

    assert [step.concept.id for step in plan.steps] == ["foundations", "vectors", "retrieval"]
    assert all(step.estimated_minutes == 30 for step in plan.steps)
    assert "retrieval" in plan.summary
