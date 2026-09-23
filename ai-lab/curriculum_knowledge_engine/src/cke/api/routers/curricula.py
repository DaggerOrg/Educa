from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from cke.api.dependencies import get_curriculum_service, get_ingestion_service
from cke.api.schemas.curricula import (
    CourseDetailOut,
    CourseSummaryOut,
    IngestCurriculumRequest,
    IngestCurriculumResponse,
)
from cke.config import get_settings
from cke.ingestion.curriculum_schema import CurriculumSpec
from cke.ingestion.ingestion_service import CurriculumIngestionService
from cke.services.curriculum_service import CurriculumService

router = APIRouter(prefix="/courses", tags=["curricula"])


@router.post("/ingest", response_model=IngestCurriculumResponse, status_code=201)
def ingest_curriculum(
    request: IngestCurriculumRequest,
    service: Annotated[CurriculumIngestionService, Depends(get_ingestion_service)],
) -> IngestCurriculumResponse:
    path = Path(request.file_path) if request.file_path else get_settings().sample_curriculum_path
    spec = CurriculumSpec.from_file(path)
    course = service.ingest(spec, enable_llm_extraction=request.enable_llm_extraction)
    return IngestCurriculumResponse(
        course=CourseSummaryOut.from_domain(course),
        message=(
            f"Ingested '{course.title}': {course.lesson_count} lessons across "
            f"{len(course.modules)} modules."
        ),
    )


@router.get("", response_model=list[CourseSummaryOut])
def list_courses(
    service: Annotated[CurriculumService, Depends(get_curriculum_service)],
) -> list[CourseSummaryOut]:
    return [CourseSummaryOut.from_domain(course) for course in service.list_courses()]


@router.get("/{course_id}", response_model=CourseDetailOut)
def get_course(
    course_id: str,
    service: Annotated[CurriculumService, Depends(get_curriculum_service)],
) -> CourseDetailOut:
    return CourseDetailOut.from_domain(service.get_course(course_id))
