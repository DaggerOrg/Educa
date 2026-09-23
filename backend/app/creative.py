"""AI Creative: a personal, cross-course media library.

Upload is a plain, immediately-effective operation, same spirit as
`knowledge.py`'s course materials -- no agent/HITL gate, it's not a
creative AI action in itself, just bringing in a file. Real AI generation
*is* wired up now: `agents/creative/tools.py`'s `generate_creative_image`
calls Gemini 2.5 Flash Image (free tier, same GOOGLE_API_KEY/
GEMINI_API_KEY every other agent already uses) and saves the result here
via `add_asset`, same as any other upload -- HITL-gated like every other
content-mutating agent tool, unlike a plain upload.

Bytes live on local disk under `_UPLOAD_ROOT` (gitignored, alongside
`tmp/educa_agent.db`) rather than in Postgres -- this row is metadata, not
a blob store. No external storage dependency, matching this prototype's
zero-external-deps spirit elsewhere (mocked marketplace payments, etc).
"""
import os
import re

from .db import SessionLocal
from .models_db import CreativeAsset

_UPLOAD_ROOT = os.path.join("tmp", "creative_uploads")
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_VIDEO_BYTES = 200 * 1024 * 1024

_EXT_RE = re.compile(r"^[a-zA-Z0-9]{1,8}$")


def _kind_for(content_type: str) -> str:
    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("video/"):
        return "video"
    raise ValueError(f"Unsupported content type: {content_type} (upload an image or video)")


def _safe_ext(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    return ext.lower() if _EXT_RE.match(ext) else "bin"


def _serialize(asset: CreativeAsset) -> dict:
    return {
        "id": asset.id,
        "kind": asset.kind,
        "filename": asset.filename,
        "contentType": asset.content_type,
        "createdAt": asset.created_at.isoformat(),
    }


def add_asset(teacher_id: str, filename: str, content_type: str, content: bytes) -> dict:
    kind = _kind_for(content_type)
    limit = MAX_IMAGE_BYTES if kind == "image" else MAX_VIDEO_BYTES
    if len(content) > limit:
        raise ValueError(f"File too large (max {limit // (1024 * 1024)}MB for {kind})")

    os.makedirs(_UPLOAD_ROOT, exist_ok=True)
    with SessionLocal() as session:
        asset = CreativeAsset(
            teacher_id=teacher_id,
            kind=kind,
            filename=filename,
            content_type=content_type,
            storage_path="",  # filled in below once we have the generated id
        )
        session.add(asset)
        session.flush()  # assigns asset.id without committing yet
        storage_path = os.path.join(_UPLOAD_ROOT, f"{asset.id}.{_safe_ext(filename)}")
        asset.storage_path = storage_path
        with open(storage_path, "wb") as f:
            f.write(content)
        session.commit()
        return _serialize(asset)


def list_assets(teacher_id: str) -> list[dict]:
    with SessionLocal() as session:
        assets = (
            session.query(CreativeAsset)
            .filter(CreativeAsset.teacher_id == teacher_id)
            .order_by(CreativeAsset.created_at.desc())
            .all()
        )
        return [_serialize(a) for a in assets]


def get_asset(asset_id: str, teacher_id: str) -> CreativeAsset | None:
    with SessionLocal() as session:
        asset = session.get(CreativeAsset, asset_id)
        if not asset or asset.teacher_id != teacher_id:
            return None
        session.expunge(asset)
        return asset


def delete_asset(asset_id: str, teacher_id: str) -> bool:
    with SessionLocal() as session:
        asset = session.get(CreativeAsset, asset_id)
        if not asset or asset.teacher_id != teacher_id:
            return False
        storage_path = asset.storage_path
        session.delete(asset)
        session.commit()
        if storage_path and os.path.exists(storage_path):
            os.remove(storage_path)
        return True
