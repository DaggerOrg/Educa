"""Course/module/lesson persistence -- the teacher-authoring side of the
Course aggregate. Backed by Postgres via SQLAlchemy (see db/session.py,
db/models.py). Every mutation here is scoped to the acting teacher
(`teacher_id`); callers get a `PermissionError` back if they don't own the
course -- see auth/context.py for where that id comes from when the caller
is an agent tool rather than a plain REST route.

`COURSE_LOAD`, `get_course_row`, `find_lesson_row`, `check_owner`, and
`current_quiz_item` are exported (not underscore-prefixed) because
enrollment/service.py and marketplace/service.py also need to read the
same Course/Lesson/Quiz rows -- Course is one aggregate, authored here,
but legitimately read across domains (a student enrolling, a teacher
listing it for sale). Everything else in this module is this domain's own:
the full, teacher-facing shape (draft lessons, quiz answer keys included).
"""
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..db.models import Course, Lesson, Module, Quiz, QuizItem
from ..db.session import SessionLocal

COURSE_LOAD = selectinload(Course.modules).selectinload(Module.lessons).selectinload(Lesson.quizzes).selectinload(
    Quiz.items
)


def current_quiz_item(lesson: Lesson) -> QuizItem | None:
    if not lesson.quizzes:
        return None
    latest = max(lesson.quizzes, key=lambda q: q.version)
    return latest.items[0] if latest.items else None


def _serialize_lesson(lesson: Lesson) -> dict:
    item = current_quiz_item(lesson)
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


def get_course_row(session, course_id: str) -> Course | None:
    return session.scalar(select(Course).where(Course.id == course_id).options(COURSE_LOAD))


def find_lesson_row(session, lesson_id: str) -> Lesson | None:
    return session.scalar(
        select(Lesson).where(Lesson.id == lesson_id).options(selectinload(Lesson.quizzes).selectinload(Quiz.items))
    )


def check_owner(course: Course, teacher_id: str) -> None:
    if course.teacher_id != teacher_id:
        raise PermissionError("You don't own this course")


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
        return _serialize_course(get_course_row(session, course.id))


def get_course(course_id: str) -> dict | None:
    with SessionLocal() as session:
        course = get_course_row(session, course_id)
        return _serialize_course(course) if course else None


def list_courses_for_teacher(teacher_id: str) -> list[dict]:
    with SessionLocal() as session:
        courses = session.scalars(
            select(Course).where(Course.teacher_id == teacher_id).options(COURSE_LOAD).order_by(Course.created_at)
        ).all()
        return [_serialize_course(c) for c in courses]


def find_lesson(lesson_id: str) -> dict | None:
    with SessionLocal() as session:
        lesson = find_lesson_row(session, lesson_id)
        return _serialize_lesson(lesson) if lesson else None


def update_syllabus(course_id: str, teacher_id: str, title: str | None, audience: str | None, weeks: list[dict]) -> dict:
    """Replace the syllabus, preserving existing lesson state (content,
    approval, publish status) *and identity* for any lesson whose title is
    unchanged -- this is what makes a manually-edited lesson survive a
    refinement prompt (SRS FR-1.4, ARCH-01 SS03). A matched lesson keeps
    its row (and id); everything else is rebuilt."""
    with SessionLocal() as session:
        course = get_course_row(session, course_id)
        if not course:
            raise ValueError(f"No course with id {course_id}")
        check_owner(course, teacher_id)

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
        return _serialize_course(get_course_row(session, course.id))


def edit_lesson(lesson_id: str, teacher_id: str, title: str | None, objective: str | None) -> dict | None:
    with SessionLocal() as session:
        lesson = find_lesson_row(session, lesson_id)
        if not lesson:
            return None
        check_owner(lesson.module.course, teacher_id)
        if title is not None:
            lesson.title = title
        if objective is not None:
            lesson.objective = objective
        session.commit()
        return _serialize_lesson(lesson)


def set_lesson_slides(lesson_id: str, teacher_id: str, slides: list[dict], speaker_notes: str) -> dict | None:
    with SessionLocal() as session:
        lesson = find_lesson_row(session, lesson_id)
        if not lesson:
            return None
        check_owner(lesson.module.course, teacher_id)
        lesson.slides = slides
        lesson.speaker_notes = speaker_notes
        session.commit()
        return _serialize_lesson(lesson)


def set_lesson_quiz(lesson_id: str, teacher_id: str, question: str, options: list[str], correct_index: int) -> dict | None:
    """Creates a new, immutable `Quiz` version rather than editing one --
    see db/models.py's `Quiz` docstring."""
    with SessionLocal() as session:
        lesson = find_lesson_row(session, lesson_id)
        if not lesson:
            return None
        check_owner(lesson.module.course, teacher_id)
        next_version = max((q.version for q in lesson.quizzes), default=0) + 1
        quiz = Quiz(lesson_id=lesson.id, version=next_version)
        quiz.items.append(QuizItem(kind="multiple_choice", prompt=question, options=options, correct_answer=correct_index))
        session.add(quiz)
        session.commit()
        return _serialize_lesson(find_lesson_row(session, lesson_id))


def set_approved(lesson_id: str, teacher_id: str, approved: bool) -> dict | None:
    with SessionLocal() as session:
        lesson = find_lesson_row(session, lesson_id)
        if not lesson:
            return None
        check_owner(lesson.module.course, teacher_id)
        if lesson.published and not approved:
            return _serialize_lesson(lesson)
        lesson.approved = approved
        session.commit()
        return _serialize_lesson(lesson)


def publish_lesson(lesson_id: str, teacher_id: str) -> dict | None:
    with SessionLocal() as session:
        lesson = find_lesson_row(session, lesson_id)
        if not lesson:
            return None
        check_owner(lesson.module.course, teacher_id)
        if not lesson.approved or lesson.slides is None or current_quiz_item(lesson) is None:
            return None
        lesson.published = True
        session.commit()
        return _serialize_lesson(lesson)


def reset_teacher_courses(teacher_id: str) -> None:
    with SessionLocal() as session:
        for course in session.scalars(select(Course).where(Course.teacher_id == teacher_id)):
            session.delete(course)
        session.commit()
