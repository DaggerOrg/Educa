"""Request-scoped authenticated-user id, readable from plain functions that
don't receive FastAPI `Depends` themselves -- namely the agent tools in
`agents/curriculum/tools.py`, `agents/lesson_content/tools.py`, and
`agents/quiz/tools.py`. Those tools are called by Agno while handling a
POST /agui request; `set_current_user` (a FastAPI dependency, wired onto
both the AGUI router and the plain REST routers in main.py) runs first and
populates this before any tool call happens, so ownership checks in
store.py can trust it instead of trusting a course/lesson id the model
supplies for addressing.
"""
from contextvars import ContextVar

from fastapi import Depends, HTTPException

from .routes import get_current_user

_current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)


def current_user_id() -> str:
    user_id = _current_user_id.get()
    if user_id is None:
        raise RuntimeError("current_user_id() read outside an authenticated request")
    return user_id


async def set_current_user(user: dict = Depends(get_current_user)) -> dict:
    # Must be `async def`, not `def` -- FastAPI runs sync dependencies in a
    # threadpool, and a ContextVar.set() made in a worker thread does not
    # reliably propagate back to the request's own asyncio Task. An async
    # dependency runs inline in that Task, so the .set() below is visible to
    # everything the route handler awaits afterwards, including deep inside
    # Agno's tool execution -- see this module's docstring.
    _current_user_id.set(user["id"])
    return user


def require_role(role: str):
    """FastAPI dependency factory gating a route to one role, e.g.
    `Depends(require_role("teacher"))`. Also runs `set_current_user`'s
    context-setting side effect, so a route can use just this one
    dependency instead of both."""

    async def _check(user: dict = Depends(set_current_user)) -> dict:
        if user["role"] != role:
            raise HTTPException(403, f"This action requires a {role} account")
        return user

    return _check
