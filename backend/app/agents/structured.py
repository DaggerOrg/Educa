"""One structured-output agent call, shared by the small single-purpose
agents outside the /agui team (student notes helpers, module story writer).

Same construction as teaching_assistant.py -- a fresh `Agent` per call with
`build_model()` and the shared fallback list -- plus an `output_schema`, so
the result is a validated Pydantic object instead of free text the caller
would have to parse. Callers pass their own daily-cap check before calling;
this records the token usage afterwards.
"""
from typing import TypeVar

from agno.agent import Agent
from agno.run.base import RunStatus
from pydantic import BaseModel

from .. import usage
from .models import build_fallback_config, build_model

T = TypeVar("T", bound=BaseModel)


class StructuredRunError(RuntimeError):
    """The model call failed, or its answer didn't fit the requested schema."""


def run_structured(
    *, agent_name: str, user_id: str | None, instructions: str, prompt: str, output: type[T]
) -> T:
    model = build_model()
    agent = Agent(
        model=model,
        fallback_config=build_fallback_config(),
        instructions=instructions,
        output_schema=output,
    )
    result = agent.run(prompt)
    if user_id and result.metrics is not None:
        usage.record(user_id, agent_name, getattr(model, "id", None), result.metrics.input_tokens, result.metrics.output_tokens)
    # Agno's fallback handling packages an exhausted-provider error as
    # ordinary `.content` instead of raising, so check both status and type.
    if result.status == RunStatus.error or not isinstance(result.content, output):
        raise StructuredRunError(f"{agent_name} model call failed or returned an unusable answer")
    return result.content
