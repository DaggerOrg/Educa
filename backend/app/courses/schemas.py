"""Request bodies for the course-authoring routes (courses/router.py).
Response bodies are plain dicts shaped by courses/service.py's
serializers -- see docs/api-contracts/README.md for those shapes."""
from pydantic import BaseModel


class LessonEdit(BaseModel):
    title: str | None = None
    objective: str | None = None


class ApprovalUpdate(BaseModel):
    approved: bool
