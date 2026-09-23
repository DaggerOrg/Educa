"""The authoring format for a curriculum (YAML/JSON on disk) - distinct from
`cke.domain.models`, which is the in-memory/runtime representation.

The authoring format is optimized for a human writing a course by hand:
concepts and their prerequisite relationships are declared once, by human-
readable *name*, in a top-level `concepts:` block; lessons then simply list
which concept names they `teaches:`. `CurriculumIngestionService` resolves
names to slug ids and expands this into `Concept` / `PrerequisiteEdge` /
`Course` / `Module` / `Lesson` domain objects.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

from cke.domain.enums import BloomLevel, DifficultyLevel


class ObjectiveSpec(BaseModel):
    text: str
    bloom_level: BloomLevel = BloomLevel.UNDERSTAND


class ConceptSpec(BaseModel):
    name: str
    description: str = ""
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    requires: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)


class LessonSpec(BaseModel):
    id: str
    title: str
    content: str
    estimated_minutes: int = 15
    teaches: list[str] = Field(default_factory=list)
    objectives: list[ObjectiveSpec] = Field(default_factory=list)


class ModuleSpec(BaseModel):
    id: str
    title: str
    description: str = ""
    lessons: list[LessonSpec] = Field(default_factory=list)


class CurriculumSpec(BaseModel):
    """Root of one curriculum authoring file."""

    id: str
    title: str
    description: str = ""
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    concepts: list[ConceptSpec] = Field(default_factory=list)
    modules: list[ModuleSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_referential_integrity(self) -> CurriculumSpec:
        known_names = {concept.name for concept in self.concepts}
        for concept in self.concepts:
            unknown = [req for req in concept.requires if req not in known_names]
            if unknown:
                raise ValueError(
                    f"Concept '{concept.name}' requires unknown concept(s): {unknown}"
                )
        for module in self.modules:
            for lesson in module.lessons:
                unknown = [name for name in lesson.teaches if name not in known_names]
                if unknown:
                    raise ValueError(
                        f"Lesson '{lesson.id}' teaches unknown concept(s): {unknown}"
                    )
        return self

    @classmethod
    def from_file(cls, path: Path | str) -> CurriculumSpec:
        path = Path(path)
        raw = path.read_text()
        data = yaml.safe_load(raw) if path.suffix in {".yaml", ".yml"} else json.loads(raw)
        return cls.model_validate(data)
