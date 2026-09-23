from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from cke.api.dependencies import get_gap_analysis_service, get_learning_path_service
from cke.api.schemas.learning_paths import (
    GapAnalysisOut,
    GapAnalysisRequest,
    LearningPathRequest,
    LearningPlanOut,
)
from cke.services.gap_analysis_service import GapAnalysisService
from cke.services.learning_path_service import LearningPathService

router = APIRouter(prefix="/learning-paths", tags=["learning-paths"])


@router.post("", response_model=LearningPlanOut)
def build_learning_path(
    request: LearningPathRequest,
    service: Annotated[LearningPathService, Depends(get_learning_path_service)],
) -> LearningPlanOut:
    plan = service.build_plan(set(request.known_concept_ids), request.goal_concept_id)
    return LearningPlanOut.from_domain(plan)


@router.post("/gap-analysis", response_model=GapAnalysisOut)
def gap_analysis(
    request: GapAnalysisRequest,
    service: Annotated[GapAnalysisService, Depends(get_gap_analysis_service)],
) -> GapAnalysisOut:
    result = service.analyze(set(request.known_concept_ids), request.target_concept_id)
    return GapAnalysisOut.from_domain(result)
