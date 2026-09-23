"""The render job, run by the same RQ worker as document processing
(`python -m curriculum_ai.jobs.worker`; RQ finds this function by its dotted
path, so no worker change is needed).

Idempotent and fenced like curriculum_ai/processing.py: the row is claimed
with one conditional UPDATE (`status='queued' AND job_id=:job_id`), so a
redelivered or superseded job loses cleanly; every later write is guarded by
`job_id` too, so an edit, re-generate or delete while rendering wins.
"""

from __future__ import annotations

from sqlalchemy import update

from app import persona
from app.db.session import SessionLocal
from curriculum_ai.logging_config import get_logger
from curriculum_ai.storage import get_storage

from .models import ModuleVideo, VideoStatus
from .renderers import RenderRequest, get_renderer

logger = get_logger(__name__)


def _claim(video_id: str, job_id: str) -> ModuleVideo | None:
    with SessionLocal() as session:
        claimed = session.execute(
            update(ModuleVideo)
            .where(
                ModuleVideo.id == video_id,
                ModuleVideo.job_id == job_id,
                ModuleVideo.status == VideoStatus.QUEUED.value,
            )
            .values(status=VideoStatus.RENDERING.value)
        ).rowcount
        session.commit()
        return session.get(ModuleVideo, video_id) if claimed == 1 else None


def _finish(video_id: str, job_id: str, **values) -> bool:
    with SessionLocal() as session:
        done = session.execute(
            update(ModuleVideo)
            .where(
                ModuleVideo.id == video_id,
                ModuleVideo.job_id == job_id,
                ModuleVideo.status == VideoStatus.RENDERING.value,
            )
            .values(**values)
        ).rowcount
        session.commit()
        return done == 1


def render_module_video(video_id: str, job_id: str) -> None:
    video = _claim(video_id, job_id)
    if video is None:
        logger.info("render_module_video(%s, %s): not claimed (done, in progress, or superseded)", video_id, job_id)
        return

    stored_key: str | None = None
    try:
        found = persona.get_persona_for_course(video.course_id)
        rendered = get_renderer(video.provider).render(
            RenderRequest(
                script=video.script or {},
                module_title=(video.script or {}).get("title", ""),
                narrator_name=found["name"] if found else None,
            )
        )
        result: dict = {"kind": rendered.kind}
        if rendered.kind == "video":
            if not rendered.video_bytes:
                raise ValueError("Renderer returned no video data")
            stored_key = f"module-videos/{video.course_id}/{video.id}-{job_id}.mp4"
            content_type = rendered.content_type or "video/mp4"
            get_storage().put(stored_key, rendered.video_bytes, content_type)
            result.update(storage_key=stored_key, content_type=content_type)

        if not _finish(video_id, job_id, status=VideoStatus.READY.value, result=result, error=None):
            logger.info("Story render for %s finished but was superseded; discarding", video_id)
            if stored_key:
                get_storage().delete(stored_key)
            return
        logger.info("Story render ready: video=%s kind=%s", video_id, rendered.kind)
    except Exception as exc:  # noqa: BLE001 - always land in FAILED with the real reason
        logger.exception("Story render failed: video=%s job=%s", video_id, job_id)
        if stored_key:
            try:
                get_storage().delete(stored_key)
            except Exception:  # noqa: BLE001
                logger.exception("Could not clean up %s after failed render", stored_key)
        _finish(video_id, job_id, status=VideoStatus.FAILED.value, error=f"{type(exc).__name__}: {exc}"[:500])
