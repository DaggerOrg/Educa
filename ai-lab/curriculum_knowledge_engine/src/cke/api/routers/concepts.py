from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from cke.api.dependencies import get_curriculum_service
from cke.api.schemas.curricula import ConceptOut, ConceptWithScoreOut
from cke.services.curriculum_service import CurriculumService

router = APIRouter(prefix="/concepts", tags=["concepts"])


@router.get("", response_model=list[ConceptOut])
def list_concepts(
    service: Annotated[CurriculumService, Depends(get_curriculum_service)],
) -> list[ConceptOut]:
    return [ConceptOut.from_domain(c) for c in service.list_concepts()]


@router.get("/central", response_model=list[ConceptWithScoreOut])
def most_central_concepts(
    service: Annotated[CurriculumService, Depends(get_curriculum_service)],
    top_n: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[ConceptWithScoreOut]:
    """Concepts ranked by how many other concepts transitively depend on
    them - the most "foundational" topics in the ingested curricula."""
    return [
        ConceptWithScoreOut(concept=ConceptOut.from_domain(concept), score=score)
        for concept, score in service.most_foundational_concepts(top_n=top_n)
    ]


@router.get("/{concept_id}", response_model=ConceptOut)
def get_concept(
    concept_id: str,
    service: Annotated[CurriculumService, Depends(get_curriculum_service)],
) -> ConceptOut:
    return ConceptOut.from_domain(service.get_concept(concept_id))


@router.get("/{concept_id}/prerequisites", response_model=list[ConceptOut])
def get_prerequisites(
    concept_id: str,
    service: Annotated[CurriculumService, Depends(get_curriculum_service)],
) -> list[ConceptOut]:
    return [ConceptOut.from_domain(c) for c in service.get_prerequisites(concept_id)]


@router.get("/{concept_id}/dependents", response_model=list[ConceptOut])
def get_dependents(
    concept_id: str,
    service: Annotated[CurriculumService, Depends(get_curriculum_service)],
) -> list[ConceptOut]:
    return [ConceptOut.from_domain(c) for c in service.get_dependents(concept_id)]
