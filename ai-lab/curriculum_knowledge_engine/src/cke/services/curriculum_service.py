from __future__ import annotations

from cke.domain.exceptions import NotFoundError
from cke.domain.models import Concept, Course
from cke.repositories.interfaces import CourseRepository, GraphRepository


class CurriculumService:
    """Read-side queries over ingested courses and the concept graph -
    the boring but necessary CRUD-ish layer behind the `/courses` and
    `/concepts` API routes."""

    def __init__(self, course_repository: CourseRepository, graph_repository: GraphRepository):
        self._courses = course_repository
        self._graph = graph_repository

    def list_courses(self) -> list[Course]:
        return self._courses.list()

    def get_course(self, course_id: str) -> Course:
        course = self._courses.get(course_id)
        if course is None:
            raise NotFoundError("Course", course_id)
        return course

    def list_concepts(self) -> list[Concept]:
        return sorted(self._graph.all_concepts(), key=lambda c: c.name)

    def get_concept(self, concept_id: str) -> Concept:
        concept = self._graph.get_concept(concept_id)
        if concept is None:
            raise NotFoundError("Concept", concept_id)
        return concept

    def get_prerequisites(self, concept_id: str) -> list[Concept]:
        self.get_concept(concept_id)  # 404s if the concept itself doesn't exist
        return self._graph.get_prerequisites(concept_id)

    def get_dependents(self, concept_id: str) -> list[Concept]:
        self.get_concept(concept_id)
        return self._graph.get_dependents(concept_id)

    def most_foundational_concepts(self, top_n: int = 10) -> list[tuple[Concept, float]]:
        return self._graph.most_central_concepts(top_n=top_n)
