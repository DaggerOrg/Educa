"""The materials agent: owns the teacher's uploaded course materials.

Given `knowledge=`, Agno automatically adds a `search_knowledge_base` tool
to this agent -- no hand-written retrieval tool needed
(`agent.search_knowledge` defaults to True). There's no ingestion tool
here: uploading is a plain REST operation (`POST /api/materials` in
`main.py`, backed by `app/knowledge.py`) that indexes a file immediately,
the same way editing a lesson is a plain REST edit rather than something
routed through the agent -- a reference document isn't a creative AI
action that needs a teacher's sign-off.
"""
from agno.agent import Agent
from agno.db.sqlite import SqliteDb

from ... import knowledge as kb
from ..models import build_fallback_models, build_model

INSTRUCTIONS = (
    "You manage the teacher's uploaded course materials. Use "
    "search_knowledge_base to find passages relevant to a topic when asked, "
    "or when curriculum_agent needs grounding for a syllabus or lesson."
)


def build_materials_agent() -> Agent:
    return Agent(
        name="materials_agent",
        model=build_model(),
        fallback_models=build_fallback_models(),
        knowledge=kb.knowledge,
        instructions=INSTRUCTIONS,
        db=SqliteDb(db_file="tmp/educa_agent.db"),
    )
