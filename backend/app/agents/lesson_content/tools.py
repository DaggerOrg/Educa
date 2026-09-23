"""Tool for lesson_content_agent -- the slides/speaker-notes specialist.

Split out of the original single generate_lesson_content tool so slide
drafting and quiz writing (see agents/quiz/tools.py, owned by quiz_agent)
are two narrower specialists coordinated by curriculum_team for one
lesson-drafting request (see agents/team.py), rather than one agent doing
both.

Arguments are typed as Pydantic models rather than bare dict/list -- see
agents/curriculum/tools.py's docstring for why (validated calls, and a
fully-specified JSON schema for every model provider, including Gemini
which 400s on an itemless array schema).
"""
import logging
from typing import List

from agno.tools import tool
from pydantic import BaseModel, Field

from ... import store
from ... import audit
from ...auth.context import current_user_id

logger = logging.getLogger(__name__)


class SlideDraft(BaseModel):
    heading: str
    bullets: List[str] = Field(default_factory=list)


@tool(requires_confirmation=True)
def generate_lesson_slides(lesson_id: str, slides: List[SlideDraft], speaker_notes: str) -> dict:
    """Write one lesson's slides and speaker notes: 3-4 slides (each a
    heading + 2-4 short bullets) and one paragraph of speaker notes.
    Compose the content yourself from the lesson's title and objective
    (visible in context -- ask the teacher which lesson if it's ambiguous),
    then call this tool with the finished result. You do not write the
    quiz -- that's a separate specialist's job.
    """
    logger.info("generate_lesson_slides: lesson_id=%s slides=%d", lesson_id, len(slides))
    lesson = store.set_lesson_slides(
        lesson_id, current_user_id(), [s.model_dump() for s in slides], speaker_notes
    )
    if lesson is None:
        logger.error("generate_lesson_slides: no lesson with id %s", lesson_id)
        raise ValueError(f"No lesson with id {lesson_id}")
    logger.info("generate_lesson_slides: saved slides for lesson %s", lesson_id)
    audit.record("generate_lesson_slides", lesson_id, f"Generated {len(slides)} slide(s)")
    return lesson


TOOLS = [generate_lesson_slides]
