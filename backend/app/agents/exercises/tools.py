"""Tool for exercises_agent -- the Exercises Builder specialist.

ExerciseDraft is a Pydantic model, same reasoning as quiz/tools.py's
QuizDraft: validated calls, a provider-agnostic JSON schema, and an actual
enforced "the right fields for this kind" rule instead of just a
docstring. Unlike QuizDraft (always exactly one multiple-choice question),
this tool accepts a *list* of drafts in mixed kinds -- multiple_choice,
true_false, flashcard -- generated together as one exercise set.
"""
import logging
from typing import List, Literal, Optional

from agno.tools import tool
from pydantic import BaseModel, model_validator

from ... import store
from ...auth.context import current_user_id

logger = logging.getLogger(__name__)


class ExerciseDraft(BaseModel):
    kind: Literal["multiple_choice", "true_false", "flashcard"]
    prompt: str
    options: Optional[List[str]] = None
    correct_answer: Optional[int] = None
    back: Optional[str] = None

    @model_validator(mode="after")
    def _validate_fields_for_kind(self) -> "ExerciseDraft":
        if self.kind == "flashcard":
            if not self.back:
                raise ValueError("flashcard exercises require `back`")
            if self.options is not None or self.correct_answer is not None:
                raise ValueError("flashcard exercises must not set options/correct_answer")
            return self

        # multiple_choice / true_false both need options + a valid correct_answer index.
        if self.back is not None:
            raise ValueError(f"{self.kind} exercises must not set `back`")
        if self.options is None or self.correct_answer is None:
            raise ValueError(f"{self.kind} exercises require options and correct_answer")
        if self.kind == "true_false" and self.options != ["True", "False"]:
            raise ValueError('true_false exercises must set options to exactly ["True", "False"]')
        if self.kind == "multiple_choice" and len(self.options) < 2:
            raise ValueError("multiple_choice exercises require at least 2 options")
        if not 0 <= self.correct_answer < len(self.options):
            raise ValueError(f"correct_answer {self.correct_answer} is out of range for {len(self.options)} options")
        return self


@tool(requires_confirmation=True)
def generate_lesson_exercises(lesson_id: str, exercises: List[ExerciseDraft]) -> dict:
    """Generate a set of exercises for a lesson -- any mix of multiple
    choice, true/false, and flashcards. Base them on the lesson's title
    and objective, and on its slides/quiz if already drafted (visible in
    context). Call this tool once with the full finished set.
    """
    logger.info("generate_lesson_exercises: lesson_id=%s count=%d", lesson_id, len(exercises))
    lesson = store.add_lesson_exercises(
        lesson_id,
        current_user_id(),
        [ex.model_dump() for ex in exercises],
    )
    if lesson is None:
        logger.error("generate_lesson_exercises: no lesson with id %s", lesson_id)
        raise ValueError(f"No lesson with id {lesson_id}")
    logger.info("generate_lesson_exercises: saved %d exercise(s) for lesson %s", len(exercises), lesson_id)
    return lesson


TOOLS = [generate_lesson_exercises]
