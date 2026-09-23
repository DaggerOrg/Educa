"""Repository interfaces (ports, in hexagonal-architecture terms).

Every service in `cke.services` depends on these abstractions, never on a
concrete backend. `VectorRepository` has a local (`ChromaVectorRepository`)
and a production (`PgVectorRepository`) implementation; `GraphRepository`
has a local (`NetworkXGraphRepository`) and a production
(`Neo4jGraphRepository`) implementation. Swapping backends is a one-line
change in `cke.config.Settings` plus a factory update in
`cke.repositories.factory` - no service code changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from cke.domain.models import Concept, Course, KnowledgeChunk, PrerequisiteEdge


class CourseRepository(ABC):
    """Stores the structured Course/Module/Lesson tree itself.

    Separate from `VectorRepository` (which only stores embedded text
    chunks) and `GraphRepository` (which only stores concepts/edges) - this
    is what backs "list courses" / "get course detail" read paths.
    """

    @abstractmethod
    def save(self, course: Course) -> None:
        """Insert or fully replace a course (keyed by `course.id`)."""

    @abstractmethod
    def get(self, course_id: str) -> Course | None: ...

    @abstractmethod
    def list(self) -> list[Course]: ...

    @abstractmethod
    def delete(self, course_id: str) -> None: ...


class VectorRepository(ABC):
    """Stores embedded text chunks and finds the most similar ones to a query."""

    @abstractmethod
    def upsert_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        """Embed and store/replace the given chunks (idempotent by chunk id)."""

    @abstractmethod
    def similarity_search(
        self, query: str, *, top_k: int = 5, course_id: str | None = None
    ) -> list[tuple[KnowledgeChunk, float]]:
        """Return the `top_k` most similar chunks and a relevance score in
        [0, 1] (higher is more relevant), optionally restricted to one course."""

    @abstractmethod
    def delete_by_course(self, course_id: str) -> None:
        """Remove every chunk belonging to a course (used on re-ingestion)."""

    @abstractmethod
    def count(self) -> int:
        """Total number of chunks currently stored."""


class GraphRepository(ABC):
    """Stores concepts (nodes) and typed prerequisite relationships (edges)."""

    @abstractmethod
    def upsert_concept(self, concept: Concept) -> None: ...

    @abstractmethod
    def get_concept(self, concept_id: str) -> Concept | None: ...

    @abstractmethod
    def all_concepts(self) -> list[Concept]: ...

    @abstractmethod
    def upsert_edge(self, edge: PrerequisiteEdge) -> None:
        """Add or update a directed edge.

        Raises `CyclicPrerequisiteError` if the edge is a REQUIRES edge and
        adding it would create a prerequisite cycle.
        """

    @abstractmethod
    def all_edges(self) -> list[PrerequisiteEdge]: ...

    @abstractmethod
    def get_prerequisites(self, concept_id: str) -> list[Concept]:
        """Concepts that `concept_id` directly requires."""

    @abstractmethod
    def get_dependents(self, concept_id: str) -> list[Concept]:
        """Concepts that directly require `concept_id`."""

    @abstractmethod
    def shortest_prerequisite_chain(
        self, known_concept_ids: set[str], goal_concept_id: str
    ) -> list[str]:
        """The minimal, dependency-ordered list of concept ids a learner who
        already knows `known_concept_ids` must still learn to reach
        `goal_concept_id`, ending with `goal_concept_id` itself.

        Raises `NotFoundError` if `goal_concept_id` isn't in the graph, and
        `UnreachableGoalError` if a transitive prerequisite is missing from
        the graph entirely (a dangling reference).
        """

    @abstractmethod
    def most_central_concepts(self, top_n: int = 10) -> list[tuple[Concept, float]]:
        """Concepts ranked by how many other concepts depend on them,
        directly or transitively - useful for spotting foundational topics."""

    @abstractmethod
    def neighbors_context(self, concept_id: str, *, hops: int = 1) -> list[PrerequisiteEdge]:
        """Every edge touching `concept_id` within `hops` steps, for
        building GraphRAG prompt context."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all concepts and edges. Primarily for tests and re-ingestion."""
