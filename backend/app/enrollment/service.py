"""Student-side of the Course aggregate: browsing the catalog, enrolling,
viewing a published lesson, and quiz attempts. Reads `Course`/`Lesson` rows
that courses/service.py owns authoring of (via its exported `COURSE_LOAD`,
`find_lesson_row`, `current_quiz_item`) but serializes them into a
deliberately different, narrower shape -- see `_serialize_course_preview`.
"""
from sqlalchemy import select

from ..courses.service import COURSE_LOAD, current_quiz_item, find_lesson_row
from ..db.models import Course, Enrollment, QuizAttempt, QuizItem, Response
from ..db.session import SessionLocal


def _serialize_course_preview(course: Course) -> dict:
    """Public/enrolled-student shape: published lessons only, title +
    objective as a table of contents -- no slides, speaker notes, or quiz
    content, so no `correctIndex` leak. Used for the catalog (any
    authenticated user, enrolled or not) and a student's own enrolled
    course list; a single published lesson's real content is only ever
    served one at a time via `get_published_lesson_for_student`, which
    also withholds the correct answer until a quiz is submitted."""
    return {
        "id": course.id,
        "teacherId": course.teacher_id,
        "title": course.title,
        "audience": course.audience,
        "weeks": [
            {
                "week": m.week_number,
                "title": m.title,
                "lessons": [
                    {"id": l.id, "title": l.title, "objective": l.objective} for l in m.lessons if l.published
                ],
            }
            for m in course.modules
        ],
    }


def list_published_courses() -> list[dict]:
    """A course counts as published once it has at least one published
    lesson -- Educa has no separate course-level publish action."""
    with SessionLocal() as session:
        courses = session.scalars(select(Course).options(COURSE_LOAD)).all()
        return [
            _serialize_course_preview(c)
            for c in courses
            if any(l.published for m in c.modules for l in m.lessons)
        ]


def enroll_student(course_id: str, student_id: str) -> dict:
    with SessionLocal() as session:
        existing = session.scalar(
            select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == student_id)
        )
        if existing:
            return {"id": existing.id, "courseId": existing.course_id, "status": existing.status}
        enrollment = Enrollment(course_id=course_id, student_id=student_id, status="active")
        session.add(enrollment)
        session.commit()
        return {"id": enrollment.id, "courseId": enrollment.course_id, "status": enrollment.status}


def is_enrolled(course_id: str, student_id: str) -> bool:
    with SessionLocal() as session:
        return (
            session.scalar(
                select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.student_id == student_id)
            )
            is not None
        )


def list_enrolled_courses(student_id: str) -> list[dict]:
    with SessionLocal() as session:
        course_ids = session.scalars(
            select(Enrollment.course_id).where(Enrollment.student_id == student_id)
        ).all()
        if not course_ids:
            return []
        courses = session.scalars(select(Course).where(Course.id.in_(course_ids)).options(COURSE_LOAD)).all()
        return [_serialize_course_preview(c) for c in courses]


def get_published_lesson_for_student(course_id: str, lesson_id: str, student_id: str) -> dict | None:
    """404-shaped `None` unless the lesson is published AND the student is
    enrolled -- never exposes `correctIndex`, unlike the teacher-facing
    shape in courses/service.py."""
    if not is_enrolled(course_id, student_id):
        return None
    with SessionLocal() as session:
        lesson = find_lesson_row(session, lesson_id)
        if not lesson or not lesson.published or lesson.module.course_id != course_id:
            return None
        item = current_quiz_item(lesson)
        return {
            "id": lesson.id,
            "title": lesson.title,
            "objective": lesson.objective,
            "slides": lesson.slides or [],
            "speakerNotes": lesson.speaker_notes or "",
            "quiz": {"quizItemId": item.id, "question": item.prompt, "options": item.options} if item else None,
        }


def record_quiz_attempt(lesson_id: str, student_id: str, quiz_item_id: str, selected_index: int) -> dict:
    """Scores once, at submission, against the lesson's *current* quiz
    item -- the resulting `QuizAttempt`/`Response` rows are never edited
    afterwards, per the entity diagram's assessment fix."""
    with SessionLocal() as session:
        item = session.get(QuizItem, quiz_item_id)
        if not item or item.quiz.lesson_id != lesson_id:
            raise ValueError("Quiz item does not belong to this lesson")
        is_correct = selected_index == item.correct_answer
        attempt = QuizAttempt(quiz_id=item.quiz_id, student_id=student_id, score=1 if is_correct else 0, max_score=1)
        attempt.responses.append(Response(item_id=item.id, value=selected_index, is_correct=is_correct))
        session.add(attempt)
        session.commit()
        return {
            "id": attempt.id,
            "score": attempt.score,
            "maxScore": attempt.max_score,
            "correct": is_correct,
            "correctIndex": item.correct_answer,
            "submittedAt": attempt.submitted_at.isoformat(),
        }


def list_attempts_for_student(lesson_id: str, student_id: str) -> list[dict]:
    with SessionLocal() as session:
        lesson = find_lesson_row(session, lesson_id)
        if not lesson:
            return []
        quiz_ids = [q.id for q in lesson.quizzes]
        if not quiz_ids:
            return []
        attempts = session.scalars(
            select(QuizAttempt)
            .where(QuizAttempt.quiz_id.in_(quiz_ids), QuizAttempt.student_id == student_id)
            .order_by(QuizAttempt.submitted_at)
        ).all()
        return [
            {"id": a.id, "score": a.score, "maxScore": a.max_score, "submittedAt": a.submitted_at.isoformat()}
            for a in attempts
        ]
