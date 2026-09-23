"""Tenant-scoped HTTP boundary for the document ingestion foundation.
Same auth/ownership pattern as rag/router.py: `require_role("teacher")`
plus an explicit ownership check on every project-scoped operation.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from redis.exceptions import RedisError

from app.auth.context import require_role

from .logging_config import get_logger
from .analysis import service as analysis_service
from .schemas import (
    DocumentOut,
    DocumentStatusOut,
    ProjectCreateRequest,
    ProjectOut,
    StudyGuideEntryOut,
    StudyGuideEntryUpdate,
    StudyGuideOut,
    StudyGuideRunOut,
)
from .service import (
    create_project,
    delete_document,
    get_document,
    list_documents,
    list_projects,
    retry_processing,
    upload_document,
)

router = APIRouter(prefix="/api/curriculum", tags=["curriculum-ingestion"])
logger = get_logger(__name__)


def _handle(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except RedisError as error:
        # The document row is already committed as UPLOADED by this point
        # (service.upload_document writes it before enqueueing) -- the
        # teacher sees a clear "try again" rather than a raw connection
        # traceback, and a manual retry (once Redis is back) picks the
        # same row up rather than creating a duplicate.
        logger.error("Job queue unavailable: %s", error)
        raise HTTPException(503, "Document processing queue is temporarily unavailable. Try again shortly.") from error
    except PermissionError as error:
        raise HTTPException(403, str(error)) from error
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project_route(body: ProjectCreateRequest, user: dict = Depends(require_role("teacher"))):
    return create_project(user["id"], body.title)


@router.get("/projects", response_model=list[ProjectOut])
def list_projects_route(user: dict = Depends(require_role("teacher"))):
    return list_projects(user["id"])


@router.post("/projects/{project_id}/documents", response_model=DocumentOut, status_code=202)
async def upload_document_route(
    project_id: str, file: UploadFile = File(...), user: dict = Depends(require_role("teacher"))
):
    content = await file.read()
    filename = Path(file.filename or "document.pdf").name
    content_type = file.content_type or "application/octet-stream"
    return _handle(upload_document, project_id, user["id"], filename, content, content_type)


@router.get("/projects/{project_id}/documents", response_model=list[DocumentOut])
def list_documents_route(project_id: str, user: dict = Depends(require_role("teacher"))):
    return _handle(list_documents, project_id, user["id"])


@router.get("/projects/{project_id}/documents/{document_id}", response_model=DocumentOut)
def get_document_route(project_id: str, document_id: str, user: dict = Depends(require_role("teacher"))):
    return _handle(get_document, project_id, document_id, user["id"])


@router.get("/projects/{project_id}/documents/{document_id}/status", response_model=DocumentStatusOut)
def get_document_status_route(project_id: str, document_id: str, user: dict = Depends(require_role("teacher"))):
    return _handle(get_document, project_id, document_id, user["id"])


@router.post("/projects/{project_id}/documents/{document_id}/retry", response_model=DocumentOut)
def retry_document_route(project_id: str, document_id: str, user: dict = Depends(require_role("teacher"))):
    return _handle(retry_processing, project_id, document_id, user["id"])


@router.delete("/projects/{project_id}/documents/{document_id}", status_code=204)
def delete_document_route(project_id: str, document_id: str, user: dict = Depends(require_role("teacher"))):
    _handle(delete_document, project_id, document_id, user["id"])


# --- study guide: the faculty panel's breakdown of a document --------------


@router.post("/projects/{project_id}/documents/{document_id}/analysis", response_model=StudyGuideRunOut, status_code=202)
def start_analysis_route(project_id: str, document_id: str, user: dict = Depends(require_role("teacher"))):
    return _handle(analysis_service.start_analysis, project_id, document_id, user["id"])


@router.get("/projects/{project_id}/documents/{document_id}/analysis", response_model=StudyGuideOut)
def get_study_guide_route(project_id: str, document_id: str, user: dict = Depends(require_role("teacher"))):
    return _handle(analysis_service.get_study_guide, project_id, document_id, user["id"])


@router.patch(
    "/projects/{project_id}/documents/{document_id}/analysis/entries/{entry_id}", response_model=StudyGuideEntryOut
)
def update_study_guide_entry_route(
    project_id: str,
    document_id: str,
    entry_id: str,
    body: StudyGuideEntryUpdate,
    user: dict = Depends(require_role("teacher")),
):
    return _handle(
        analysis_service.update_entry,
        project_id,
        document_id,
        entry_id,
        user["id"],
        review_status=body.review_status,
        title=body.title,
        data=body.data,
    )
