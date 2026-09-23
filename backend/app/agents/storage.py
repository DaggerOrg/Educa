"""The one Agno session/run store shared by every agent, the team, and
chat_history.py.

Holds the state a `requires_confirmation` tool needs between "the agent
paused for approval" and "the teacher clicked approve", plus the Ask AI
conversation history. It used to be a SQLite file under `tmp/`, which meant
a pending approval vanished on redeploy and split across replicas. It now
lives in the same Postgres as everything else.

`AGENT_DB=sqlite` restores the old local file (`tmp/educa_agent.db`) -- useful
for a laptop without Postgres, or to read history recorded before the move.
One instance is shared so all agents use a single connection pool.
"""
import os
from functools import cache

from agno.db.postgres import PostgresDb
from agno.db.sqlite import SqliteDb

SQLITE_FILE = "tmp/educa_agent.db"


@cache
def build_agent_db():
    if os.environ.get("AGENT_DB", "postgres").lower() == "sqlite":
        return SqliteDb(db_file=SQLITE_FILE)
    return PostgresDb(db_url=os.environ["DATABASE_URL"])
