"""Turns a learner's known concepts + a goal concept into an ordered study
plan.

The *order* is never left to the LLM: `GraphRepository.shortest_prerequisite_chain`
computes it deterministically via topological sort over the REQUIRES
sub-graph, exactly the way `_extract_and_merge_graph` in the ingestion
service keeps LLM-authored graph edges separate from human-authored ones.
Claude's only job here is pedagogical narrative - explaining *why* each
step matters given what comes before it, and estimating study time - which
is enrichment, not a source of truth, and is validated/repaired if the
model's response doesn't line up with the graph's concept list.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from cke.domain.exceptions import NotFoundError
from cke.domain.models import Concept, LearningPathStep, LearningPlan
from cke.llm.claude_client import ClaudeClient
from cke.logging_config import get_logger
from cke.repositories.interfaces import GraphRepository
from cke.retrieval.vector_retriever import VectorRetriever

logger = get_logger(__name__)

_PLAN_SYSTEM_PROMPT = """\
You are an instructional designer. You are given an ordered list of \
concepts a learner must study, in the exact order they must be studied \
(this order is fixed by prerequisite dependencies - never reorder it). For \
each concept, write one or two sentences explaining why it matters at this \
point in the sequence (referencing what the learner already knows and what \
came just before it), and estimate realistic focused study minutes (typically \
15-90). Then write one short paragraph summarizing the overall plan. \
Return every concept from the input list, in the same order, using its \
exact name."""

_FALLBACK_MINUTES = 30


class _StepNarrative(BaseModel):
    concept_name: str
    rationale: str
    estimated_minutes: int = Field(ge=5, le=240)


class _PlanNarrative(BaseModel):
    steps: list[_StepNarrative]
    summary: str


def _build_narrative_prompt(
    ordered_concepts: list[Concept], known_concepts: list[Concept], goal: Concept
) -> str:
    known_block = ", ".join(c.name for c in known_concepts) or "(nothing yet)"
    steps_block = "\n".join(
        f"{i + 1}. {c.name} - {c.description}".rstrip(" -")
        for i, c in enumerate(ordered_concepts)
    )
    return (
        f"Learner already knows: {known_block}\n"
        f"Goal concept: {goal.name}\n\n"
        f"Fixed study order:\n{steps_block}"
    )


class LearningPathService:
    def __init__(
        self,
        graph_repository: GraphRepository,
        vector_retriever: VectorRetriever,
        claude_client: ClaudeClient,
        *,
        resources_per_step: int = 2,
    ):
        self._graph = graph_repository
        self._vector_retriever = vector_retriever
        self._claude = claude_client
        self._resources_per_step = resources_per_step

    def build_plan(self, known_concept_ids: set[str], goal_concept_id: str) -> LearningPlan:
        goal = self._graph.get_concept(goal_concept_id)
        if goal is None:
            raise NotFoundError("Concept", goal_concept_id)

        ordered_ids = self._graph.shortest_prerequisite_chain(known_concept_ids, goal_concept_id)
        if not ordered_ids:
            return LearningPlan(
                goal_concept_id=goal_concept_id,
                known_concept_ids=sorted(known_concept_ids),
                steps=[],
                summary=f"You already know everything required for '{goal.name}'.",
                total_estimated_minutes=0,
            )

        ordered_concepts = [self._graph.get_concept(cid) for cid in ordered_ids]
        ordered_concepts = [c for c in ordered_concepts if c is not None]

        known_concepts = [
            c for cid in sorted(known_concept_ids) if (c := self._graph.get_concept(cid))
        ]

        narrative = self._narrate(ordered_concepts, known_concepts, goal)
        narrative_by_name = {step.concept_name.lower(): step for step in narrative.steps}

        steps: list[LearningPathStep] = []
        for concept in ordered_concepts:
            step_narrative = narrative_by_name.get(concept.name.lower())
            if step_narrative is None:
                logger.warning(
                    "Claude's plan narrative omitted concept '%s'; using a fallback rationale",
                    concept.name,
                )
            resources = self._vector_retriever.retrieve_citations(
                concept.name, top_k=self._resources_per_step
            )
            steps.append(
                LearningPathStep(
                    concept=concept,
                    rationale=step_narrative.rationale
                    if step_narrative
                    else f"Required before you can understand '{goal.name}'.",
                    estimated_minutes=step_narrative.estimated_minutes
                    if step_narrative
                    else _FALLBACK_MINUTES,
                    resources=resources,
                )
            )

        return LearningPlan(
            goal_concept_id=goal_concept_id,
            known_concept_ids=sorted(known_concept_ids),
            steps=steps,
            summary=narrative.summary,
        )

    def _narrate(
        self, ordered_concepts: list[Concept], known_concepts: list[Concept], goal: Concept
    ) -> _PlanNarrative:
        prompt = _build_narrative_prompt(ordered_concepts, known_concepts, goal)
        try:
            return self._claude.extract(
                prompt, output_model=_PlanNarrative, system=_PLAN_SYSTEM_PROMPT
            )
        except Exception as exc:  # noqa: BLE001 - narrative is enrichment; fall back rather than fail the plan
            logger.warning("Plan narration failed, using fallback rationale for every step: %s", exc)
            return _PlanNarrative(
                steps=[
                    _StepNarrative(
                        concept_name=c.name,
                        rationale=f"Required before you can understand '{goal.name}'.",
                        estimated_minutes=_FALLBACK_MINUTES,
                    )
                    for c in ordered_concepts
                ],
                summary=f"A {len(ordered_concepts)}-step path to '{goal.name}'.",
            )
