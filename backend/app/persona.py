"""Teacher Persona: a teacher's own enrolled video/voice likeness.

No avatar-rendering provider is integrated (checked against Agno's own
tool catalog -- DALL-E/nano-banana/fal/replicate/lumalab are all generic
generation, not "clone a specific person" services, and none of the
dedicated avatar providers like HeyGen/Synthesia/D-ID/Tavus are wired up).
So this module only owns real enrollment data -- the training clip lives
in creative.py's storage (a CreativeAsset the teacher already uploaded),
this is just the persona record + consent timestamp on top of it. The
frontend renders playback as a clearly-labeled mock, never calls out to
any rendering service.
"""
from datetime import datetime, timezone

from . import store
from .db import SessionLocal
from .models_db import CreativeAsset, TeacherPersona


def _serialize(persona: TeacherPersona) -> dict:
    return {
        "id": persona.id,
        "name": persona.name,
        "trainingAssetId": persona.training_asset_id,
        "consentedAt": persona.consented_at.isoformat(),
        "createdAt": persona.created_at.isoformat(),
    }


def create_or_update_persona(teacher_id: str, name: str, training_asset_id: str, consented: bool) -> dict:
    if not consented:
        raise ValueError("Consent is required to create a persona")
    with SessionLocal() as session:
        asset = session.get(CreativeAsset, training_asset_id)
        if not asset or asset.teacher_id != teacher_id:
            raise ValueError("Training video not found")
        if asset.kind != "video":
            raise ValueError("A persona needs a short video (for both likeness and voice)")

        existing = session.query(TeacherPersona).filter(TeacherPersona.teacher_id == teacher_id).one_or_none()
        if existing:
            existing.name = name
            existing.training_asset_id = training_asset_id
            existing.consented_at = datetime.now(timezone.utc)
            persona = existing
        else:
            persona = TeacherPersona(
                teacher_id=teacher_id,
                name=name,
                training_asset_id=training_asset_id,
                consented_at=datetime.now(timezone.utc),
            )
            session.add(persona)
        session.commit()
        return _serialize(persona)


def get_persona(teacher_id: str) -> dict | None:
    with SessionLocal() as session:
        persona = session.query(TeacherPersona).filter(TeacherPersona.teacher_id == teacher_id).one_or_none()
        return _serialize(persona) if persona else None


def get_persona_for_course(course_id: str) -> dict | None:
    course = store.get_course(course_id)
    if not course:
        return None
    return get_persona(course["teacherId"])


def delete_persona(teacher_id: str) -> bool:
    with SessionLocal() as session:
        persona = session.query(TeacherPersona).filter(TeacherPersona.teacher_id == teacher_id).one_or_none()
        if not persona:
            return False
        session.delete(persona)
        session.commit()
        return True
