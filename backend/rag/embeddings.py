"""Embedding provider selection for `AgnoPgVectorStore`.

Returns an Agno-native embedder (one implementing `get_embedding` /
`get_embedding_and_usage`, per `agno.knowledge.embedder.base.Embedder`) so
it plugs directly into `agno.vectordb.pgvector.PgVector`, which reads
`embedder.dimensions` to size the vector column and calls
`embedder.get_embedding_and_usage` on every insert/query.

Defaults to a local `sentence-transformers` model - no API key, no
billing, runs on CPU. Set `RAG_EMBEDDER_PROVIDER=openai` (needs a funded
`OPENAI_API_KEY`) for OpenAI's hosted embeddings instead; the two are not
interchangeable on an existing table since the vector column's dimension
is fixed at table-creation time (384 for the local model, 1536 for
`text-embedding-3-small`) - switching providers on a table that already has
rows needs a re-ingest, not just a config change.
"""

import os
from typing import Protocol


class Embedder(Protocol):
    """Structural shape `PgVector` actually requires - see module docstring."""

    dimensions: int

    def get_embedding(self, text: str) -> list[float]: ...


def build_embedder(provider: str | None = None) -> Embedder:
    provider = (provider or os.environ.get("RAG_EMBEDDER_PROVIDER", "local")).lower()

    if provider == "local":
        from agno.knowledge.embedder.sentence_transformer import SentenceTransformerEmbedder

        model = os.environ.get("RAG_EMBEDDER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        return SentenceTransformerEmbedder(id=model)

    if provider == "openai":
        from agno.knowledge.embedder.openai import OpenAIEmbedder

        model = os.environ.get("RAG_EMBEDDER_MODEL", "text-embedding-3-small")
        return OpenAIEmbedder(id=model)

    raise ValueError(f"Unknown RAG_EMBEDDER_PROVIDER: {provider!r} (use 'local' or 'openai')")
