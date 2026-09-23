"""Maps every domain exception (see `cke.domain.exceptions`) to an HTTP
response, so route handlers can raise a plain domain error and never touch
`HTTPException` or a status code directly. Registered once in
`cke.api.app.create_app()`.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cke.domain.exceptions import (
    CKEError,
    CurriculumIngestionError,
    CyclicPrerequisiteError,
    LLMGenerationError,
    NotFoundError,
    UnreachableGoalError,
    ValidationError,
)
from cke.logging_config import get_logger

logger = get_logger(__name__)


def _error_response(status_code: int, error_type: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": error_type, "detail": message})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def _not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return _error_response(404, "not_found", str(exc))

    @app.exception_handler(CyclicPrerequisiteError)
    async def _cyclic(request: Request, exc: CyclicPrerequisiteError) -> JSONResponse:
        return _error_response(409, "cyclic_prerequisite", str(exc))

    @app.exception_handler(UnreachableGoalError)
    async def _unreachable(request: Request, exc: UnreachableGoalError) -> JSONResponse:
        return _error_response(422, "unreachable_goal", str(exc))

    @app.exception_handler(ValidationError)
    async def _validation(request: Request, exc: ValidationError) -> JSONResponse:
        return _error_response(422, "validation_error", str(exc))

    @app.exception_handler(CurriculumIngestionError)
    async def _ingestion(request: Request, exc: CurriculumIngestionError) -> JSONResponse:
        return _error_response(400, "ingestion_error", str(exc))

    @app.exception_handler(LLMGenerationError)
    async def _llm(request: Request, exc: LLMGenerationError) -> JSONResponse:
        status_code = 503 if exc.retryable else 502
        logger.error("LLM generation error (retryable=%s): %s", exc.retryable, exc)
        return _error_response(status_code, "llm_generation_error", str(exc))

    @app.exception_handler(CKEError)
    async def _generic_domain_error(request: Request, exc: CKEError) -> JSONResponse:
        logger.exception("Unhandled domain error")
        return _error_response(500, "internal_error", str(exc))
