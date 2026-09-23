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

from ... import knowledge as kb
from ..storage import build_agent_db
from ..safety import with_safety_rules
from ..models import build_fallback_config, build_model

INSTRUCTIONS = (
    "You manage the teacher's uploaded course materials. Use "
    "search_knowledge_base to find passages relevant to a topic when asked, "
    "or when curriculum_agent needs grounding for a syllabus or lesson."
)


def build_materials_agent() -> Agent:
    return Agent(
        name="materials_agent",
        model=build_model(),
        fallback_config=build_fallback_config(),
        knowledge=kb.knowledge,
        instructions=with_safety_rules(INSTRUCTIONS),
        db=build_agent_db(),
    )
