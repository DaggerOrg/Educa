"""Tenant-scoped HTTP boundary for the independent RAG service."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.auth.context import require_role
from app.db import SessionLocal
from app import store as course_store

from .models import RagDocument
from .service import DocumentService
from .store import AgnoPgVectorStore

router = APIRouter(prefix="/api/rag", tags=["rag"])
_upload_root = Path("tmp/rag_uploads")
_document_service: DocumentService | None = None


def _service() -> DocumentService:
    global _document_service
    if _document_service is None:
        _document_service = DocumentService(AgnoPgVectorStore())
    return _document_service


def _assert_course_owner(course_id: str | None, user_id: str) -> None:
    if course_id:
        course = course_store.get_course(course_id)
        if not course:
            raise HTTPException(404, "Course not found")
        if course["teacherId"] != user_id:
            raise HTTPException(403, "You don't own this course")


def _document_out(document: RagDocument) -> dict:
    return {
        "id": document.id,
        "organization_id": document.organization_id,
        "course_id": document.course_id,
        "filename": document.filename,
        "title": document.title,
        "status": document.status,
        "chunk_count": document.chunk_count,
        "error": document.error,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    course_id: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


@router.post("/documents", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    course_id: str | None = Form(default=None),
    user: dict = Depends(require_role("teacher")),
):
    _assert_course_owner(course_id, user["id"])
    filename = Path(file.filename or "document").name
    content = await file.read()
    document_id = f"doc_{uuid.uuid4().hex}"
    _upload_root.mkdir(parents=True, exist_ok=True)
    storage_path = _upload_root / f"{document_id}{Path(filename).suffix.lower()}"
    storage_path.write_bytes(content)
    document = RagDocument(
        id=document_id,
        organization_id=user["id"],
        course_id=course_id,
        filename=filename,
        storage_path=str(storage_path),
    )
    with SessionLocal() as session:
        session.add(document)
        session.commit()
    try:
        result = _service().ingest(filename, content, user["id"], document_id, course_id)
        with SessionLocal() as session:
            saved = session.get(RagDocument, document_id)
            saved.title = result["title"]
            saved.chunk_count = result["chunk_count"]
            saved.status = "complete"
            session.commit()
            session.refresh(saved)
            return _document_out(saved)
    except (ValueError, KeyError) as error:
        with SessionLocal() as session:
            saved = session.get(RagDocument, document_id)
            saved.status = "failed"
            saved.error = str(error)
            session.commit()
        raise HTTPException(400, str(error)) from error


@router.get("/documents")
def list_documents(user: dict = Depends(require_role("teacher"))):
    with SessionLocal() as session:
        documents = session.scalars(
            select(RagDocument)
            .where(RagDocument.organization_id == user["id"])
            .order_by(RagDocument.created_at.desc())
        ).all()
    return [_document_out(document) for document in documents]


@router.get("/documents/{document_id}")
def get_document(document_id: str, user: dict = Depends(require_role("teacher"))):
    with SessionLocal() as session:
        document = session.scalar(
            select(RagDocument).where(
                RagDocument.id == document_id,
                RagDocument.organization_id == user["id"],
            )
        )
    if not document:
        raise HTTPException(404, "Document not found")
    return _document_out(document)


@router.get("/documents/{document_id}/status")
def get_document_status(document_id: str, user: dict = Depends(require_role("teacher"))):
    with SessionLocal() as session:
        document = session.scalar(
            select(RagDocument).where(
                RagDocument.id == document_id,
                RagDocument.organization_id == user["id"],
            )
        )
    if not document:
        raise HTTPException(404, "Document not found")
    return {
        "id": document.id,
        "status": document.status,
        "chunk_count": document.chunk_count,
        "error": document.error,
    }


@router.post("/retrieval/search")
def search_documents(body: SearchRequest, user: dict = Depends(require_role("teacher"))):
    return _service().search(body.query, user["id"], body.course_id, body.limit)