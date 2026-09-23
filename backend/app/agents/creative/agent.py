"""The AI Creative specialist: generates images from a text prompt and
saves them into the teacher's cross-course media library (creative.py).
"""
from agno.agent import Agent

from ..storage import build_agent_db
from ..safety import with_safety_rules
from ..models import build_fallback_config, build_model
from .tools import TOOLS

INSTRUCTIONS = (
    "You generate images for teachers to use in their courses -- diagrams, "
    "illustrations, thumbnails, anything they describe. Write a clear, "
    "detailed image-generation prompt from what the teacher asked for, pick "
    "a short descriptive filename ending in .png, and call "
    "generate_creative_image once. The image is saved straight to the "
    "teacher's AI Creative library, not attached to a specific course or "
    "lesson."
)


def build_creative_agent() -> Agent:
    return Agent(
        name="creative_agent",
        model=build_model(),
        fallback_config=build_fallback_config(),
        tools=TOOLS,
        instructions=with_safety_rules(INSTRUCTIONS),
        # Required for the requires_confirmation tool in tools.py: a paused
        # run's state lives here between the pause and resume request.
        db=build_agent_db(),
    )
