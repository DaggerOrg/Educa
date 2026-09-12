"""The curriculum agent (syllabus structure only), built with Agno.

One of four members of the `curriculum_team` (see `agents/team.py`), which
is what's actually exposed over AG-UI (mounted in app.main) -- no
LangGraph, no LangChain, and no Node "Copilot Runtime" in front of it: the
team's members call their model provider themselves, and Agno's router
speaks AG-UI straight to the React frontend. See the project README for
the earlier LangGraph-based version this replaces and why.
"""
from agno.agent import Agent
from agno.db.sqlite import SqliteDb

from ..models import build_fallback_models, build_model
from .tools import TOOLS

INSTRUCTIONS = (
    "You are Educa's curriculum agent, helping a teacher design a course's "
    "syllabus structure. If materials_agent's search_knowledge_base returns "
    "relevant passages from the teacher's uploaded materials, follow a "
    "faculty curriculum's topic order and pacing when one is uploaded. If "
    "nothing relevant is available, fall back to your own knowledge. "
    "When a teacher first describes a course, or asks to start a new one, "
    "design a complete syllabus yourself and call create_syllabus. When "
    "asked to change the syllabus of a course that already exists (its id "
    "and current syllabus are visible in context), call update_syllabus "
    "with that course's id and the full updated syllabus, preserving any "
    "lesson the teacher has manually edited unless they ask to change it. "
    "Always call a tool to make a syllabus change -- do not just describe "
    "the change in the chat. You do not write lesson slides, speaker "
    "notes, or quizzes -- lesson_content_agent and quiz_agent handle those."
)


def build_curriculum_agent() -> Agent:
    return Agent(
        name="curriculum_agent",
        model=build_model(),
        # Free-tier Gemini occasionally returns 503 UNAVAILABLE under load --
        # Agno retries the same failed run against these in order instead of
        # surfacing the error to the teacher.
        fallback_models=build_fallback_models(),
        tools=TOOLS,
        instructions=INSTRUCTIONS,
        # Required for the two requires_confirmation tools in tools.py: a
        # paused run's requirements live here between the pause request and
        # the resume request, not just in memory (see tools.py docstring).
        db=SqliteDb(db_file="tmp/educa_agent.db"),
    )
