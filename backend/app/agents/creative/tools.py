"""Tool for creative_agent -- the AI Creative image-generation specialist.

Originally called DALL-E (OpenAI retired dall-e-3 on 2026-03-04, so that
integration stopped working outright) -- switched to Gemini 2.5 Flash
Image ("Nano Banana") instead, which is free up to 500 images/day on
Google AI Studio's free tier and reuses the same GOOGLE_API_KEY/
GEMINI_API_KEY every other agent in this project already authenticates
with via `agents/models.py`'s `api_key()` -- no new provider key needed.

Calls the `google-genai` SDK directly (the same one Agno's own `Gemini`
model wraps) rather than going through an Agno toolkit, since we need
`requires_confirmation` on this call -- generating and saving an image is
a creative AI action like every other content-mutating tool in this
codebase, so it needs the same HITL gate a wrapped, non-`@tool` SDK method
couldn't get.
"""
import logging

from agno.tools import tool
from google import genai
from google.genai.types import GenerateContentConfig

from ... import creative
from ... import audit
from ...auth.context import current_user_id
from ..models import api_key

logger = logging.getLogger(__name__)

_MODEL_ID = "gemini-2.5-flash-image"


@tool(requires_confirmation=True)
def generate_creative_image(prompt: str, filename: str) -> dict:
    """Generate an image with Gemini from a text prompt and save it to the
    teacher's AI Creative library. `filename` should be a short,
    descriptive `.png` name (e.g. "photosynthesis-diagram.png") -- it's
    what the teacher sees in their library, not used for anything
    functional.
    """
    logger.info("generate_creative_image: prompt=%r filename=%s", prompt, filename)
    client = genai.Client(api_key=api_key())
    response = client.models.generate_content(
        model=_MODEL_ID,
        contents=prompt,
        config=GenerateContentConfig(response_modalities=["IMAGE"]),
    )

    image_bytes = None
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None and part.inline_data.data is not None:
            image_bytes = part.inline_data.data
            break
    if image_bytes is None:
        raise ValueError("Gemini did not return an image")

    asset = creative.add_asset(current_user_id(), filename, "image/png", image_bytes)
    logger.info("generate_creative_image: saved asset=%s", asset["id"])
    audit.record("generate_creative_image", asset["id"], f"Generated image '{filename}'")
    return asset


TOOLS = [generate_creative_image]
