"""Tool for quiz_agent -- the assessment specialist.

Split out of the original single generate_lesson_content tool so quiz
writing and slide drafting (see agents/lesson_content/tools.py, owned by
lesson_content_agent) are two narrower specialists coordinated by
curriculum_team for one lesson-drafting request (see agents/team.py).

QuizDraft is a Pydantic model rather than a bare dict -- see
agents/curriculum/tools.py's docstring for why (validated calls,
provider-agnostic JSON schema), plus it lets us actually enforce the
"exactly four options, valid correctIndex" rule instead of just
documenting it in a docstring and hoping the model follows it.
"""
import logging
from typing import List

from agno.tools import tool
from pydantic import BaseModel, model_validator

from ... import store
from ... import audit
from ...auth.context import current_user_id

logger = logging.getLogger(__name__)


class QuizDraft(BaseModel):
    question: str
    options: List[str]
    correctIndex: int

    @model_validator(mode="after")
    def _validate_correct_index(self) -> "QuizDraft":
        if len(self.options) != 4:
            raise ValueError(f"options must have exactly 4 items, got {len(self.options)}")
        if not 0 <= self.correctIndex < len(self.options):
            raise ValueError(f"correctIndex {self.correctIndex} is out of range for {len(self.options)} options")
        return self


@tool(requires_confirmation=True)
def generate_lesson_quiz(lesson_id: str, quiz: QuizDraft) -> dict:
    """Write one multiple-choice quiz question for a lesson: a question,
    exactly four options, and a 0-based correctIndex identifying the
    correct option. Base it on the lesson's title and objective, and on
    the lesson's slides if lesson_content_agent has already drafted them
    (visible in context). Call this tool with the finished result.
    """
    logger.info("generate_lesson_quiz: lesson_id=%s", lesson_id)
    lesson = store.set_lesson_quiz(lesson_id, current_user_id(), quiz.question, quiz.options, quiz.correctIndex)
    if lesson is None:
        logger.error("generate_lesson_quiz: no lesson with id %s", lesson_id)
        raise ValueError(f"No lesson with id {lesson_id}")
    logger.info("generate_lesson_quiz: saved quiz for lesson %s", lesson_id)
    audit.record("generate_lesson_quiz", lesson_id, "Generated a lesson quiz")
    return lesson


TOOLS = [generate_lesson_quiz]
