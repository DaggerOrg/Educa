"""Teacher-side script/approve/render flow and student-side playback lookup
for module story videos.

Errors: LookupError -> 404, PermissionError -> 403, ValueError -> 400,
`usage.UsageLimitExceeded` -> 429, `StructuredRunError` -> 503 (the router
maps them).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app import persona, store, usage
from app.agents.models import build_model
from app.agents.structured import run_structured
from app.db.session import SessionLocal
from app.models_db import Course, Module
from curriculum_ai.jobs.queue import get_queue
from curriculum_ai.logging_config import get_logger
from curriculum_ai.storage import get_storage

from .models import ModuleVideo, VideoStatus
from .renderers import configured_provider
from .render import render_module_video
from .schemas import ScriptRequest, StoryScript
from .story_agent import STORY_INSTRUCTIONS, build_story_prompt

logger = get_logger(__name__)

USAGE_AGENT = "module_story"
DEFAULT_DAILY_TOKEN_CAP = 200_000  # per teacher per UTC day; STORY_DAILY_TOKEN_CAP=0 disables
MAX_SCENES = 8
RENDER_TIMEOUT_SECONDS = 1800  # real providers can take a while; the mock takes milliseconds


# ---- helpers ---------------------------------------------------------------------


def _load_module(session, module_id: str) -> dict:
    module = session.scalar(select(Module).where(Module.id == module_id).options(selectinload(Module.lessons)))
    if module is None:
        raise LookupError(f"Module '{module_id}' not found")
    course = session.get(Course, module.course_id)
    return {
        "id": module.id,
        "course_id": module.course_id,
        "teacher_id": course.teacher_id if course else None,
        "title": module.title,
        "week": module.week_number,
        "lessons": [
            {"title": l.title, "objective": l.objective, "slides": l.slides or []} for l in module.lessons
        ],
    }


def _owned_module(session, module_id: str, teacher_id: str) -> dict:
    module = _load_module(session, module_id)
    if module["teacher_id"] != teacher_id:
        raise PermissionError("You don't own this course")
    return module


def normalize_script(script: StoryScript) -> dict:
    """Trim and clamp a script (from the agent or from a teacher edit) to
    limits the schema itself can't carry; reject one with nothing to say."""
    scenes = []
    for scene in script.scenes[:MAX_SCENES]:
        narration = scene.narration.strip()
        if not narration:
            continue
        scenes.append(
            {
                "narration": narration[:600],
                "on_screen_text": scene.on_screen_text.strip()[:80],
                "visual": scene.visual.strip()[:400],
                "seconds": min(max(int(scene.seconds or 8), 3), 30),
            }
        )
    if not scenes:
        raise ValueError("The script needs at least one scene with narration")
    return {
        "title": script.title.strip()[:120] or "Module story",
        "hook": script.hook.strip()[:200],
        "scenes": scenes,
        "takeaway": script.takeaway.strip()[:300],
    }


def _serialize(video: ModuleVideo | None) -> dict | None:
    if video is None:
        return None
    return {
        "id": video.id,
        "moduleId": video.module_id,
        "status": video.status,
        "style": video.style,
        "script": video.script,
        "provider": video.provider,
        "kind": (video.result or {}).get("kind"),
        "error": video.error,
        "updatedAt": video.updated_at.isoformat(),
    }


def _delete_stored(result: dict | None) -> None:
    key = (result or {}).get("storage_key")
    if not key:
        return
    try:
        get_storage().delete(key)
    except Exception:  # noqa: BLE001 - the row is already updated; log and move on
        logger.exception("Could not delete stored story video %s", key)


def _get_row(session, module_id: str) -> ModuleVideo | None:
    return session.scalar(select(ModuleVideo).where(ModuleVideo.module_id == module_id))


# ---- teacher ---------------------------------------------------------------------


def get_video(module_id: str, teacher_id: str) -> dict | None:
    with SessionLocal() as session:
        _owned_module(session, module_id, teacher_id)
        return _serialize(_get_row(session, module_id))


def generate_script(module_id: str, teacher_id: str, request: ScriptRequest) -> dict:
    with SessionLocal() as session:
        module = _owned_module(session, module_id, teacher_id)
    if not module["lessons"]:
        raise ValueError("Add at least one lesson to this module before writing its story")
    usage.check_daily_cap(teacher_id, USAGE_AGENT, usage.daily_cap("STORY_DAILY_TOKEN_CAP", DEFAULT_DAILY_TOKEN_CAP))

    script = normalize_script(
        run_structured(
            agent_name=USAGE_AGENT,
            user_id=teacher_id,
            instructions=STORY_INSTRUCTIONS,
            prompt=build_story_prompt(module["title"], module["week"], module["lessons"], request.style),
            output=StoryScript,
        )
    )
    return _write_draft(module, teacher_id, script, request.style.strip(), model_id=getattr(build_model(), "id", None))


def update_script(module_id: str, teacher_id: str, script: StoryScript) -> dict:
    with SessionLocal() as session:
        module = _owned_module(session, module_id, teacher_id)
        existing = _get_row(session, module_id)
    return _write_draft(
        module, teacher_id, normalize_script(script), existing.style if existing else "",
        model_id=existing.model_id if existing else None,
    )


