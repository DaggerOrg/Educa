"""Tools for feedback_agent -- the assessment-feedback specialist.

Two tools, a read then a write, since the model has no other way to learn
a real `attempt_id` to write feedback for: a teacher says something like
"give feedback on quiz attempts for the photosynthesis lesson", and the
model must first call `list_quiz_attempts` to see who attempted it and
their scores before it can call the write tool with a specific id.
`list_quiz_attempts` is a plain read (no `requires_confirmation`, same
reasoning as materials_agent's `search_knowledge_base`); writing feedback
is a teacher-visible/student-visible AI action, so it's gated like every
other content-mutating tool in this codebase.
"""
import logging

from agno.tools import tool

from ... import store
from ... import audit
from ...auth.context import current_user_id

logger = logging.getLogger(__name__)


@tool
def list_quiz_attempts(lesson_id: str) -> list[dict]:
    """List every student's quiz attempts for a lesson -- id, student name,
    score, existing feedback (if any), and submission time, most recent
    first. Call this before writing feedback, to find the attempt(s) to
    address and see what's already been said.
    """
    logger.info("list_quiz_attempts: lesson_id=%s", lesson_id)
    return store.list_lesson_quiz_attempts(lesson_id, current_user_id())


@tool(requires_confirmation=True)
def generate_attempt_feedback(attempt_id: str, feedback: str) -> dict:
    """Write personalized feedback for one student's quiz attempt --
    acknowledge what they got right, explain what they missed and why the
    correct answer is correct, and suggest one concrete next step. Keep it
    encouraging and specific to their actual answer, not generic. The
    student sees this feedback alongside their score.
    """
    logger.info("generate_attempt_feedback: attempt_id=%s", attempt_id)
    result = store.set_quiz_attempt_feedback(attempt_id, current_user_id(), feedback)
    logger.info("generate_attempt_feedback: saved feedback for attempt %s", attempt_id)
    audit.record("generate_attempt_feedback", attempt_id, "Wrote feedback for a quiz attempt")
    return result


TOOLS = [list_quiz_attempts, generate_attempt_feedback]
