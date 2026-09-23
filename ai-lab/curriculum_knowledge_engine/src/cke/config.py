"""Central configuration, read once from the environment.

Every other module receives its settings via `get_settings()` (cached) or
explicit constructor arguments - nothing else in the codebase calls
`os.environ` directly, so the whole app's configuration surface is this
one file.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class VectorBackend(StrEnum):
    CHROMA = "chroma"
    PGVECTOR = "pgvector"


class GraphBackend(StrEnum):
    NETWORKX = "networkx"
    NEO4J = "neo4j"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="CKE_",
        extra="ignore",
    )

    # --- LLM ---
    anthropic_api_key: str | None = Field(default=None)
    claude_model: str = "claude-opus-5"
    claude_effort: str = "high"
    claude_max_answer_tokens: int = 2048
    claude_max_extraction_tokens: int = 4096

    # --- Embeddings ---
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Storage backend selection ---
    vector_backend: VectorBackend = VectorBackend.CHROMA
    graph_backend: GraphBackend = GraphBackend.NETWORKX

    # --- Chroma (local vector backend) ---
    chroma_persist_dir: Path = PROJECT_ROOT / "var" / "chroma"
    chroma_collection: str = "cke_curriculum_chunks"

    # --- NetworkX (local graph backend) ---
    graph_persist_path: Path = PROJECT_ROOT / "var" / "concept_graph.json"

    # --- course tree persistence (always local JSON, regardless of vector/graph backend) ---
    course_persist_dir: Path = PROJECT_ROOT / "var" / "courses"

    # --- bundled sample content ---
    sample_curriculum_path: Path = PROJECT_ROOT / "data" / "sample_curriculum.yaml"

    # --- pgvector (production vector backend) ---
    postgres_dsn: str | None = Field(default=None)
    pgvector_table: str = "curriculum_chunks"
    pgvector_embedding_dim: int = 384  # matches all-MiniLM-L6-v2

    # --- Neo4j (production graph backend) ---
    neo4j_uri: str | None = Field(default=None)
    neo4j_user: str = "neo4j"
    neo4j_password: str | None = Field(default=None)

    # --- Retrieval tuning ---
    vector_top_k: int = 5
    graph_context_hops: int = 1

    # --- App / logging ---
    app_env: str = "development"
    log_level: str = "INFO"
    log_json: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
