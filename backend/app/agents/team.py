"""The curriculum team: coordinates four specialists under one Agno `Team`,
which is what's actually mounted over AG-UI in `app.main`
(`AGUI(team=build_team())`) -- the React frontend talks to this team, not
to any member directly (see `frontend/src/App.tsx`'s
`agents__unsafe_dev_only` / `CopilotChat agentId`, both keyed to
`curriculum_team`, the team's own `name=`).

Each member lives in its own package under `agents/`, one folder per
specialist, each holding an `agent.py` (the `build_*_agent()` factory) and
a `tools.py` (its `@tool`-decorated functions) -- a uniform layout instead
of the old flat `agent/` directory where naming was inconsistent
(`agent.py`/`tools.py` for curriculum but `quiz_agent.py`/`quiz_tools.py`
for quiz). The four members: `agents/materials` (searches uploaded course
materials), `agents/curriculum` (syllabus structure), `agents/lesson_content`
(slides + speaker notes), and `agents/quiz` (assessment questions). Lesson
drafting used to be one agent's job; it's split into two narrower
specialists so each has a single tool and responsibility (see their own
docstrings). `agents/models.py` is the one shared, non-agent-specific file
-- model + fallback-list construction used by all four.

`Team` supports the exact same `requires_confirmation` pause/resume
mechanic as a single `Agent`, including propagating a paused member's
confirmation up through the team -- confirmed by reading
`agno/team/_run.py` and `agno/team/_hooks.py` directly rather than
assumed. It needs its own `db` for that pause/resume state, same as
every member already has.
"""
from agno.db.sqlite import SqliteDb
from agno.team import Team
from agno.team.mode import TeamMode

from .curriculum.agent import build_curriculum_agent
from .lesson_content.agent import build_lesson_content_agent
from .materials.agent import build_materials_agent
from .models import build_fallback_models, build_model
from .quiz.agent import build_quiz_agent

INSTRUCTIONS = (
    "Coordinate four specialists helping a teacher build a course. Delegate "
    "by member_id using these exact hyphenated ids -- Agno derives each "
    "member's id from its name via url_safe_string(), which turns "
    "underscores into hyphens, so the id is NOT the same string as the "
    "name below. Route requests about searching uploaded materials to "
    "materials-agent (name: materials_agent). Route syllabus structure -- "
    "creating or changing the course/week/lesson outline -- to "
    "curriculum-agent (name: curriculum_agent). Route lesson slides and "
    "speaker notes to lesson-content-agent (name: lesson_content_agent). "
    "Route quiz/assessment writing to quiz-agent (name: quiz_agent). "
    "If a request would benefit from the teacher's uploaded materials, "
    "have materials_agent search first and pass what it finds to whichever "
    "specialist drafts next. When asked to draft or regenerate a full "
    "lesson (not just its slides or just its quiz), call BOTH "
    "lesson_content_agent and quiz_agent for that lesson -- a complete "
    "lesson needs both, and quiz_agent should go second so it can see the "
    "slides lesson_content_agent just wrote."
)


def build_team() -> Team:
    return Team(
        name="curriculum_team",
        members=[
            build_materials_agent(),
            build_curriculum_agent(),
            build_lesson_content_agent(),
            build_quiz_agent(),
        ],
        model=build_model(),
        fallback_models=build_fallback_models(),
        mode=TeamMode.coordinate,
        instructions=INSTRUCTIONS,
        db=SqliteDb(db_file="tmp/educa_agent.db"),
    )
