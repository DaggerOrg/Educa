"""FastAPI dependency accessors.

The `Container` is built once at app startup (see `cke.api.app`'s lifespan
context manager) and stashed on `app.state`; every dependency function here
just reaches into it. Routers depend on these, never on `cke.container`
directly, so a route's signature says exactly which service it needs.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from cke.container import Container
from cke.ingestion.ingestion_service import CurriculumIngestionService
from cke.services.curriculum_service import CurriculumService
from cke.services.gap_analysis_service import GapAnalysisService
from cke.services.learning_path_service import LearningPathService
from cke.services.qa_service import QAService


def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_ingestion_service(container: ContainerDep) -> CurriculumIngestionService:
    return container.ingestion_service


def get_qa_service(container: ContainerDep) -> QAService:
    return container.qa_service


def get_learning_path_service(container: ContainerDep) -> LearningPathService:
    return container.learning_path_service


def get_gap_analysis_service(container: ContainerDep) -> GapAnalysisService:
    return container.gap_analysis_service


def get_curriculum_service(container: ContainerDep) -> CurriculumService:
    return container.curriculum_service
