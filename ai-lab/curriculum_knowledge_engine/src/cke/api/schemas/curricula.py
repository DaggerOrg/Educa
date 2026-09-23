"""API-facing DTOs for courses/modules/lessons/concepts.

Deliberately separate from `cke.domain.models` - the wire format (enums as
plain strings, computed summary fields like `lesson_count`) is allowed to
diverge from the domain model's shape without that shape becoming a
backwards-compatibility constraint on the API, and vice versa.
"""

from __future__ import annotations

from pydantic import BaseModel

from cke.domain.models import Concept, Course, Lesson, Module


class ConceptOut(BaseModel):
    id: str
    name: str
    description: str
    difficulty: str
    source: str
    aliases: list[str]

    @classmethod
    def from_domain(cls, concept: Concept) -> ConceptOut:
        return cls(
            id=concept.id,
            name=concept.name,
            description=concept.description,
            difficulty=concept.difficulty.value,
            source=concept.source.value,
            aliases=concept.aliases,
        )


class LessonOut(BaseModel):
    id: str
    title: str
    estimated_minutes: int
    concept_ids: list[str]

    @classmethod
    def from_domain(cls, lesson: Lesson) -> LessonOut:
        return cls(
            id=lesson.id,
            title=lesson.title,
            estimated_minutes=lesson.estimated_minutes,
            concept_ids=lesson.concept_ids,
        )


class ModuleOut(BaseModel):
    id: str
    title: str
    description: str
    lessons: list[LessonOut]

    @classmethod
    def from_domain(cls, module: Module) -> ModuleOut:
        return cls(
            id=module.id,
            title=module.title,
            description=module.description,
            lessons=[LessonOut.from_domain(lesson) for lesson in module.lessons],
        )


class CourseSummaryOut(BaseModel):
    id: str
    title: str
    description: str
    difficulty: str
    module_count: int
    lesson_count: int
    total_minutes: int

    @classmethod
    def from_domain(cls, course: Course) -> CourseSummaryOut:
        return cls(
            id=course.id,
            title=course.title,
            description=course.description,
            difficulty=course.difficulty.value,
            module_count=len(course.modules),
            lesson_count=course.lesson_count,
            total_minutes=course.total_minutes,
        )


class CourseDetailOut(CourseSummaryOut):
    modules: list[ModuleOut]

    @classmethod
    def from_domain(cls, course: Course) -> CourseDetailOut:
        summary = CourseSummaryOut.from_domain(course)
        return cls(
            **summary.model_dump(),
            modules=[ModuleOut.from_domain(module) for module in course.modules],
        )


class IngestCurriculumRequest(BaseModel):
    file_path: str | None = None  # None => ingest the bundled sample curriculum
    enable_llm_extraction: bool = False


class IngestCurriculumResponse(BaseModel):
    course: CourseSummaryOut
    message: str


class ConceptWithScoreOut(BaseModel):
    concept: ConceptOut
    score: float
