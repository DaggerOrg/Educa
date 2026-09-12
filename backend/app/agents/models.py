"""Shared Gemini model construction for all three Agno agents/team.

Centralized so the API-key lookup and fallback list aren't triplicated
across agent.py/team.py/materials_agent.py. The free tier intermittently
returns 503 UNAVAILABLE under load on a given model id, so the primary is
backed by a few alternate flash models tried in order via Agno's native
`fallback_models` (see agno.models.fallback.FallbackConfig) -- no hand-rolled
retry loop needed.
"""
import os
from typing import List, Optional

from agno.models.google import Gemini

# Tried in order if the primary (EDUCA_MODEL) errors out with a
# retryable/5xx error. gemini-2.5-flash was in this list originally but the
# API now 404s it for new users ("no longer available to new users") --
# verified live against this project's key, not assumed from docs.
FALLBACK_MODEL_IDS = ["gemini-flash-lite-latest", "gemini-3.6-flash", "gemini-3.1-flash-lite"]


def _api_key() -> Optional[str]:
    # Agno's Gemini wrapper only reads GOOGLE_API_KEY -- ours is stored as
    # GEMINI_API_KEY in Infisical, so accept either name.
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")


def build_model() -> Gemini:
    return Gemini(id=os.environ.get("EDUCA_MODEL", "gemini-3.7-flash"), api_key=_api_key())


def build_fallback_models() -> List[Gemini]:
    primary_id = os.environ.get("EDUCA_MODEL", "gemini-3.7-flash")
    return [Gemini(id=model_id, api_key=_api_key()) for model_id in FALLBACK_MODEL_IDS if model_id != primary_id]