def _write_draft(module: dict, teacher_id: str, script: dict, style: str, *, model_id: str | None) -> dict:
    """Store `script` as the module's draft. Clearing `job_id` fences off any
    render already in flight for the old script."""
    with SessionLocal() as session:
        video = _get_row(session, module["id"])
        old_result = video.result if video else None
        if video is None:
            video = ModuleVideo(module_id=module["id"], course_id=module["course_id"], teacher_id=teacher_id)
            session.add(video)
        video.status = VideoStatus.DRAFT.value
        video.script = script
        video.style = style
        video.model_id = model_id
        video.job_id = None
        video.result = None
        video.error = None
        session.commit()
        session.refresh(video)
        out = _serialize(video)
    _delete_stored(old_result)
    return out


def approve_script(module_id: str, teacher_id: str) -> dict:
    with SessionLocal() as session:
        _owned_module(session, module_id, teacher_id)
        video = _get_row(session, module_id)
        if video is None or not video.script:
            raise ValueError("There's no script to approve yet")
        if video.status != VideoStatus.DRAFT.value:
            raise ValueError(f"Only a draft script can be approved (current status: {video.status})")
        video.status = VideoStatus.APPROVED.value
        session.commit()
        session.refresh(video)
        return _serialize(video)


def start_render(module_id: str, teacher_id: str) -> dict:
    provider = configured_provider()
    with SessionLocal() as session:
        _owned_module(session, module_id, teacher_id)
        video = _get_row(session, module_id)
        if video is None or not video.script:
            raise ValueError("There's no script to render yet")
        if video.status in (VideoStatus.QUEUED.value, VideoStatus.RENDERING.value):
            raise ValueError("This story is already rendering")
        if video.status == VideoStatus.DRAFT.value:
            raise ValueError("Approve the script before rendering")
        job_id = uuid.uuid4().hex
        video.status = VideoStatus.QUEUED.value
        video.job_id = job_id
        video.provider = provider
        video.error = None
        session.commit()
        video_id = video.id

    try:
        get_queue().enqueue(render_module_video, video_id, job_id, job_id=job_id, job_timeout=RENDER_TIMEOUT_SECONDS)
    except Exception:
        logger.exception("Could not enqueue story render: video=%s", video_id)
        with SessionLocal() as session:
            session.execute(
                update(ModuleVideo)
                .where(ModuleVideo.id == video_id, ModuleVideo.job_id == job_id)
                .values(status=VideoStatus.FAILED.value, error="Could not queue the render (job queue unavailable).")
            )
            session.commit()
        raise
    with SessionLocal() as session:
        return _serialize(_get_row(session, module_id))


def delete_video(module_id: str, teacher_id: str) -> bool:
    with SessionLocal() as session:
        _owned_module(session, module_id, teacher_id)
        video = _get_row(session, module_id)
        if video is None:
            return False
        result = video.result
        session.delete(video)
        session.commit()
    _delete_stored(result)
    return True


# ---- student ---------------------------------------------------------------------


def _narrator(course_id: str) -> dict:
    found = persona.get_persona_for_course(course_id)
    return {"name": found["name"] if found else None}


def _assert_enrolled(course_id: str, student_id: str) -> None:
    if not store.is_enrolled(course_id, student_id):
        raise PermissionError("You're not enrolled in this course")


def list_ready_for_course(course_id: str, student_id: str) -> list[dict]:
    _assert_enrolled(course_id, student_id)
    with SessionLocal() as session:
        rows = session.execute(
            select(ModuleVideo, Module)
            .join(Module, Module.id == ModuleVideo.module_id)
            .where(ModuleVideo.course_id == course_id, ModuleVideo.status == VideoStatus.READY.value)
            .order_by(Module.week_number)
        ).all()
        return [
            {"moduleId": m.id, "week": m.week_number, "title": m.title, "kind": (v.result or {}).get("kind")}
            for v, m in rows
        ]


def _ready_video_for_student(session, course_id: str, module_id: str, student_id: str) -> ModuleVideo:
    _assert_enrolled(course_id, student_id)
    video = _get_row(session, module_id)
    if video is None or video.course_id != course_id or video.status != VideoStatus.READY.value:
        raise LookupError("No story video is available for this module yet")
    return video


def get_ready_for_student(course_id: str, module_id: str, student_id: str) -> dict:
    with SessionLocal() as session:
        video = _ready_video_for_student(session, course_id, module_id, student_id)
        module = session.get(Module, module_id)
        return {
            "moduleId": module_id,
            "week": module.week_number if module else None,
            "title": module.title if module else "",
            "kind": (video.result or {}).get("kind"),
            "script": video.script,
            "narrator": _narrator(course_id),
        }


def get_video_file(course_id: str, module_id: str, student_id: str) -> tuple[bytes, str]:
    with SessionLocal() as session:
        video = _ready_video_for_student(session, course_id, module_id, student_id)
        result = video.result or {}
    if result.get("kind") != "video" or not result.get("storage_key"):
        raise LookupError("This story has no video file (it plays as a storyboard)")
    return get_storage().get(result["storage_key"]), result.get("content_type") or "video/mp4"
