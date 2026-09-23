from __future__ import annotations

import pytest

from cke.config import get_settings
from cke.domain.models import KnowledgeChunk
from cke.ingestion.curriculum_schema import ConceptSpec, CurriculumSpec, LessonSpec, ModuleSpec
from cke.repositories.interfaces import VectorRepository


@pytest.fixture
def cke_env(tmp_path, monkeypatch):
    """Points every local persistence path at a throwaway tmp_path, and
    clears the cached Settings singleton so the new env vars take effect."""
    monkeypatch.setenv("CKE_CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    monkeypatch.setenv("CKE_GRAPH_PERSIST_PATH", str(tmp_path / "graph.json"))
    monkeypatch.setenv("CKE_COURSE_PERSIST_DIR", str(tmp_path / "courses"))
    monkeypatch.setenv("CKE_LOG_LEVEL", "WARNING")
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture
def small_spec() -> CurriculumSpec:
    """A tiny, three-concept linear-chain curriculum: Foundations ->
    Vectors -> Retrieval. Small enough for fast, readable assertions."""
    return CurriculumSpec(
        id="test-course",
        title="Test Course",
        description="A tiny course for tests.",
        concepts=[
            ConceptSpec(name="Foundations", description="The base layer."),
            ConceptSpec(name="Vectors", description="Embeddings.", requires=["Foundations"]),
            ConceptSpec(name="Retrieval", description="Finding things.", requires=["Vectors"]),
        ],
        modules=[
            ModuleSpec(
                id="m1",
                title="Module One",
                lessons=[
                    LessonSpec(
                        id="l1",
                        title="Intro to Foundations",
                        content="Foundations are the conceptual base everything else builds on. " * 15,
                        teaches=["Foundations"],
                    ),
                    LessonSpec(
                        id="l2",
                        title="Vectors 101",
                        content="A vector represents meaning as a list of numbers in space. " * 15,
                        teaches=["Vectors"],
                    ),
                    LessonSpec(
                        id="l3",
                        title="Retrieval Basics",
                        content="Retrieval finds the most relevant stored content for a query. " * 15,
                        teaches=["Retrieval"],
                    ),
                ],
            )
        ],
    )


class FakeClaudeClient:
    """Test double for `ClaudeClient` - no network calls, canned/derived
    responses. Services depend on it only through duck typing (`.complete`
    / `.extract`), so this needs no shared base class."""

    def __init__(
        self,
        *,
        complete_response: str = "A grounded answer. [1]",
        extract_response=None,
        extract_exception: Exception | None = None,
    ):
        self.complete_response = complete_response
        self.extract_response = extract_response
        self.extract_exception = extract_exception
        self.complete_calls: list[dict] = []
        self.extract_calls: list[dict] = []

    def complete(self, prompt, *, system=None, max_tokens=None, effort=None):
        self.complete_calls.append({"prompt": prompt, "system": system})
        return self.complete_response

    def extract(self, prompt, *, output_model, system=None, max_tokens=None, effort=None):
        self.extract_calls.append({"prompt": prompt, "system": system, "output_model": output_model})
        if self.extract_exception is not None:
            raise self.extract_exception
        if self.extract_response is not None:
            return self.extract_response
        raise NotImplementedError("FakeClaudeClient.extract_response was not configured")


@pytest.fixture
def fake_claude_client() -> FakeClaudeClient:
    return FakeClaudeClient()


class StubVectorRepository(VectorRepository):
    """No embeddings, no I/O - `similarity_search` just returns whatever
    was configured via `set_results`, in order. Used by service-level unit
    tests that need *a* `VectorRepository` but aren't testing retrieval
    quality itself."""

    def __init__(self):
        self._results: list[tuple[KnowledgeChunk, float]] = []
        self.upserted: list[KnowledgeChunk] = []

    def set_results(self, results: list[tuple[KnowledgeChunk, float]]) -> None:
        self._results = results

    def upsert_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        self.upserted.extend(chunks)

    def similarity_search(self, query, *, top_k=5, course_id=None):
        return self._results[:top_k]

    def delete_by_course(self, course_id: str) -> None:
        self.upserted = [c for c in self.upserted if c.course_id != course_id]

    def count(self) -> int:
        return len(self.upserted)


@pytest.fixture
def stub_vector_repository() -> StubVectorRepository:
    return StubVectorRepository()
