"""Shared fixtures for the student_ai / module_video integration tests:
a real teacher, two real students, and a real published course, all created
through the app's own store/auth functions against the local Postgres, and
deleted again afterwards."""

import os
import sys
import uuid
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://educa:educa@localhost:55432/educa")
sys.path.insert(0, str(Path(__file__).parents[2]))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402

from app import store  # noqa: E402
from app.auth import security  # noqa: E402
from app.auth import store as auth_store  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models_db import AgentUsage, Course, Module, User  # noqa: E402


def _make_user(role: str) -> dict:
    email = f"{role}-{uuid.uuid4().hex}@example.com"
    user = auth_store.create_user(email, f"Test {role}", security.hash_password("testpass123"), role)
    return {"id": user["id"], "headers": {"Authorization": f"Bearer {security.create_access_token(user['id'])}"}}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def world():
    teacher, student, other_student, other_teacher = (
        _make_user("teacher"), _make_user("student"), _make_user("student"), _make_user("teacher"),
    )
    course = store.create_course(
        teacher["id"],
        "Present Tense",
        "Beginners",
        [
            {
                "week": 1,
                "title": "Everyday routines",
                "lessons": [
                    {"title": "Simple present", "objective": "Use the simple present for habits"},
                    {"title": "Unpublished draft", "objective": "Not ready"},
                ],
            }
        ],
    )
    module = course["weeks"][0]
    lesson = module["lessons"][0]
    draft_lesson = module["lessons"][1]
    store.set_lesson_slides(
        lesson["id"],
        teacher["id"],
        [{"heading": "Habits", "bullets": ["We add -s for he/she/it", "Use it for routines"]}],
        "Remind students about third person singular.",
    )
    store.set_lesson_quiz(lesson["id"], teacher["id"], "SECRETQUIZQUESTION?", ["ALPHAOPTION", "BETAOPTION"], 1)
    store.set_approved(lesson["id"], teacher["id"], True)
    store.publish_lesson(lesson["id"], teacher["id"])
    store.enroll_student(course["id"], student["id"])

    with SessionLocal() as session:
        module_id = session.scalar(select(Module.id).where(Module.course_id == course["id"]))

    yield {
        "teacher": teacher,
        "other_teacher": other_teacher,
        "student": student,
        "other_student": other_student,
        "course_id": course["id"],
        "module_id": module_id,
        "lesson_id": lesson["id"],
        "draft_lesson_id": draft_lesson["id"],
    }

    user_ids = [teacher["id"], student["id"], other_student["id"], other_teacher["id"]]
    with SessionLocal() as session:
        course_row = session.get(Course, course["id"])
        if course_row is not None:
            session.delete(course_row)
            session.commit()
        session.execute(delete(AgentUsage).where(AgentUsage.user_id.in_(user_ids)))
        session.execute(delete(User).where(User.id.in_(user_ids)))
        session.commit()
