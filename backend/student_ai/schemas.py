"""Request bodies and the structured answers each helper agent must return.

The answer models deliberately carry no length/count constraints: they are
sent to the model as its output schema, and provider schema support for
`minItems`/`maxLength` is uneven. Limits are enforced in service.py after
parsing instead.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---- requests -----------------------------------------------------------


class NotesUpdate(BaseModel):
    """Only the fields present in the body are written, so the editor and the
    sketch canvas can save independently without overwriting each other."""

    doc: dict | None = None
    sketch: dict | None = None


class SuggestRequest(BaseModel):
    heading: str = Field(min_length=1, max_length=200)
    # A little of what the student already wrote around the heading, so the
    # suggestion doesn't repeat it. Optional.
    surrounding: str = Field(default="", max_length=2000)


class AssistRequest(BaseModel):
    input: str = Field(default="", max_length=2000)  # a question, or the text the student selected
    notes: str = Field(default="", max_length=4000)  # plain text of the student's notes so far


# ---- structured answers ---------------------------------------------------


class NoteSuggestion(BaseModel):
    title: str
    summary: str
    key_points: list[str]
    example: str | None = None
    # "lesson" when the notes are drawn from the lesson material, "general"
    # when the topic isn't covered there and this is background knowledge.
    source: Literal["lesson", "general"]


class Explanation(BaseModel):
    explanation: str
    analogy: str | None = None
    check_question: str


class PracticeQuestion(BaseModel):
    question: str
    options: list[str]
    answer_index: int
    explanation: str


class PracticeQuiz(BaseModel):
    questions: list[PracticeQuestion]


class Flashcard(BaseModel):
    front: str
    back: str


class FlashcardSet(BaseModel):
    cards: list[Flashcard]


class Summary(BaseModel):
    summary: str
    key_points: list[str]
