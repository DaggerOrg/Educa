"""Builds the configured repository implementations from `Settings`.

This is the single place that knows both interfaces *and* every concrete
backend - services and API routers only ever import from
`cke.repositories.interfaces`, never from a `*_repository` module directly.
"""

from __future__ import annotations

from cke.config import GraphBackend, Settings, VectorBackend
from cke.repositories.course.json_course_repository import JsonCourseRepository
from cke.repositories.graph.networkx_repository import NetworkXGraphRepository
from cke.repositories.interfaces import CourseRepository, GraphRepository, VectorRepository
from cke.repositories.vector.chroma_repository import ChromaVectorRepository


def build_course_repository(settings: Settings) -> CourseRepository:
    return JsonCourseRepository(persist_dir=settings.course_persist_dir)


def build_vector_repository(settings: Settings) -> VectorRepository:
    if settings.vector_backend == VectorBackend.CHROMA:
        return ChromaVectorRepository(
            persist_dir=settings.chroma_persist_dir,
            collection_name=settings.chroma_collection,
            embedding_model_name=settings.embedding_model_name,
        )
    if settings.vector_backend == VectorBackend.PGVECTOR:
        from cke.repositories.vector.pgvector_repository import PgVectorRepository

        if not settings.postgres_dsn:
            raise ValueError("CKE_POSTGRES_DSN is required when CKE_VECTOR_BACKEND=pgvector")
        return PgVectorRepository(
            dsn=settings.postgres_dsn,
            table_name=settings.pgvector_table,
            embedding_dim=settings.pgvector_embedding_dim,
            embedding_model_name=settings.embedding_model_name,
        )
    raise ValueError(f"Unknown vector backend: {settings.vector_backend}")


def build_graph_repository(settings: Settings) -> GraphRepository:
    if settings.graph_backend == GraphBackend.NETWORKX:
        return NetworkXGraphRepository(persist_path=settings.graph_persist_path)
    if settings.graph_backend == GraphBackend.NEO4J:
        from cke.repositories.graph.neo4j_repository import Neo4jGraphRepository

        if not settings.neo4j_uri or not settings.neo4j_password:
            raise ValueError(
                "CKE_NEO4J_URI and CKE_NEO4J_PASSWORD are required when CKE_GRAPH_BACKEND=neo4j"
            )
        return Neo4jGraphRepository(
            uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password
        )
    raise ValueError(f"Unknown graph backend: {settings.graph_backend}")
