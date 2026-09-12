"""Course-materials routes: upload/list/delete the shared knowledge base
`materials_agent` searches while drafting (see materials/service.py)."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..auth.context import require_role
from . import service

router = APIRouter(prefix="/api", tags=["materials"])


@router.post("/materials")
async def upload_material(file: UploadFile = File(...), _: dict = Depends(require_role("teacher"))):
    # Indexes immediately -- a reference document isn't a creative AI
    # action that needs a teacher's sign-off, unlike the four course-
    # mutating agent tools. Shared across all teachers, like the rest of
    # this prototype's single knowledge base -- not yet scoped
    # per-teacher/course.
    try:
        return service.add_material(file.filename, await file.read())
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/materials")
def list_materials(_: dict = Depends(require_role("teacher"))):
    return service.list_materials()


@router.delete("/materials/{material_id}")
def delete_material(material_id: str, _: dict = Depends(require_role("teacher"))):
    if not service.delete_material(material_id):
        raise HTTPException(404, "Material not found")
    return {"ok": True}
