from __future__ import annotations

from .base import RenderedVideo, RenderRequest


class StoryboardRenderer:
    """The default: no video provider is configured, so "rendering" just
    validates the script and marks it playable as a storyboard (scene cards,
    captions, optional browser narration). Honest about what it is -- the
    student player labels it a storyboard, not a video."""

    key = "mock"

    def render(self, request: RenderRequest) -> RenderedVideo:
        if not request.script.get("scenes"):
            raise ValueError("Script has no scenes to render")
        return RenderedVideo(kind="storyboard")
