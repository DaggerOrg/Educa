"""Student-facing routes: browse the catalog, self-enrol, view a published
lesson, and take/review its quiz. See docs/api-contracts/README.md section
05 for the Moodle Web Service function each of these parallels."""
from fastapi import APIRouter, Depends, HTTPException

from ..auth.context import require_role, set_current_user
from ..courses import service as courses_service
from . import service
from .schemas import QuizAttemptSubmit

router = APIRouter(prefix="/api", tags=["enrollment"])


@router.get("/courses")
def catalog(user: dict = Depends(set_current_user)):
    # Published courses only -- Moodle's self-enrol method, the simplest of
    # its four enrollment methods, matching this app's no-admin-console scope.
    return service.list_published_courses()


@router.get("/students/me/courses")
def my_enrolled_courses(user: dict = Depends(require_role("student"))):
    return service.list_enrolled_courses(user["id"])


@router.post("/courses/{course_id}/enroll")
def enroll(course_id: str, user: dict = Depends(require_role("student"))):
    if not courses_service.get_course(course_id):
        raise HTTPException(404, "Course not found")
    return service.enroll_student(course_id, user["id"])


@router.get("/courses/{course_id}/lessons/{lesson_id}")
def student_lesson(course_id: str, lesson_id: str, user: dict = Depends(require_role("student"))):
    lesson = service.get_published_lesson_for_student(course_id, lesson_id, user["id"])
    if not lesson:
        raise HTTPException(404, "Lesson not found, not published yet, or you're not enrolled in this course")
    return lesson


@router.post("/lessons/{lesson_id}/quiz/attempts")
def submit_quiz_attempt(lesson_id: str, body: QuizAttemptSubmit, user: dict = Depends(require_role("student"))):
    try:
        return service.record_quiz_attempt(lesson_id, user["id"], body.quizItemId, body.selectedIndex)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/lessons/{lesson_id}/quiz/attempts/me")
def my_quiz_attempts(lesson_id: str, user: dict = Depends(require_role("student"))):
    return service.list_attempts_for_student(lesson_id, user["id"])
