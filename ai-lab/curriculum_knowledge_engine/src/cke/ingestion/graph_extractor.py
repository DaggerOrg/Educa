"""LLM-based knowledge-graph enrichment.

The curriculum author declares the *backbone* prerequisite graph by hand
(`CurriculumSpec.concepts[].requires`) - that's authoritative. This module
asks Claude to read each lesson's actual prose and point out prerequisite
relationships the text implies but the author didn't declare (a lesson that
casually assumes the reader already knows some concept it never lists as a
formal prerequisite is exactly the kind of gap this catches). Every
extracted edge is tagged `ConceptSource.LLM_EXTRACTED` with a confidence
score and rationale, so it's always possible to tell an author's ground
truth from a model's suggestion, and a low-confidence or graph-breaking
suggestion can be filtered or rejected without touching the authored graph.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from cke.domain.enums import RelationType
from cke.domain.models import Lesson
from cke.llm.claude_client import ClaudeClient
from cke.logging_config import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a curriculum knowledge-graph analyst. You read one lesson at a time \
and identify prerequisite-style relationships between concepts that ARE IN \
THE PROVIDED CONCEPT LIST ONLY. Never invent a concept name that is not in \
the list, and never emit a relationship whose source and target are the \
same concept. Be conservative: only report a relationship you can point to \
direct textual evidence for, and give it an honest confidence score - most \
genuine relationships should score 0.6-0.9, not 1.0."""


class ExtractedRelationship(BaseModel):
    source_concept: str = Field(description="Exact concept name from the provided list.")
    target_concept: str = Field(description="Exact concept name from the provided list.")
    relation: RelationType
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(description="One sentence citing the textual evidence.")


class GraphExtractionResult(BaseModel):
    relationships: list[ExtractedRelationship] = Field(default_factory=list)


def build_extraction_prompt(lesson: Lesson, known_concept_names: list[str]) -> str:
    concept_list = "\n".join(f"- {name}" for name in known_concept_names)
    return (
        f"Known concepts for this curriculum:\n{concept_list}\n\n"
        f"Lesson title: {lesson.title}\n\n"
        f"Lesson content:\n{lesson.content}\n\n"
        "Identify prerequisite-style relationships this lesson's text implies "
        "between concepts in the known-concepts list above. Only use relation "
        "types requires, relates_to, part_of, extends. Return an empty list if "
        "the lesson doesn't clearly imply any relationship beyond what's obvious "
        "from its title."
    )


def extract_relationships(
    client: ClaudeClient, lesson: Lesson, known_concept_names: list[str]
) -> GraphExtractionResult:
    if not known_concept_names:
        return GraphExtractionResult(relationships=[])

    prompt = build_extraction_prompt(lesson, known_concept_names)
    result = client.extract(
        prompt, output_model=GraphExtractionResult, system=_SYSTEM_PROMPT
    )

    known_lower = {name.lower() for name in known_concept_names}
    valid: list[ExtractedRelationship] = []
    for rel in result.relationships:
        if rel.source_concept.lower() not in known_lower:
            logger.warning(
                "Dropping extracted relationship with unknown source concept: %s",
                rel.source_concept,
            )
            continue
        if rel.target_concept.lower() not in known_lower:
            logger.warning(
                "Dropping extracted relationship with unknown target concept: %s",
                rel.target_concept,
            )
            continue
        if rel.source_concept.lower() == rel.target_concept.lower():
            logger.warning("Dropping self-referential extracted relationship: %s", rel.source_concept)
            continue
        valid.append(rel)

    return GraphExtractionResult(relationships=valid)
