"""Offline guards on the agent design -- properties that must hold no matter
which model is behind them, so they run in CI with no API key. They do NOT
measure answer quality (that needs live model evals); they stop the safety
and wiring properties from silently regressing.
"""
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://educa:educa@localhost:55432/educa")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
sys.path.insert(0, str(Path(__file__).parents[2]))

from agno.utils.string import url_safe_string  # noqa: E402
from google import genai  # noqa: E402
from google.genai import _transformers  # noqa: E402

from app.agents.creative.tools import TOOLS as CREATIVE_TOOLS  # noqa: E402
from app.agents.curriculum.tools import TOOLS as CURRICULUM_TOOLS  # noqa: E402
from app.agents.exercises.tools import TOOLS as EXERCISE_TOOLS  # noqa: E402
from app.agents.faculty import schemas as faculty_schemas  # noqa: E402
from app.agents.feedback.tools import TOOLS as FEEDBACK_TOOLS  # noqa: E402
from app.agents.knowledge_graph.tools import TOOLS as KG_TOOLS  # noqa: E402
from app.agents.lesson_content.tools import TOOLS as LESSON_TOOLS  # noqa: E402
from app.agents.quiz.tools import TOOLS as QUIZ_TOOLS  # noqa: E402
from app.agents.safety import UNTRUSTED_TEXT_RULE  # noqa: E402
from app.agents.team import build_team  # noqa: E402

ALL_TOOLS = [
    *CURRICULUM_TOOLS, *LESSON_TOOLS, *QUIZ_TOOLS, *EXERCISE_TOOLS,
    *FEEDBACK_TOOLS, *KG_TOOLS, *CREATIVE_TOOLS,
]
# The only tools allowed to run without a teacher's approval: they read, never write.
READ_ONLY_TOOLS = {"list_quiz_attempts"}


@pytest.fixture(scope="module")
def team():
    return build_team()


@pytest.mark.unit
def test_every_content_changing_tool_requires_teacher_approval():
    unapproved = [t.name for t in ALL_TOOLS if t.name not in READ_ONLY_TOOLS and not t.requires_confirmation]
    assert unapproved == [], f"these tools change content without approval: {unapproved}"


@pytest.mark.unit
def test_read_only_allowlist_has_no_stale_entries():
    assert READ_ONLY_TOOLS <= {t.name for t in ALL_TOOLS}


@pytest.mark.unit
def test_coordinator_names_every_member_by_its_real_delegation_id(team):
    """The coordinator delegates by hyphenated id, derived from each member's name. A rename
    that isn't mirrored in the routing instructions leaves that specialist unreachable."""
    for member in team.members:
        assert url_safe_string(member.name) in team.instructions, f"{member.name} missing from routing instructions"
        assert f"name: {member.name}" in team.instructions


@pytest.mark.unit
def test_coordinator_states_the_right_number_of_specialists(team):
    words = {6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}
    assert f"Coordinate {words[len(team.members)]} specialists" in team.instructions


@pytest.mark.unit
def test_agents_that_read_uploaded_material_carry_the_untrusted_text_rule(team):
    assert UNTRUSTED_TEXT_RULE in team.instructions
    drafting = {"materials_agent", "curriculum_agent", "lesson_content_agent", "quiz_agent",
                "exercises_agent", "creative_agent", "knowledge_graph_agent"}
    missing = [m.name for m in team.members if m.name in drafting and UNTRUSTED_TEXT_RULE not in str(m.instructions)]
    assert missing == []


@pytest.mark.unit
def test_every_agent_retries_on_rate_limit_not_only_on_error(team):
    for agent in [team, *team.members]:
        config = agent.fallback_config
        assert config.on_error and config.on_rate_limit, f"{agent.name} has no rate-limit fallback"


@pytest.mark.unit
def test_all_members_share_the_one_agent_store(team):
    assert all(member.db is team.db for member in team.members if member.db is not None)


def _arrays_without_items(node, path=""):
    if isinstance(node, dict):
        if node.get("type") == "array" and "items" not in node:
            yield path or "<root>"
        for key, value in node.items():
            yield from _arrays_without_items(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _arrays_without_items(value, f"{path}[{index}]")


@pytest.mark.unit
@pytest.mark.parametrize("tool", ALL_TOOLS, ids=lambda t: t.name)
def test_tool_schemas_have_no_arrays_without_items(tool):
    """Gemini's function-calling API 400s on an array schema with no `items` (a bug this repo
    already hit once -- see agents/curriculum/tools.py)."""
    tool.process_entrypoint()
    assert list(_arrays_without_items(tool.parameters)) == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "schema",
    [faculty_schemas.ConceptAnalysis, faculty_schemas.TheoryBreakdown,
     faculty_schemas.ExerciseBreakdown, faculty_schemas.ChairSummary],
    ids=lambda s: s.__name__,
)
def test_structured_output_schemas_convert_for_gemini_without_defaults(schema):
    converted = _transformers.t_schema(genai.Client(api_key="x"), schema).model_dump(exclude_none=True, mode="json")
    assert list(_arrays_without_items(converted)) == []
    assert "default" not in str(converted), "a schema `default` is sent to Gemini, which some API versions reject"
