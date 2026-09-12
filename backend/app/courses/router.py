"""Teacher-side course-authoring routes: direct reads/edits + the publish
gate. The actual syllabus/slide/quiz *content* is mostly written by the AI
agent team (see agents/team.py), not these routes -- see
docs/api-contracts/README.md section 02.
"""
from fastapi import APIRouter, Depends, HTTPException

from ..auth.context import require_role
from . import service
from .schemas import ApprovalUpdate, LessonEdit

router = APIRouter(prefix="/api", tags=["courses"])


def _course_or_404(course_id: str) -> dict:
    course = service.get_course(course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    return course


def _owned_or_403(course: dict, user: dict) -> dict:
    if course["teacherId"] != user["id"]:
        raise HTTPException(403, "You don't own this course")
    return course


@router.get("/courses/mine")
def list_my_courses(user: dict = Depends(require_role("teacher"))):
    return service.list_courses_for_teacher(user["id"])


@router.get("/courses/{course_id}")
def get_my_course(course_id: str, user: dict = Depends(require_role("teacher"))):
    return _owned_or_403(_course_or_404(course_id), user)


@router.patch("/lessons/{lesson_id}")
def edit_lesson(lesson_id: str, body: LessonEdit, user: dict = Depends(require_role("teacher"))):
    try:
        lesson = service.edit_lesson(lesson_id, user["id"], body.title, body.objective)
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    return lesson


@router.patch("/lessons/{lesson_id}/approval")
def set_approval(lesson_id: str, body: ApprovalUpdate, user: dict = Depends(require_role("teacher"))):
    try:
        lesson = service.set_approved(lesson_id, user["id"], body.approved)
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    return lesson


@router.post("/lessons/{lesson_id}/publish")
def publish(lesson_id: str, user: dict = Depends(require_role("teacher"))):
    try:
        lesson = service.publish_lesson(lesson_id, user["id"])
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    if not lesson:
        raise HTTPException(400, "Lesson must be approved and have generated content before publishing")
    return lesson


@router.post("/reset")
def reset(user: dict = Depends(require_role("teacher"))):
    # Scoped to the calling teacher's own courses -- a global wipe isn't
    # safe once the database holds more than one person's real data.
    service.reset_teacher_courses(user["id"])
    return {"ok": True}
