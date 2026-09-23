from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class RenderRequest:
    script: dict  # the approved, normalized StoryScript as a dict
    module_title: str
    narrator_name: str | None  # the teacher's persona name, if they've set one up


@dataclass(frozen=True)
class RenderedVideo:
    """`storyboard`: no media file -- the app plays the script itself.
    `video`: a real rendered file, returned as bytes for the caller to store."""

    kind: Literal["storyboard", "video"]
    video_bytes: bytes | None = None
    content_type: str | None = None


class VideoRenderer(Protocol):
    key: str

    def render(self, request: RenderRequest) -> RenderedVideo:
        """Turn an approved script into a video. May take minutes and may
        raise; module_video.render.render_module_video records the failure."""
