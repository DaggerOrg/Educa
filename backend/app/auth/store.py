"""User accounts, persisted in Postgres via SQLAlchemy (see ../db.py,
../models_db.py) -- replaces the earlier module-level dict, which didn't
survive a process restart and couldn't support real multi-user data (a
teacher's courses and a student's enrollments/attempts all key off a real,
durable user id).
"""
from sqlalchemy import select

from ..db import SessionLocal
from ..models_db import User


def _to_dict(user: User) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "password_hash": user.password_hash, "role": user.role}


def create_user(email: str, name: str, password_hash: str, role: str) -> dict:
    email = email.strip().lower()
    with SessionLocal() as session:
        if session.scalar(select(User).where(User.email == email)):
            raise ValueError("Email already registered")
        user = User(email=email, name=name, password_hash=password_hash, role=role)
        session.add(user)
        session.commit()
        session.refresh(user)
        return _to_dict(user)


def find_by_email(email: str) -> dict | None:
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email.strip().lower()))
        return _to_dict(user) if user else None


def find_by_id(user_id: str) -> dict | None:
    with SessionLocal() as session:
        user = session.get(User, user_id)
        return _to_dict(user) if user else None
