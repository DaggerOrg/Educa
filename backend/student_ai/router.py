"""Student-only HTTP surface: private notes per lesson and the helper agents.
Same `require_role("student")` gating as the rest of the student routes in
app/main.py; enrollment/published checks are in service.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app import usage
from app.agents.structured import StructuredRunError
from app.auth.context import require_role

from . import service
from .agents import AGENTS
from .schemas import AssistRequest, NotesUpdate, SuggestRequest

router = APIRouter(prefix="/api", tags=["student-ai"])

_LESSON = "/courses/{course_id}/lessons/{lesson_id}"


def _handle(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except LookupError as error:
        raise HTTPException(404, str(error)) from error
    except service.TooLarge as error:
        raise HTTPException(413, str(error)) from error
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    except usage.UsageLimitExceeded as error:
        raise HTTPException(429, "You've reached today's AI helper limit. Try again tomorrow.") from error
    except StructuredRunError as error:
        raise HTTPException(503, "The AI helper is temporarily unavailable. Try again in a moment.") from error


@router.get("/student-ai/agents")
def list_agents(_: dict = Depends(require_role("student"))):
    return [
        {"key": a.key, "label": a.label, "description": a.description, "needsInput": a.needs_input}
        for a in AGENTS.values()
    ]


@router.get(_LESSON + "/notes")
def get_notes(course_id: str, lesson_id: str, user: dict = Depends(require_role("student"))):
    return _handle(service.get_notes, user["id"], course_id, lesson_id)


@router.put(_LESSON + "/notes")
def put_notes(course_id: str, lesson_id: str, body: NotesUpdate, user: dict = Depends(require_role("student"))):
    return _handle(service.save_notes, user["id"], course_id, lesson_id, body)


@router.post(_LESSON + "/notes/suggest")
def suggest(course_id: str, lesson_id: str, body: SuggestRequest, user: dict = Depends(require_role("student"))):
    return _handle(service.suggest_note, user["id"], course_id, lesson_id, body.heading, body.surrounding)


@router.post(_LESSON + "/assist/{agent}")
def assist(
    course_id: str, lesson_id: str, agent: str, body: AssistRequest, user: dict = Depends(require_role("student"))
):
    return _handle(service.assist, user["id"], course_id, lesson_id, agent, body.input, body.notes)
