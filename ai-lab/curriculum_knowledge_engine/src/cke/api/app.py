from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from cke import __version__
from cke.api.error_handlers import register_error_handlers
from cke.api.routers import concepts, curricula, health, learning_paths, qa
from cke.config import get_settings
from cke.container import build_container
from cke.logging_config import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(level=settings.log_level, as_json=settings.log_json)
    logger.info(
        "Starting Curriculum Knowledge Engine (vector_backend=%s, graph_backend=%s)",
        settings.vector_backend,
        settings.graph_backend,
    )
    app.state.container = build_container(settings)
    yield
    logger.info("Shutting down Curriculum Knowledge Engine")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Curriculum Knowledge Engine",
        description=(
            "Enterprise curriculum knowledge engine: hybrid RAG + GraphRAG "
            "over ingested curricula, plus graph-driven learning paths."
        ),
        version=__version__,
        lifespan=lifespan,
    )
    register_error_handlers(app)

    app.include_router(health.router)
    app.include_router(curricula.router)
    app.include_router(concepts.router)
    app.include_router(qa.router)
    app.include_router(learning_paths.router)

    return app


app = create_app()
