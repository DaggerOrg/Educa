"""Core domain model - plain Pydantic models with no framework or storage
concerns. Repositories translate to/from these; API schemas translate
these to/from wire format. Neither direction ever happens in this file.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from cke.domain.enums import BloomLevel, ConceptSource, DifficultyLevel, RelationType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def slugify(text: str) -> str:
    """Deterministic id derivation so the same concept name always maps to
    the same node, whether it was authored or extracted by the LLM twice."""
    keep = (c.lower() if c.isalnum() else "-" for c in text.strip())
    slug = "".join(keep)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


class LearningObjective(BaseModel):
    text: str
    bloom_level: BloomLevel = BloomLevel.UNDERSTAND


class Concept(BaseModel):
    """A single addressable unit of knowledge - the node type of the graph."""

    id: str
    name: str
    description: str = ""
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    source: ConceptSource = ConceptSource.AUTHORED
    aliases: list[str] = Field(default_factory=list)

    @classmethod
    def from_name(
        cls,
        name: str,
        *,
        description: str = "",
        difficulty: DifficultyLevel = DifficultyLevel.BEGINNER,
        source: ConceptSource = ConceptSource.AUTHORED,
        aliases: list[str] | None = None,
    ) -> Concept:
        return cls(
            id=slugify(name),
            name=name,
            description=description,
            difficulty=difficulty,
            source=source,
            aliases=aliases or [],
        )


class PrerequisiteEdge(BaseModel):
    """A directed, typed relationship between two concepts.

    Direction convention: `source_id --relation--> target_id`, e.g. for
    RelationType.REQUIRES, `source_id` is the concept that requires
    `target_id` as a prerequisite (source depends on target).
    """

    source_id: str
    target_id: str
    relation: RelationType = RelationType.REQUIRES
    source_type: ConceptSource = ConceptSource.AUTHORED
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    rationale: str = ""

    @field_validator("confidence")
    @classmethod
    def _authored_edges_are_certain(cls, v: float, info) -> float:
        # Authored edges come from a human-written curriculum spec; treat
        # them as ground truth regardless of what the caller passed in.
        if info.data.get("source_type") == ConceptSource.AUTHORED:
            return 1.0
        return v


class Lesson(BaseModel):
    id: str
    module_id: str
    title: str
    content: str
    objectives: list[LearningObjective] = Field(default_factory=list)
    concept_ids: list[str] = Field(default_factory=list)
    estimated_minutes: int = Field(default=15, gt=0)
    order: int = 0


class Module(BaseModel):
    id: str
    course_id: str
    title: str
    description: str = ""
    lessons: list[Lesson] = Field(default_factory=list)
    order: int = 0

    @property
    def total_minutes(self) -> int:
        return sum(lesson.estimated_minutes for lesson in self.lessons)


class Course(BaseModel):
    id: str
    title: str
    description: str = ""
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    modules: list[Module] = Field(default_factory=list)

    @property
    def total_minutes(self) -> int:
        return sum(module.total_minutes for module in self.modules)

    @property
    def lesson_count(self) -> int:
        return sum(len(module.lessons) for module in self.modules)

    def iter_lessons(self):
        for module in self.modules:
            yield from module.lessons


class KnowledgeChunk(BaseModel):
    """One retrievable unit in the vector store - a slice of a lesson's
    content, small enough to embed meaningfully and cite precisely."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    text: str
    lesson_id: str
    lesson_title: str
    module_id: str
    course_id: str
    chunk_index: int
    concept_ids: list[str] = Field(default_factory=list)

    def to_metadata(self) -> dict:
        """Flat dict for vector-store metadata columns (no nested values)."""
        return {
            "lesson_id": self.lesson_id,
            "lesson_title": self.lesson_title,
            "module_id": self.module_id,
            "course_id": self.course_id,
            "chunk_index": self.chunk_index,
            "concept_ids": ",".join(self.concept_ids),
        }


class Citation(BaseModel):
    chunk_id: str
    lesson_id: str
    lesson_title: str
    snippet: str
    relevance_score: float = 0.0


class AnswerResult(BaseModel):
    """Output of the Q&A service - a grounded answer plus its evidence."""

    question: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    concepts_referenced: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=_utcnow)


class LearningPathStep(BaseModel):
    concept: Concept
    rationale: str
    estimated_minutes: int
    resources: list[Citation] = Field(default_factory=list)


class LearningPlan(BaseModel):
    """A learner-specific, ordered plan from what they know to a goal concept."""

    goal_concept_id: str
    known_concept_ids: list[str]
    steps: list[LearningPathStep]
    summary: str
    total_estimated_minutes: int = 0

    @model_validator(mode="after")
    def _derive_total(self) -> LearningPlan:
        # Always recomputed from `steps` - never trust a caller-supplied
        # value, so the field can't drift out of sync with the steps it
        # summarizes. `field_validator` alone won't do this: Pydantic v2
        # skips per-field validators when a field is left at its default
        # (no `validate_default=True`), which is exactly the case for
        # every caller that never passes `total_estimated_minutes` in.
        self.total_estimated_minutes = sum(step.estimated_minutes for step in self.steps)
        return self


class GapAnalysisResult(BaseModel):
    """Comparison between what a learner knows and what a target requires."""

    target_id: str
    known_concept_ids: list[str]
    required_concept_ids: list[str]
    missing_concepts: list[Concept]
    readiness_pct: float = Field(ge=0.0, le=100.0)
