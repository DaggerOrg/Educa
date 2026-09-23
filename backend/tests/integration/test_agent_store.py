"""The shared Agno store (agents/storage.py): approval/run state and the Ask AI
history now live in Postgres, and chat_history must read exactly what the
team wrote there -- a regression here would silently empty every teacher's
conversation history.
"""
import os
import sys
import time
import uuid
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://educa:educa@localhost:55432/educa")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
sys.path.insert(0, str(Path(__file__).parents[2]))

from agno.db.postgres import PostgresDb  # noqa: E402
from agno.run.agent import RunInput  # noqa: E402
from agno.run.team import TeamRunOutput  # noqa: E402
from agno.session import TeamSession  # noqa: E402

from app import chat_history  # noqa: E402
from app.agents.storage import build_agent_db  # noqa: E402
from app.agents.team import build_team  # noqa: E402


@pytest.fixture
def team_session():
    db = build_agent_db()
    user_id, session_id = f"user_store_{uuid.uuid4().hex[:8]}", f"sess_{uuid.uuid4().hex[:8]}"
    run = TeamRunOutput(
        run_id=f"run_{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        team_id="curriculum-team",
        user_id=user_id,
        input=RunInput(input_content="Build me a 4 week Python syllabus"),
        content="Here is a draft syllabus.",
        created_at=int(time.time()),
    )
    now = int(time.time())
    db.upsert_session(
        TeamSession(
            session_id=session_id, team_id="curriculum-team", user_id=user_id, created_at=now, updated_at=now
        )
    )
    # Runs are stored per-run, the same call agno/team/_storage.py makes -- not inside the session row.
    db.upsert_run(run=run, session_id=session_id, user_id=user_id, run_index=0)
    yield {"user_id": user_id, "session_id": session_id}
    db.delete_session(session_id)


@pytest.mark.integration
def test_agents_share_one_postgres_store_by_default():
    team = build_team()
    assert isinstance(team.db, PostgresDb)
    assert all(member.db is team.db for member in team.members if member.db is not None)


@pytest.mark.integration
def test_history_written_by_the_team_is_readable_by_its_owner_only(team_session):
    listed = chat_history.list_my_sessions(team_session["user_id"])
    assert [s["id"] for s in listed] == [team_session["session_id"]]
    assert listed[0]["title"] == "Build me a 4 week Python syllabus"

    transcript = chat_history.get_session_transcript(team_session["user_id"], team_session["session_id"])
    assert transcript == [
        {"role": "user", "content": "Build me a 4 week Python syllabus"},
        {"role": "assistant", "content": "Here is a draft syllabus."},
    ]

    assert chat_history.list_my_sessions("someone-else") == []
    assert chat_history.get_session_transcript("someone-else", team_session["session_id"]) is None


@pytest.mark.integration
def test_sqlite_can_still_be_selected_for_local_use(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_DB", "sqlite")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tmp").mkdir()
    build_agent_db.cache_clear()
    try:
        assert type(build_agent_db()).__name__ == "SqliteDb"
    finally:
        monkeypatch.delenv("AGENT_DB")
        build_agent_db.cache_clear()
