"""The Exercises Builder specialist: generates practice exercises for a
lesson -- multiple choice, true/false, and flashcards -- as one set per
call, distinct from quiz_agent's single graded quiz question (see
agents/quiz/agent.py). Exercises are for practice, not the summative quiz
students are scored on.
"""
from agno.agent import Agent
from agno.db.sqlite import SqliteDb

from ..models import build_fallback_models, build_model
from .tools import TOOLS

INSTRUCTIONS = (
    "You generate practice exercises for a lesson: any mix of multiple "
    "choice, true/false, and flashcards, as requested. A multiple_choice "
    "exercise needs a prompt, at least two options, and a 0-based "
    "correct_answer index. A true_false exercise needs a prompt, options "
    "set to exactly [\"True\", \"False\"], and a 0-based correct_answer "
    "index. A flashcard needs a prompt (the front) and a back -- no "
    "options or correct_answer. If lesson_content_agent has already "
    "drafted this lesson's slides (visible in context), base exercises on "
    "that content for continuity; otherwise base them on the lesson's "
    "title and objective. Call generate_lesson_exercises once with the "
    "full finished set."
)


def build_exercises_agent() -> Agent:
    return Agent(
        name="exercises_agent",
        model=build_model(),
        fallback_models=build_fallback_models(),
        tools=TOOLS,
        instructions=INSTRUCTIONS,
        # Required for the requires_confirmation tool in tools.py: a paused
        # run's state lives here between the pause and resume request.
        db=SqliteDb(db_file="tmp/educa_agent.db"),
    )
