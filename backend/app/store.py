"""Course/lesson/enrollment/quiz persistence, backed by Postgres via
SQLAlchemy (see db.py, models_db.py) -- replaces the earlier single
in-memory `_course` dict, which couldn't hold more than one course or
survive a restart. Every course now belongs to a teacher (`teacher_id`);
callers that mutate a course pass the acting teacher's id and get a
`PermissionError` back if they don't own it -- see auth/context.py for
where that id comes from when the caller is an agent tool rather than a
plain REST route.
"""
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .db import SessionLocal
from .models_db import Course, Enrollment, Lesson, LessonExercise, Module, Quiz, QuizAttempt, QuizItem, Response

_COURSE_LOAD = selectinload(Course.modules).selectinload(Module.lessons).options(
    selectinload(Lesson.quizzes).selectinload(Quiz.items),
    selectinload(Lesson.exercises),
)


def _current_quiz_item(lesson: Lesson) -> QuizItem | None:
    if not lesson.quizzes:
        return None
    latest = max(lesson.quizzes, key=lambda q: q.version)
    return latest.items[0] if latest.items else None


def _serialize_lesson(lesson: Lesson) -> dict:
    item = _current_quiz_item(lesson)
    content = None
    if lesson.slides is not None or item is not None:
        content = {
            "slides": lesson.slides or [],
            "speakerNotes": lesson.speaker_notes or "",
            "quiz": {"question": item.prompt, "options": item.options, "correctIndex": item.correct_answer}
            if item
            else None,
        }
    return {
        "id": lesson.id,
        "title": lesson.title,
        "objective": lesson.objective,
        "content": content,
        "approved": lesson.approved,
        "published": lesson.published,
    }


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


def _serialize_course(course: Course) -> dict:
    return {
        "id": course.id,
        "teacherId": course.teacher_id,
        "title": course.title,
        "audience": course.audience,
        "weeks": [
            {
                "week": m.week_number,
                "title": m.title,
                "lessons": [_serialize_lesson(l) for l in m.lessons],
            }
            for m in course.modules
        ],
    }


def _get_course(session, course_id: str) -> Course | None:
    return session.scalar(select(Course).where(Course.id == course_id).options(_COURSE_LOAD))


def _find_lesson_row(session, lesson_id: str) -> Lesson | None:
    return session.scalar(
        select(Lesson).where(Lesson.id == lesson_id).options(selectinload(Lesson.quizzes).selectinload(Quiz.items))
    )


def _check_owner(course: Course, teacher_id: str) -> None:
    if course.teacher_id != teacher_id:
        raise PermissionError("You don't own this course")


# ---- Teacher-side: course/syllabus authoring -------------------------------


def create_course(teacher_id: str, title: str, audience: str, weeks: list[dict]) -> dict:
    with SessionLocal() as session:
        course = Course(teacher_id=teacher_id, title=title, audience=audience)
        for w in weeks:
            module = Module(week_number=w.get("week"), title=w["title"])
            for l in w.get("lessons", []):
                module.lessons.append(Lesson(title=l["title"], objective=l.get("objective", "")))
            course.modules.append(module)
        session.add(course)
        session.commit()
        return _serialize_course(_get_course(session, course.id))


def get_course(course_id: str) -> dict | None:
    with SessionLocal() as session:
        course = _get_course(session, course_id)
        return _serialize_course(course) if course else None


def list_courses_for_teacher(teacher_id: str) -> list[dict]:
    with SessionLocal() as session:
        courses = session.scalars(
            select(Course).where(Course.teacher_id == teacher_id).options(_COURSE_LOAD).order_by(Course.created_at)
        ).all()
        return [_serialize_course(c) for c in courses]


def find_lesson(lesson_id: str) -> dict | None:
    with SessionLocal() as session:
        lesson = _find_lesson_row(session, lesson_id)
        return _serialize_lesson(lesson) if lesson else None


def update_syllabus(course_id: str, teacher_id: str, title: str | None, audience: str | None, weeks: list[dict]) -> dict:
    """Replace the syllabus, preserving existing lesson state (content,
    approval, publish status) *and identity* for any lesson whose title is
    unchanged -- this is what makes a manually-edited lesson survive a
    refinement prompt (SRS FR-1.4, ARCH-01 SS03). A matched lesson keeps
    its row (and id); everything else is rebuilt."""
    with SessionLocal() as session:
        course = _get_course(session, course_id)
        if not course:
            raise ValueError(f"No course with id {course_id}")
        _check_owner(course, teacher_id)

        old_by_title = {
            l.title.strip().lower(): l for m in course.modules for l in m.lessons
        }
        old_modules = list(course.modules)

        new_modules = []
        for w in weeks:
            module = Module(course_id=course.id, week_number=w.get("week"), title=w["title"])
            session.add(module)
            for l in w.get("lessons", []):
                match = old_by_title.get(l["title"].strip().lower())
                if match:
                    match.title = l["title"]
                    match.objective = l.get("objective", match.objective)
                    match.module = module
                else:
                    module.lessons.append(Lesson(title=l["title"], objective=l.get("objective", "")))
            new_modules.append(module)

        for m in old_modules:
            session.delete(m)  # cascades only to lessons still parented here (the unmatched ones)

        course.modules = new_modules
        if title:
            course.title = title
        if audience:
            course.audience = audience
        session.commit()
        return _serialize_course(_get_course(session, course.id))


