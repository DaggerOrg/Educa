from enum import StrEnum


class BloomLevel(StrEnum):
    """Bloom's Taxonomy cognitive levels, ordered from lowest to highest."""

    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"

    @property
    def rank(self) -> int:
        return list(BloomLevel).index(self)


class DifficultyLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

    @property
    def rank(self) -> int:
        return list(DifficultyLevel).index(self)


class RelationType(StrEnum):
    """Edge labels in the concept graph."""

    REQUIRES = "requires"  # concept A cannot be understood without concept B
    RELATES_TO = "relates_to"  # weaker, non-blocking association
    PART_OF = "part_of"  # concept A is a sub-topic of concept B
    EXTENDS = "extends"  # concept A builds on / generalizes concept B


class ConceptSource(StrEnum):
    """How a concept or edge entered the graph - matters for trust/auditing."""

    AUTHORED = "authored"  # explicitly declared in the curriculum spec
    LLM_EXTRACTED = "llm_extracted"  # inferred by Claude from lesson content
