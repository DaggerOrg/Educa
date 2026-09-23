"""Tool for knowledge_graph_agent -- proposes a new collaborative
knowledge-graph board (see frontend/src/knowledge-graph/live/) pre-filled
with concept/skill nodes and relationships, instead of a teacher building
one from a blank canvas.

NodeDraft/RelationshipDraft are Pydantic models for the same reason as
QuizDraft/ExerciseDraft (agents/quiz, agents/exercises/tools.py): validated
calls and an enforced schema. Two flat list params (not one wrapper model
holding both lists) to match those tools' style, and because a
cross-referential check (every relationship's endpoints name a real node
id) is simplest as a plain check in the tool body, not a nested
model_validator.
"""
import logging
from typing import List, Literal

from agno.tools import tool
from pydantic import BaseModel

from ... import kg_boards
from ... import audit
from ...auth.context import current_user_id

logger = logging.getLogger(__name__)

NodeType = Literal["concept", "skill", "learning_objective", "exercise", "resource", "level"]
RelationshipType = Literal[
    "prerequisite_of", "part_of", "practices", "assesses", "teaches",
    "uses", "explained_by", "supported_by", "belongs_to_level", "reinforces",
]


class NodeDraft(BaseModel):
    id: str  # A short stable slug this call invents, e.g. "photosynthesis" -- referenced by RelationshipDraft below.
    type: NodeType
    name: str
    cefr_level: Literal["A1", "A2", "B1", "B2", "C1", "C2"] | None = None


class RelationshipDraft(BaseModel):
    source_id: str
    target_id: str
    type: RelationshipType


@tool(requires_confirmation=True)
def generate_knowledge_graph(title: str, nodes: List[NodeDraft], relationships: List[RelationshipDraft]) -> dict:
    """Create a new collaborative knowledge-graph board titled `title`,
    pre-populated with proposed concept/skill/learning_objective/exercise/
    resource/level nodes and the relationships between them (e.g.
    prerequisite_of, part_of, teaches). Invent short stable string ids for
    each node (e.g. "photosynthesis") and reference those same ids as
    source_id/target_id in relationships. The board opens for every
    lecturer to review, adjust, and approve live -- it's a starting point,
    not a finished graph.
    """
    node_ids = {n.id for n in nodes}
    bad = [r for r in relationships if r.source_id not in node_ids or r.target_id not in node_ids]
    if bad:
        raise ValueError(
            f"relationship(s) reference a node id not in `nodes`: "
            f"{[(r.source_id, r.target_id) for r in bad]}"
        )

    logger.info("generate_knowledge_graph: title=%r nodes=%d relationships=%d", title, len(nodes), len(relationships))
    board = kg_boards.create_board(current_user_id(), title)
    kg_boards.seed_graph(
        board["id"],
        [n.model_dump() for n in nodes],
        [r.model_dump() for r in relationships],
    )
    logger.info("generate_knowledge_graph: created board=%s", board["id"])
    audit.record("generate_knowledge_graph", board["id"], f"Created knowledge graph '{title}' ({len(nodes)} nodes)")
    return board


TOOLS = [generate_knowledge_graph]
