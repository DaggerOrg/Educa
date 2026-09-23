"""Shared Gemini model construction for all three Agno agents/team.

Centralized so the API-key lookup and fallback list aren't triplicated
across agent.py/team.py/materials_agent.py. The free tier intermittently
returns 503 UNAVAILABLE under load on a given model id, so the primary is
backed by a few alternate flash models tried in order via Agno's native
`fallback_models` (see agno.models.fallback.FallbackConfig) -- no hand-rolled
retry loop needed.

`timeout` matters as much as the fallback list: without one, a stuck (not
just erroring) call to a given model -- observed live against the free
tier, not hypothetical -- hangs the whole chat turn forever with no error
surfaced to the teacher, since Agno only moves on to the next fallback
once the current attempt actually fails. 30s is generous for a flash-tier
model's first token; a genuinely healthy call finishes well under that.
"""
import os
from typing import List, Optional

from agno.models.fallback import FallbackConfig
from agno.models.google import Gemini

# Tried in order if the primary (EDUCA_MODEL) errors out with a
# retryable/5xx error. gemini-2.5-flash was in this list originally but the
# API now 404s it for new users ("no longer available to new users") --
# verified live against this project's key, not assumed from docs.
FALLBACK_MODEL_IDS = ["gemini-flash-lite-latest", "gemini-3.6-flash", "gemini-3.1-flash-lite"]

REQUEST_TIMEOUT_SECONDS = 30


def api_key() -> Optional[str]:
    # Agno's Gemini wrapper only reads GOOGLE_API_KEY -- ours is stored as
    # GEMINI_API_KEY in Infisical, so accept either name.
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")


def build_model(timeout: int = REQUEST_TIMEOUT_SECONDS) -> Gemini:
    return Gemini(id=os.environ.get("EDUCA_MODEL", "gemini-3.7-flash"), api_key=api_key(), timeout=timeout)


def build_fallback_models(timeout: int = REQUEST_TIMEOUT_SECONDS) -> List[Gemini]:
    primary_id = os.environ.get("EDUCA_MODEL", "gemini-3.7-flash")
    return [
        Gemini(id=model_id, api_key=api_key(), timeout=timeout)
        for model_id in FALLBACK_MODEL_IDS
        if model_id != primary_id
    ]


def build_fallback_config(timeout: int = REQUEST_TIMEOUT_SECONDS) -> FallbackConfig:
    """`fallback_models=` alone only covers generic errors (`on_error`); a 429
    from a rate-limited free-tier model would surface to the teacher instead
    of trying a sibling model. Gemini tracks quotas per model, so the
    same alternates are also tried on rate-limit."""
    return FallbackConfig(
        on_error=build_fallback_models(timeout),
        on_rate_limit=build_fallback_models(timeout),
    )
