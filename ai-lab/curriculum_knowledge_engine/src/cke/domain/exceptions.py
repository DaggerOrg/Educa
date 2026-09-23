class CKEError(Exception):
    """Base class for every domain-level error raised by this application.

    API route handlers catch this (see api/error_handlers.py) so a domain
    error never leaks as an unhandled 500 with a stack trace.
    """


class NotFoundError(CKEError):
    """A requested entity (course, concept, lesson, ...) does not exist."""

    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} '{entity_id}' not found")


class ValidationError(CKEError):
    """Input failed a domain rule that a schema alone cannot express."""


class CurriculumIngestionError(CKEError):
    """Ingesting a curriculum spec into the knowledge base failed."""


class CyclicPrerequisiteError(CKEError):
    """Adding an edge would create a prerequisite cycle (A requires B requires A)."""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        super().__init__(f"Prerequisite cycle detected: {' -> '.join(cycle)}")


class UnreachableGoalError(CKEError):
    """No valid learning path exists from what the learner knows to the goal."""

    def __init__(self, goal_concept: str, missing: list[str]):
        self.goal_concept = goal_concept
        self.missing = missing
        super().__init__(
            f"Cannot reach '{goal_concept}': prerequisite concepts not in the "
            f"knowledge graph: {', '.join(missing)}"
        )


class LLMGenerationError(CKEError):
    """Claude call failed or returned output that couldn't be used.

    Wraps the underlying anthropic.APIError chain so callers only need to
    catch one exception type at the service/API boundary, while the
    original error is preserved via `__cause__` for logging/debugging.
    """

    def __init__(self, message: str, *, retryable: bool = False):
        self.retryable = retryable
        super().__init__(message)
