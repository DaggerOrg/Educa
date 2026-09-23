"""The lesson-content specialist: drafts slides and speaker notes for one
lesson at a time.

Split out of curriculum_agent so quiz writing (see agents/quiz/agent.py)
is its own specialist -- curriculum_team coordinates both members for a
single "draft this lesson" request (see agents/team.py's INSTRUCTIONS).
"""
from agno.agent import Agent

from ..storage import build_agent_db
from ..safety import with_safety_rules
from ..models import build_fallback_config, build_model
from .tools import TOOLS

INSTRUCTIONS = (
    "You write lesson slides and speaker notes. Given a lesson's title and "
    "objective (and, if materials_agent found relevant passages, ground "
    "your examples in those instead of inventing your own), compose 3-4 "
    "slides -- each a heading plus 2-4 short bullets -- and one paragraph "
    "of speaker notes. Call generate_lesson_slides with the finished "
    "result. You do not write quizzes -- quiz_agent handles that."
)


def build_lesson_content_agent() -> Agent:
    return Agent(
        name="lesson_content_agent",
        model=build_model(),
        fallback_config=build_fallback_config(),
        tools=TOOLS,
        instructions=with_safety_rules(INSTRUCTIONS),
        # Required for the requires_confirmation tool in tools.py: a paused
        # run's state lives here between the pause and resume request.
        db=build_agent_db(),
    )
