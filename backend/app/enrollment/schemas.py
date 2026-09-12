"""Request body for submitting a quiz attempt (enrollment/router.py)."""
from pydantic import BaseModel


class QuizAttemptSubmit(BaseModel):
    quizItemId: str
    selectedIndex: int
