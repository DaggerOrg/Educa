"""Notes storage and the helper-agent calls. Every entry point first
resolves the lesson through `store.get_published_lesson_for_student`, which
already returns nothing unless the lesson is published AND the student is
enrolled -- so access control lives in one existing, tested place.

Errors: LookupError -> 404, ValueError -> 400/413, `usage.UsageLimitExceeded`
-> 429, `StructuredRunError` -> 503 (the router does the mapping).
"""

from __future__ import annotations

import json

from sqlalchemy import select

from app import store, usage
from app.agents.structured import run_structured
from app.db.session import SessionLocal

from .agents import AGENTS, NOTE_WRITER, build_prompt
from .models import StudentNote
from .schemas import (
    Explanation,
    FlashcardSet,
    NoteSuggestion,
    NotesUpdate,
    PracticeQuiz,
    Summary,
)

USAGE_AGENT = "student_ai"
DEFAULT_DAILY_TOKEN_CAP = 300_000  # per student per UTC day; STUDENT_AI_DAILY_TOKEN_CAP=0 disables

MAX_DOC_BYTES = 512_000
MAX_SKETCH_BYTES = 2_000_000
MIN_HEADING_CHARS = 3


class TooLarge(ValueError):
    pass


def _lesson_or_404(course_id: str, lesson_id: str, student_id: str) -> dict:
    lesson = store.get_published_lesson_for_student(course_id, lesson_id, student_id)
    if not lesson:
        raise LookupError("Lesson not found, not published yet, or you're not enrolled in this course")
    return lesson


def _serialize(note: StudentNote | None) -> dict:
    if note is None:
        return {"doc": None, "sketch": None, "updatedAt": None}
    return {"doc": note.doc, "sketch": note.sketch, "updatedAt": note.updated_at.isoformat()}


# ---- notes storage ------------------------------------------------------------


def get_notes(student_id: str, course_id: str, lesson_id: str) -> dict:
    _lesson_or_404(course_id, lesson_id, student_id)
    with SessionLocal() as session:
        note = session.scalar(
            select(StudentNote).where(StudentNote.student_id == student_id, StudentNote.lesson_id == lesson_id)
        )
        return _serialize(note)


def _check_size(value: dict | None, limit: int, label: str) -> None:
    if value is not None and len(json.dumps(value, separators=(",", ":"))) > limit:
        raise TooLarge(f"Your {label} is too large to save (limit {limit // 1000} KB)")


def save_notes(student_id: str, course_id: str, lesson_id: str, update: NotesUpdate) -> dict:
    _lesson_or_404(course_id, lesson_id, student_id)
    fields = update.model_fields_set
    if "doc" in fields:
        _check_size(update.doc, MAX_DOC_BYTES, "notes")
        if update.doc is not None and update.doc.get("type") != "doc":
            raise ValueError("Notes must be a document")
    if "sketch" in fields:
        _check_size(update.sketch, MAX_SKETCH_BYTES, "sketch")

    with SessionLocal() as session:
        note = session.scalar(
            select(StudentNote).where(StudentNote.student_id == student_id, StudentNote.lesson_id == lesson_id)
        )
        if note is None:
            note = StudentNote(student_id=student_id, course_id=course_id, lesson_id=lesson_id)
            session.add(note)
        if "doc" in fields:
            note.doc = update.doc
        if "sketch" in fields:
            note.sketch = update.sketch
        session.commit()
        session.refresh(note)
        return _serialize(note)


# ---- agents ---------------------------------------------------------------------


def _check_cap(student_id: str) -> None:
    usage.check_daily_cap(student_id, USAGE_AGENT, usage.daily_cap("STUDENT_AI_DAILY_TOKEN_CAP", DEFAULT_DAILY_TOKEN_CAP))


def suggest_note(student_id: str, course_id: str, lesson_id: str, heading: str, surrounding: str = "") -> NoteSuggestion:
    lesson = _lesson_or_404(course_id, lesson_id, student_id)
    heading = heading.strip()
    if len(heading) < MIN_HEADING_CHARS:
        raise ValueError("Heading is too short to write notes for")
    _check_cap(student_id)

    suggestion = run_structured(
        agent_name=USAGE_AGENT,
        user_id=student_id,
        instructions=NOTE_WRITER.instructions,
        prompt=build_prompt(lesson, heading=heading, surrounding=surrounding.strip()),
        output=NOTE_WRITER.output,
    )
    # Limits the schema can't express (see schemas.py): keep the card short.
    suggestion.key_points = [p.strip() for p in suggestion.key_points if p.strip()][:6]
    if not suggestion.summary.strip() and not suggestion.key_points:
        raise ValueError("The helper had nothing useful to add for that heading")
    return suggestion


def assist(
    student_id: str, course_id: str, lesson_id: str, agent_key: str, request: str = "", notes: str = ""
) -> Explanation | PracticeQuiz | FlashcardSet | Summary:
    spec = AGENTS.get(agent_key)
    if spec is None:
        raise LookupError(f"Unknown helper '{agent_key}'")
    lesson = _lesson_or_404(course_id, lesson_id, student_id)
    request = request.strip()
    if spec.needs_input and not request:
        raise ValueError(f"{spec.label} needs a question or some selected text")
    _check_cap(student_id)

    answer = run_structured(
        agent_name=USAGE_AGENT,
        user_id=student_id,
        instructions=spec.instructions,
        prompt=build_prompt(lesson, request=request, notes=notes.strip()),
        output=spec.output,
    )
    if isinstance(answer, PracticeQuiz):
        answer.questions = [
            q
            for q in answer.questions[:5]
            if 2 <= len(q.options) <= 5 and 0 <= q.answer_index < len(q.options)
        ]
        if not answer.questions:
            raise ValueError("The helper's questions were malformed; try again")
    elif isinstance(answer, FlashcardSet):
        answer.cards = [c for c in answer.cards[:10] if c.front.strip() and c.back.strip()]
        if not answer.cards:
            raise ValueError("The helper's flashcards were empty; try again")
    return answer
