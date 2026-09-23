"""The only module in this codebase that talks to the Anthropic API.

Every other module that needs Claude goes through `ClaudeClient`, so the
request/response shape, model id, and error handling live in exactly one
place. See ai-lab/README.md for why generation is called directly through
the official SDK rather than through a framework's LLM wrapper class.
"""

from __future__ import annotations

from typing import TypeVar

import anthropic
from pydantic import BaseModel

from cke.config import Settings, get_settings
from cke.domain.exceptions import LLMGenerationError
from cke.logging_config import get_logger

logger = get_logger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)


class ClaudeClient:
    """Thin, typed wrapper around `anthropic.Anthropic`.

    Two entry points, matching the two things this app needs from an LLM:
    - `complete()` for free-text generation (Q&A answers, study-plan prose)
    - `extract()` for schema-constrained extraction (graph building), backed
      by `client.messages.parse()` so the result is a validated Pydantic
      model rather than hand-parsed JSON.
    """

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int | None = None,
        effort: str | None = None,
    ) -> str:
        try:
            response = self._client.messages.create(
                model=self._settings.claude_model,
                max_tokens=max_tokens or self._settings.claude_max_answer_tokens,
                system=system,
                output_config={"effort": effort or self._settings.claude_effort},
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:
            raise self._wrap(exc) from exc
        except TypeError as exc:
            raise self._wrap_credentials_error(exc) from exc

        if response.stop_reason == "refusal":
            raise LLMGenerationError(
                "Claude declined to answer this request (safety refusal)."
            )

        text = "".join(block.text for block in response.content if block.type == "text")
        if not text.strip():
            raise LLMGenerationError(
                f"Claude returned no text content (stop_reason={response.stop_reason!r})."
            )
        return text

    def extract(
        self,
        prompt: str,
        *,
        output_model: type[ModelT],
        system: str | None = None,
        max_tokens: int | None = None,
        effort: str | None = None,
    ) -> ModelT:
        try:
            response = self._client.messages.parse(
                model=self._settings.claude_model,
                max_tokens=max_tokens or self._settings.claude_max_extraction_tokens,
                system=system,
                output_config={"effort": effort or self._settings.claude_effort},
                messages=[{"role": "user", "content": prompt}],
                output_format=output_model,
            )
        except anthropic.APIError as exc:
            raise self._wrap(exc) from exc
        except TypeError as exc:
            raise self._wrap_credentials_error(exc) from exc

        if response.stop_reason == "refusal":
            raise LLMGenerationError(
                "Claude declined to answer this request (safety refusal)."
            )
        if response.parsed_output is None:
            raise LLMGenerationError(
                f"Claude's structured output failed to parse (stop_reason={response.stop_reason!r})."
            )
        return response.parsed_output

    @staticmethod
    def _wrap_credentials_error(exc: TypeError) -> LLMGenerationError:
        # The SDK raises a bare TypeError - not an anthropic.APIError
        # subclass - when it can't resolve any credentials at all (no
        # ANTHROPIC_API_KEY, no ANTHROPIC_AUTH_TOKEN, no `ant auth login`
        # profile), since it fails validating request headers before a
        # request is even sent. Narrowed to this try block so an unrelated
        # TypeError from our own code isn't accidentally swallowed here.
        logger.error("Claude credentials could not be resolved: %s", exc)
        return LLMGenerationError(
            "Claude API credentials are not configured (set ANTHROPIC_API_KEY, "
            "ANTHROPIC_AUTH_TOKEN, or run `ant auth login`).",
            retryable=False,
        )

    @staticmethod
    def _wrap(exc: anthropic.APIError) -> LLMGenerationError:
        # Most-specific-first: each branch logs and classifies retryability
        # the way an ops runbook would, not just "the call failed".
        if isinstance(exc, anthropic.AuthenticationError):
            logger.error("Claude authentication failed - check ANTHROPIC_API_KEY")
            return LLMGenerationError("Claude authentication failed.", retryable=False)
        if isinstance(exc, anthropic.RateLimitError):
            retry_after = exc.response.headers.get("retry-after", "unknown")
            logger.warning("Claude rate limited, retry-after=%s", retry_after)
            return LLMGenerationError("Claude rate limit exceeded.", retryable=True)
        if isinstance(exc, anthropic.NotFoundError):
            logger.error("Claude model not found: %s", exc.message)
            return LLMGenerationError(f"Claude model not available: {exc.message}", retryable=False)
        if isinstance(exc, anthropic.BadRequestError):
            logger.error("Claude rejected the request: %s", exc.message)
            return LLMGenerationError(f"Invalid request to Claude: {exc.message}", retryable=False)
        if isinstance(exc, anthropic.APIStatusError):
            retryable = exc.status_code >= 500
            logger.error("Claude API error %s: %s", exc.status_code, exc.message)
            return LLMGenerationError(f"Claude API error: {exc.message}", retryable=retryable)
        if isinstance(exc, anthropic.APIConnectionError):
            logger.error("Could not reach the Claude API")
            return LLMGenerationError("Could not reach the Claude API.", retryable=True)
        logger.error("Unexpected Claude SDK error: %s", exc)
        return LLMGenerationError(f"Unexpected Claude SDK error: {exc}", retryable=False)
