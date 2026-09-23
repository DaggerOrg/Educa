"""The quiz/assessment specialist: writes one multiple-choice question per
lesson.

Split out of curriculum_agent so slide/notes drafting (see
agents/lesson_content/agent.py) is a separate specialist -- curriculum_team
coordinates both members for a single "draft this lesson" request (see
agents/team.py's INSTRUCTIONS).
"""
from agno.agent import Agent

from ..storage import build_agent_db
from ..safety import with_safety_rules
from ..models import build_fallback_config, build_model
from .tools import TOOLS

INSTRUCTIONS = (
    "You write one multiple-choice quiz question per lesson, testing the "
    "lesson's objective: a question, exactly four options, and a 0-based "
    "correctIndex for the correct option. If lesson_content_agent has "
    "already drafted this lesson's slides (visible in context), base the "
    "question on that content for continuity; otherwise base it on the "
    "lesson's title and objective. Call generate_lesson_quiz with the "
    "finished result."
)


def build_quiz_agent() -> Agent:
    return Agent(
        name="quiz_agent",
        model=build_model(),
        fallback_config=build_fallback_config(),
        tools=TOOLS,
        instructions=with_safety_rules(INSTRUCTIONS),
        # Required for the requires_confirmation tool in tools.py: a paused
        # run's state lives here between the pause and resume request.
        db=build_agent_db(),
    )
