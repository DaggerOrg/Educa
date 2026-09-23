from __future__ import annotations

from pydantic import BaseModel, Field

from cke.domain.models import GapAnalysisResult, LearningPathStep, LearningPlan
from cke.api.schemas.curricula import ConceptOut
from cke.api.schemas.qa import CitationOut


class LearningPathRequest(BaseModel):
    known_concept_ids: list[str] = Field(default_factory=list)
    goal_concept_id: str


class LearningPathStepOut(BaseModel):
    concept: ConceptOut
    rationale: str
    estimated_minutes: int
    resources: list[CitationOut]

    @classmethod
    def from_domain(cls, step: LearningPathStep) -> LearningPathStepOut:
        return cls(
            concept=ConceptOut.from_domain(step.concept),
            rationale=step.rationale,
            estimated_minutes=step.estimated_minutes,
            resources=[CitationOut.from_domain(r) for r in step.resources],
        )


class LearningPlanOut(BaseModel):
    goal_concept_id: str
    known_concept_ids: list[str]
    steps: list[LearningPathStepOut]
    summary: str
    total_estimated_minutes: int

    @classmethod
    def from_domain(cls, plan: LearningPlan) -> LearningPlanOut:
        return cls(
            goal_concept_id=plan.goal_concept_id,
            known_concept_ids=plan.known_concept_ids,
            steps=[LearningPathStepOut.from_domain(step) for step in plan.steps],
            summary=plan.summary,
            total_estimated_minutes=plan.total_estimated_minutes,
        )


class GapAnalysisRequest(BaseModel):
    known_concept_ids: list[str] = Field(default_factory=list)
    target_concept_id: str


class GapAnalysisOut(BaseModel):
    target_id: str
    known_concept_ids: list[str]
    required_concept_ids: list[str]
    missing_concepts: list[ConceptOut]
    readiness_pct: float

    @classmethod
    def from_domain(cls, result: GapAnalysisResult) -> GapAnalysisOut:
        return cls(
            target_id=result.target_id,
            known_concept_ids=result.known_concept_ids,
            required_concept_ids=result.required_concept_ids,
            missing_concepts=[ConceptOut.from_domain(c) for c in result.missing_concepts],
            readiness_pct=result.readiness_pct,
        )
