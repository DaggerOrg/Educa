from cke.domain.enums import RelationType
from cke.domain.models import Concept, KnowledgeChunk, PrerequisiteEdge
from cke.repositories.graph.networkx_repository import NetworkXGraphRepository
from cke.retrieval.graph_retriever import GraphRetriever
from cke.retrieval.hybrid_retriever import HybridRetriever
from cke.retrieval.vector_retriever import VectorRetriever
from cke.services.qa_service import QAService, _NO_CONTEXT_ANSWER


def _chunk(text: str, concept_ids: list[str]) -> KnowledgeChunk:
    return KnowledgeChunk(
        text=text,
        lesson_id="lesson-1",
        lesson_title="Lesson One",
        module_id="module-1",
        course_id="course-1",
        chunk_index=0,
        concept_ids=concept_ids,
    )


def test_answer_with_no_retrieved_context_returns_canned_response(stub_vector_repository, fake_claude_client):
    graph_repo = NetworkXGraphRepository()
    hybrid = HybridRetriever(VectorRetriever(stub_vector_repository), GraphRetriever(graph_repo))
    service = QAService(hybrid, fake_claude_client)

    result = service.answer("What is a transformer?")

    assert result.answer == _NO_CONTEXT_ANSWER
    assert result.citations == []
    assert fake_claude_client.complete_calls == []  # never call the LLM with no context


def test_answer_grounds_response_in_retrieved_chunks_and_graph_context(stub_vector_repository, fake_claude_client):
    graph_repo = NetworkXGraphRepository()
    graph_repo.upsert_concept(Concept.from_name("Vectors"))
    graph_repo.upsert_concept(Concept.from_name("Foundations"))
    graph_repo.upsert_edge(
        PrerequisiteEdge(source_id="vectors", target_id="foundations", relation=RelationType.REQUIRES)
    )
    stub_vector_repository.set_results(
        [(_chunk("Vectors represent meaning as numbers.", ["vectors"]), 0.9)]
    )

    hybrid = HybridRetriever(VectorRetriever(stub_vector_repository), GraphRetriever(graph_repo))
    fake_claude_client.complete_response = "Vectors build on Foundations. [1]"
    service = QAService(hybrid, fake_claude_client)

    result = service.answer("What are vectors?")

    assert result.answer == "Vectors build on Foundations. [1]"
    assert len(result.citations) == 1
    assert result.citations[0].lesson_title == "Lesson One"
    assert "vectors" in result.concepts_referenced

    [call] = fake_claude_client.complete_calls
    assert "Vectors represent meaning as numbers." in call["prompt"]
    assert "requires--> Foundations" in call["prompt"]
    assert call["system"] is not None
