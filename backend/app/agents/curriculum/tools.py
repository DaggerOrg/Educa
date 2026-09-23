"""Plain Python functions the curriculum agent (syllabus structure only)
can call.

Agno introspects each function's type hints and docstring to build its
tool schema -- no decorator or framework-specific wrapper needed beyond
`@tool(requires_confirmation=True)`, below. Each function is a plain
persistence step; the model does the creative work (drafting a syllabus)
and calls these with the finished, structured result as arguments. See
ARCH-01 SS03 for why generation and persistence are split this way.

Arguments are typed as Pydantic models (below), not bare dict/list --
Agno wraps every tool with pydantic's `validate_call`, so a malformed call
from the model (missing field, wrong type) is rejected before it reaches
this code, and every provider gets a fully-specified JSON schema. This
also fixed a real bug: Gemini's function-calling API 400s on an array
schema with no `items` (bare `list` produces exactly that); a typed model
schema doesn't have that gap for any provider.

Both tools require confirmation: Agno pauses the run and re-emits the
call as a normal AG-UI tool call, which the frontend renders as an
approve/reject card (see `frontend/src/components/ApprovalCards.tsx`) and
answers by resending the run with a tool result -- no separate resume
endpoint needed, see `agno.os.interfaces.agui.router.run_agent_agui`.
This requires the agent to have a `db` (see `agent.py`): the paused run's
state has to survive between the pause request and the resume request.

Lesson slides/notes and quiz tools live in `agents/lesson_content/tools.py`
and `agents/quiz/tools.py` respectively -- split into narrower specialists
so each has one job. Materials search/ingestion tools live on
`agents/materials/agent.py`. See `agents/team.py` for how all four agents
are coordinated under one `Team`.
"""
import logging
from typing import List

from agno.tools import tool
from pydantic import BaseModel, Field

from ... import store
from ... import audit
from ...auth.context import current_user_id

logger = logging.getLogger(__name__)


class LessonDraft(BaseModel):
    title: str
    objective: str = ""


class WeekDraft(BaseModel):
    week: int
    title: str
    lessons: List[LessonDraft] = Field(default_factory=list)


@tool(requires_confirmation=True)
def create_syllabus(title: str, audience: str, weeks: List[WeekDraft]) -> dict:
    """Create a new course syllabus, owned by the teacher in this
    conversation. Call this the first time a teacher describes a course
    they want to build, or whenever they ask to start a brand-new course.
    Design a complete 4-8 week syllabus yourself, 1-2 lessons per week,
    each lesson a title and a one-sentence objective -- then call this
    tool with the finished result.
    """
    teacher_id = current_user_id()
    logger.info("create_syllabus: teacher=%s title=%r weeks=%d", teacher_id, title, len(weeks))
    result = store.create_course(
        teacher_id=teacher_id, title=title, audience=audience, weeks=[w.model_dump() for w in weeks]
    )
    logger.info("create_syllabus: created course %s with %d week(s)", result["id"], len(result["weeks"]))
    audit.record("create_syllabus", result["id"], f"Created syllabus '{title}' ({len(weeks)} weeks)")
    return result


@tool(requires_confirmation=True)
def update_syllabus(course_id: str, weeks: List[WeekDraft], title: str = "", audience: str = "") -> dict:
    """Apply a refinement to an existing syllabus. `course_id` is the id of
    the course to update -- visible to you in the conversation context
    along with the rest of its current syllabus, including which lessons
    the teacher has manually edited. Preserve every manually-edited
    lesson's title and objective EXACTLY as given unless the teacher's
    instruction specifically targets it. Return the FULL updated list of
    weeks, not just the part that changed.
    """
    logger.info("update_syllabus: course=%s title=%r weeks=%d", course_id, title or "<unchanged>", len(weeks))
    result = store.update_syllabus(
        course_id=course_id,
        teacher_id=current_user_id(),
        title=title or None,
        audience=audience or None,
        weeks=[w.model_dump() for w in weeks],
    )
    logger.info("update_syllabus: course now has %d week(s)", len(result["weeks"]))
    audit.record("update_syllabus", course_id, f"Updated syllabus ({len(weeks)} weeks)")
    return result


TOOLS = [create_syllabus, update_syllabus]
