from __future__ import annotations

from pydantic import BaseModel, Field


class Scene(BaseModel):
    narration: str  # what the avatar says, in the instructor's first person
    on_screen_text: str  # a short caption shown during the scene
    visual: str  # what the scene looks like (a description a renderer or illustrator can act on)
    seconds: int


class StoryScript(BaseModel):
    """Doubles as the agent's output schema and the teacher-edit payload, so
    it carries no length constraints (provider schema support for them is
    uneven) -- service.normalize_script enforces the limits."""

    title: str
    hook: str  # the opening line that makes a learner want to keep watching
    scenes: list[Scene]
    takeaway: str  # one-sentence close


class ScriptRequest(BaseModel):
    style: str = Field(default="", max_length=300)  # e.g. "playful, for teenagers"


class ScriptUpdate(BaseModel):
    script: StoryScript
