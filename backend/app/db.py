"""SQLAlchemy engine/session for Educa's own relational tables (users,
courses, enrollments, quizzes/attempts -- see models_db.py).

Separate from `knowledge.py`'s `PgVector` wiring but the same Postgres
instance/`DATABASE_URL` (`docker-compose.yml` has one Postgres, many
tables) -- `PgVector` manages its own `course_materials` table directly,
this module manages everything else via a plain declarative ORM.

No Alembic: this prototype has never had migration tooling (knowledge.py's
`vector_db.create()` is the same "create what's missing at startup" spirit).
`init_db()` runs once from `main.py` at import time.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

engine = create_engine(os.environ["DATABASE_URL"])
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from . import models_db  # noqa: F401  (registers tables on Base.metadata)

    Base.metadata.create_all(engine)
