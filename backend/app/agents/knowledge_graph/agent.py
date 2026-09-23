"""The knowledge-graph specialist: proposes a new collaborative
knowledge-graph board (see frontend/src/knowledge-graph/live/) pre-filled
with concept/skill nodes and relationships from a syllabus or the
teacher's uploaded materials, instead of a teacher starting from a blank
canvas.
"""
from agno.agent import Agent

from ..storage import build_agent_db
from ..safety import with_safety_rules
from ..models import build_fallback_config, build_model
from .tools import TOOLS

INSTRUCTIONS = (
    "You propose knowledge graphs: concepts, skills, learning objectives, "
    "exercises, resources, and levels, connected by relationships like "
    "prerequisite_of, part_of, teaches, practices, assesses, and "
    "reinforces. Base the graph on whatever the teacher describes -- a "
    "course syllabus (visible in context), a topic they name, or "
    "materials_agent's search results if grounding is needed. Aim for "
    "10-25 nodes with a clear prerequisite structure, not a flat "
    "unconnected list -- most nodes should have at least one relationship. "
    "Call generate_knowledge_graph once with the full proposed graph and a "
    "short, descriptive title. This creates a brand new board; it never "
    "edits an existing one."
)


def build_knowledge_graph_agent() -> Agent:
    return Agent(
        name="knowledge_graph_agent",
        model=build_model(),
        fallback_config=build_fallback_config(),
        tools=TOOLS,
        instructions=with_safety_rules(INSTRUCTIONS),
        # Required for the requires_confirmation tool in tools.py: a paused
        # run's state lives here between the pause and resume request.
        db=build_agent_db(),
    )
