"""Teacher routes (author/approve/render a module's story) and student routes
(list and play the ready ones)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from redis.exceptions import RedisError

from app import usage
from app.agents.structured import StructuredRunError
from app.auth.context import require_role

from . import service
from .schemas import ScriptRequest, ScriptUpdate

router = APIRouter(prefix="/api", tags=["module-video"])


def _handle(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except PermissionError as error:
        raise HTTPException(403, str(error)) from error
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    except usage.UsageLimitExceeded as error:
        raise HTTPException(429, "You've reached today's story-writing limit. Try again tomorrow.") from error
    except (StructuredRunError, RedisError) as error:
        raise HTTPException(503, "That's temporarily unavailable. Try again in a moment.") from error


# ---- teacher ---------------------------------------------------------------------

_MODULE = "/modules/{module_id}/story-video"


@router.get(_MODULE)
def get_video(module_id: str, user: dict = Depends(require_role("teacher"))):
    return _handle(service.get_video, module_id, user["id"])


@router.post(_MODULE + "/script")
def generate_script(module_id: str, body: ScriptRequest, user: dict = Depends(require_role("teacher"))):
    return _handle(service.generate_script, module_id, user["id"], body)


@router.put(_MODULE + "/script")
def update_script(module_id: str, body: ScriptUpdate, user: dict = Depends(require_role("teacher"))):
    return _handle(service.update_script, module_id, user["id"], body.script)


@router.post(_MODULE + "/approve")
def approve(module_id: str, user: dict = Depends(require_role("teacher"))):
    return _handle(service.approve_script, module_id, user["id"])


@router.post(_MODULE + "/render")
def render(module_id: str, user: dict = Depends(require_role("teacher"))):
    return _handle(service.start_render, module_id, user["id"])


@router.delete(_MODULE)
def delete(module_id: str, user: dict = Depends(require_role("teacher"))):
    if not _handle(service.delete_video, module_id, user["id"]):
        raise HTTPException(404, "This module has no story video")
    return {"ok": True}


# ---- student ---------------------------------------------------------------------


@router.get("/courses/{course_id}/story-videos")
def list_ready(course_id: str, user: dict = Depends(require_role("student"))):
    return _handle(service.list_ready_for_course, course_id, user["id"])


@router.get("/courses/{course_id}/modules/{module_id}/story-video")
def watch(course_id: str, module_id: str, user: dict = Depends(require_role("student"))):
    return _handle(service.get_ready_for_student, course_id, module_id, user["id"])


@router.get("/courses/{course_id}/modules/{module_id}/story-video/file")
def watch_file(course_id: str, module_id: str, user: dict = Depends(require_role("student"))):
    content, content_type = _handle(service.get_video_file, course_id, module_id, user["id"])
    return Response(content=content, media_type=content_type)
