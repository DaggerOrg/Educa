"""Renderer selection: VIDEO_PROVIDER, "mock" (default) for now.

To add a real provider (a talking-avatar API, a text-to-video API, ...):
write a class in this package with a `key` and a `render(request)` that
returns `RenderedVideo(kind="video", video_bytes=..., content_type=...)`,
then add it to `_RENDERERS` below. Nothing else changes -- the job, storage,
status flow and student player already handle `kind="video"`.
"""

from __future__ import annotations

import os

from .base import RenderedVideo, RenderRequest, VideoRenderer
from .mock import StoryboardRenderer

_RENDERERS: dict[str, type] = {StoryboardRenderer.key: StoryboardRenderer}

DEFAULT_PROVIDER = "mock"


def configured_provider() -> str:
    return (os.environ.get("VIDEO_PROVIDER") or DEFAULT_PROVIDER).lower()


def get_renderer(key: str | None = None) -> VideoRenderer:
    key = (key or configured_provider()).lower()
    renderer = _RENDERERS.get(key)
    if renderer is None:
        raise ValueError(f"Unknown VIDEO_PROVIDER: {key!r} (available: {', '.join(sorted(_RENDERERS))})")
    return renderer()


__all__ = ["RenderRequest", "RenderedVideo", "VideoRenderer", "configured_provider", "get_renderer"]
