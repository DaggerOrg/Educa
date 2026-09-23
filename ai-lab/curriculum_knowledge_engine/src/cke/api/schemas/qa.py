from __future__ import annotations

from pydantic import BaseModel, Field

from cke.domain.models import AnswerResult, Citation


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    course_id: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)


class CitationOut(BaseModel):
    chunk_id: str
    lesson_id: str
    lesson_title: str
    snippet: str
    relevance_score: float

    @classmethod
    def from_domain(cls, citation: Citation) -> CitationOut:
        return cls(**citation.model_dump())


class AskResponse(BaseModel):
    question: str
    answer: str
    citations: list[CitationOut]
    concepts_referenced: list[str]

    @classmethod
    def from_domain(cls, result: AnswerResult) -> AskResponse:
        return cls(
            question=result.question,
            answer=result.answer,
            citations=[CitationOut.from_domain(c) for c in result.citations],
            concepts_referenced=result.concepts_referenced,
        )
