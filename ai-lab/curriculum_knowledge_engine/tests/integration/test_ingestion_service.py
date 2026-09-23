"""Full pipeline test against real local backends (Chroma + NetworkX +
JSON course store) - no mocking below the ingestion service. The only
thing NOT exercised here is the Claude API itself (`enable_llm_extraction`
stays off), since this environment has no API key.
"""

from __future__ import annotations

import pytest

from cke.domain.enums import RelationType
from cke.ingestion.ingestion_service import CurriculumIngestionService
from cke.repositories.course.json_course_repository import JsonCourseRepository
from cke.repositories.graph.networkx_repository import NetworkXGraphRepository
from cke.repositories.vector.chroma_repository import ChromaVectorRepository


@pytest.fixture
def ingested(tmp_path, small_spec):
    vector_repo = ChromaVectorRepository(
        persist_dir=tmp_path / "chroma",
        collection_name="test_chunks",
        embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
    )
    graph_repo = NetworkXGraphRepository()
    course_repo = JsonCourseRepository(persist_dir=tmp_path / "courses")

    service = CurriculumIngestionService(vector_repo, graph_repo, course_repo)
    course = service.ingest(small_spec, enable_llm_extraction=False)

    return {
        "course": course,
        "vector_repo": vector_repo,
        "graph_repo": graph_repo,
        "course_repo": course_repo,
    }


def test_ingest_builds_course_tree(ingested):
    course = ingested["course"]
    assert course.id == "test-course"
    assert len(course.modules) == 1
    assert course.lesson_count == 3
    lesson_ids = {lesson.id for lesson in course.iter_lessons()}
    assert lesson_ids == {"l1", "l2", "l3"}


def test_ingest_populates_authored_graph(ingested):
    graph_repo = ingested["graph_repo"]
    concepts = {c.id for c in graph_repo.all_concepts()}
    assert concepts == {"foundations", "vectors", "retrieval"}

    edges = graph_repo.all_edges()
    assert len(edges) == 2
    assert all(edge.relation == RelationType.REQUIRES for edge in edges)

    chain = graph_repo.shortest_prerequisite_chain(set(), "retrieval")
    assert chain == ["foundations", "vectors", "retrieval"]


def test_ingest_saves_course_for_later_retrieval(ingested):
    course_repo = ingested["course_repo"]
    reloaded = course_repo.get("test-course")
    assert reloaded is not None
    assert reloaded.title == "Test Course"
    assert [c.id for c in course_repo.list()] == ["test-course"]


def test_ingest_embeds_chunks_and_similarity_search_finds_relevant_one(ingested):
    vector_repo = ingested["vector_repo"]
    # Each lesson's repeated-sentence fixture content runs past the 120-word
    # chunk window once, so the chunker splits each of the 3 lessons in two.
    assert vector_repo.count() == 6

    matches = vector_repo.similarity_search("How do vectors represent meaning?", top_k=1)
    assert len(matches) == 1
    chunk, score = matches[0]
    assert chunk.lesson_id == "l2"
    assert score > 0.0


def test_ingest_similarity_search_respects_course_filter(ingested):
    vector_repo = ingested["vector_repo"]
    matches = vector_repo.similarity_search("vectors", top_k=5, course_id="a-different-course")
    assert matches == []


def test_reingesting_same_course_replaces_chunks(ingested, small_spec):
    vector_repo = ingested["vector_repo"]
    graph_repo = ingested["graph_repo"]
    course_repo = ingested["course_repo"]
    service = CurriculumIngestionService(vector_repo, graph_repo, course_repo)

    count_before = vector_repo.count()
    service.ingest(small_spec, enable_llm_extraction=False)

    assert vector_repo.count() == count_before  # replaced, not duplicated
