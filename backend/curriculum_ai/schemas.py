from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ProjectOut(BaseModel):
    id: str
    teacher_id: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: str
    project_id: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    checksum_sha256: str
    status: str
    processing_error: str | None
    processing_attempts: int
    uploaded_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentStatusOut(BaseModel):
    id: str
    status: str
    processing_error: str | None
    processing_attempts: int

    model_config = {"from_attributes": True}


class StudyGuideRunOut(BaseModel):
    id: str
    document_id: str
    status: str
    error: str | None
    model_id: str | None
    total_units: int
    completed_units: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StudyGuideUnitOut(BaseModel):
    id: str
    order_index: int
    title: str
    page_start: int
    page_end: int
    summary: str | None
    learning_objectives: list[str] | None
    status: str
    error: str | None

    model_config = {"from_attributes": True}


class StudyGuideEntryOut(BaseModel):
    id: str
    kind: str
    unit_order: int
    unit_title: str
    title: str
    data: dict
    evidence_quote: str | None
    page_start: int | None
    page_end: int | None
    grounded: bool
    review_status: str
    edited: bool

    model_config = {"from_attributes": True}


class StudyGuideOut(BaseModel):
    run: StudyGuideRunOut | None
    units: list[StudyGuideUnitOut]
    entries: list[StudyGuideEntryOut]


class StudyGuideEntryUpdate(BaseModel):
    review_status: str | None = None
    title: str | None = None
    data: dict | None = None