def edit_lesson(lesson_id: str, teacher_id: str, title: str | None, objective: str | None) -> dict | None:
    with SessionLocal() as session:
        lesson = _find_lesson_row(session, lesson_id)
        if not lesson:
            return None
        _check_owner(lesson.module.course, teacher_id)
        if title is not None:
            lesson.title = title
        if objective is not None:
            lesson.objective = objective
        session.commit()
        return _serialize_lesson(lesson)


def set_lesson_slides(lesson_id: str, teacher_id: str, slides: list[dict], speaker_notes: str) -> dict | None:
    with SessionLocal() as session:
        lesson = _find_lesson_row(session, lesson_id)
        if not lesson:
            return None
        _check_owner(lesson.module.course, teacher_id)
        lesson.slides = slides
        lesson.speaker_notes = speaker_notes
        session.commit()
        return _serialize_lesson(lesson)


def set_lesson_quiz(lesson_id: str, teacher_id: str, question: str, options: list[str], correct_index: int) -> dict | None:
    """Creates a new, immutable `Quiz` version rather than editing one --
    see models_db.py's `Quiz` docstring."""
    with SessionLocal() as session:
        lesson = _find_lesson_row(session, lesson_id)
        if not lesson:
            return None
        _check_owner(lesson.module.course, teacher_id)
        next_version = max((q.version for q in lesson.quizzes), default=0) + 1
        quiz = Quiz(lesson_id=lesson.id, version=next_version)
        quiz.items.append(QuizItem(kind="multiple_choice", prompt=question, options=options, correct_answer=correct_index))
        session.add(quiz)
        session.commit()
        return _serialize_lesson(_find_lesson_row(session, lesson_id))


def set_approved(lesson_id: str, teacher_id: str, approved: bool) -> dict | None:
    with SessionLocal() as session:
        lesson = _find_lesson_row(session, lesson_id)
        if not lesson:
            return None
        _check_owner(lesson.module.course, teacher_id)
        if lesson.published and not approved:
            return _serialize_lesson(lesson)
        lesson.approved = approved
        session.commit()
        return _serialize_lesson(lesson)


def publish_lesson(lesson_id: str, teacher_id: str) -> dict | None:
    with SessionLocal() as session:
        lesson = _find_lesson_row(session, lesson_id)
        if not lesson:
            return None
        _check_owner(lesson.module.course, teacher_id)
        if not lesson.approved or lesson.slides is None or _current_quiz_item(lesson) is None:
            return None
        lesson.published = True
        session.commit()
        return _serialize_lesson(lesson)


def reset_teacher_courses(teacher_id: str) -> None:
    with SessionLocal() as session:
        for course in session.scalars(select(Course).where(Course.teacher_id == teacher_id)):
            session.delete(course)
        session.commit()


# ---- Student-side: catalog, enrollment, lesson viewing, quiz attempts -----


def list_published_courses() -> list[dict]:
    """A course counts as published once it has at least one published
    lesson -- Educa has no separate course-level publish action."""
    with SessionLocal() as session:
        courses = session.scalars(select(Course).options(_COURSE_LOAD)).all()
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
        courses = session.scalars(select(Course).where(Course.id.in_(course_ids)).options(_COURSE_LOAD)).all()
        return [_serialize_course_preview(c) for c in courses]


def get_published_lesson_for_student(course_id: str, lesson_id: str, student_id: str) -> dict | None:
    """404-shaped `None` unless the lesson is published AND the student is
    enrolled -- never exposes `correctIndex`, unlike the teacher-facing
    `_serialize_lesson` used everywhere above."""
    if not is_enrolled(course_id, student_id):
        return None
    with SessionLocal() as session:
        lesson = _find_lesson_row(session, lesson_id)
        if not lesson or not lesson.published or lesson.module.course_id != course_id:
            return None
        item = _current_quiz_item(lesson)
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
        lesson = _find_lesson_row(session, lesson_id)
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
