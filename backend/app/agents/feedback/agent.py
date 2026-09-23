"""The assessment-feedback specialist: reviews a lesson's quiz attempts and
writes personalized feedback for individual students.

The one member that reads real student data rather than only drafting
course content -- see tools.py for why it needs a read tool
(`list_quiz_attempts`) before its write tool.
"""
from agno.agent import Agent

from ..storage import build_agent_db
from ..models import build_fallback_config, build_model
from .tools import TOOLS

INSTRUCTIONS = (
    "You review student quiz attempts and write feedback. When asked about "
    "a lesson's attempts, call list_quiz_attempts first to see who "
    "attempted it, their scores, and any existing feedback. When asked to "
    "give feedback (on one student, or on everyone who's attempted a "
    "quiz), call generate_attempt_feedback once per attempt: acknowledge "
    "what they got right, explain what they missed and why the correct "
    "answer is correct, and suggest one concrete next step. Keep feedback "
    "encouraging and specific to that student's actual answer, not "
    "generic praise or criticism. Don't overwrite feedback that's already "
    "there unless asked to."
)


def build_feedback_agent() -> Agent:
    return Agent(
        name="feedback_agent",
        model=build_model(),
        fallback_config=build_fallback_config(),
        tools=TOOLS,
        instructions=INSTRUCTIONS,
        # Required for the requires_confirmation tool in tools.py: a paused
        # run's state lives here between the pause and resume request.
        db=build_agent_db(),
    )
