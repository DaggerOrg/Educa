"""Structured outputs for the faculty panel (see agents.py).

Every specialist returns one of these Pydantic models rather than free
text, for the same reasons as agents/quiz/tools.py's QuizDraft: the model
call is schema-validated, and the result is directly persistable. Each
entry carries an `evidence_quote` and `page` so a teacher can check any
claim against the book -- the panel is required to cite, not just narrate
(docs/architecture/educa-ai-architecture.md SS8).
"""
from typing import List, Literal

from pydantic import BaseModel, Field


class ConceptEntry(BaseModel):
    name: str
    definition: str  # the precise definition, in the book's own terms
    explanation: str  # how a lecturer would put it to a first-time student
    prerequisites: List[str] = Field(default_factory=list)  # names of concepts a student must already know
    misconceptions: List[str] = Field(default_factory=list)
    evidence_quote: str  # short verbatim excerpt from the source text supporting this entry
    page: int


class ConceptAnalysis(BaseModel):
    concepts: List[ConceptEntry] = Field(default_factory=list)


class TheoryEntry(BaseModel):
    name: str
    statement: str  # the theory, law, theorem, or model, stated precisely
    intuition: str  # why it is true / what it says in plain language
    assumptions: List[str] = Field(default_factory=list)
    derivation_outline: List[str] = Field(default_factory=list)  # the key steps, in order
    applications: List[str] = Field(default_factory=list)
    evidence_quote: str
    page: int


class TheoryBreakdown(BaseModel):
    theories: List[TheoryEntry] = Field(default_factory=list)


class ExerciseEntry(BaseModel):
    kind: Literal["worked_example", "practice_problem", "conceptual_question"]
    title: str
    problem: str
    solution_approach: List[str] = Field(default_factory=list)  # the steps a lecturer would walk through
    final_answer: str  # "" unless the book gives one; never invented. No default: it would be sent to Gemini as a schema `default`, which some API versions reject.
    difficulty: Literal["introductory", "intermediate", "advanced"]
    concepts_tested: List[str] = Field(default_factory=list)
    evidence_quote: str
    page: int


class ExerciseBreakdown(BaseModel):
    exercises: List[ExerciseEntry] = Field(default_factory=list)


class ChairSummary(BaseModel):
    summary: str  # 3-5 sentences on what the chapter teaches and how it builds
    learning_objectives: List[str] = Field(default_factory=list)  # 3-6, "Students will be able to ..."
