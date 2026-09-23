"""Integration coverage for rag/embeddings.py and rag/store.py against the
real local Postgres/pgvector instance and a real (local, no API key)
sentence-transformers model - the two things test_rag.py's unit tests
can't exercise.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://educa:educa@localhost:55432/educa")
sys.path.insert(0, str(Path(__file__).parents[2]))

from rag.domain import Chunk
from rag.embeddings import build_embedder
from rag.store import AgnoPgVectorStore


@pytest.mark.integration
def test_build_embedder_local_provider_is_the_default_and_produces_384_dim_vectors():
    embedder = build_embedder()  # no provider given -> RAG_EMBEDDER_PROVIDER default ("local")

    assert embedder.dimensions == 384
    vector = embedder.get_embedding("On Sunday, Tom gets up at 10 o'clock.")
    assert len(vector) == 384
    assert all(isinstance(value, float) for value in vector)


@pytest.mark.integration
def test_store_add_and_search_round_trips_with_the_local_embedder():
    table_name = "rag_chunks_test_local_embedder"
    store = AgnoPgVectorStore(table_name=table_name, embedder=build_embedder("local"))
    try:
        chunks = [
            Chunk(
                content="Tom gets up at 10 o'clock on Sunday and reads the newspaper.",
                organization_id="org-test",
                course_id="course-test",
                document_id="doc-test",
                section_title="Tom's Day",
                chunk_index=0,
                page_number=1,
                metadata={"document_title": "Practice Reading"},
            ),
            Chunk(
                content="The hotel receptionist asks for a signature and gives the guest a room key.",
                organization_id="org-test",
                course_id="course-test",
                document_id="doc-test",
                section_title="Hotel Dialogue",
                chunk_index=1,
                page_number=2,
                metadata={"document_title": "Practice Reading"},
            ),
        ]

        store.add(chunks)
        results = store.search("What time does Tom wake up?", "org-test", "course-test", limit=1)

        assert len(results) == 1
        assert results[0].meta_data["section_title"] == "Tom's Day"
    finally:
        store.vector_db.drop()


@pytest.mark.integration
def test_store_search_filters_by_course_id():
    table_name = "rag_chunks_test_course_filter"
    store = AgnoPgVectorStore(table_name=table_name, embedder=build_embedder("local"))
    try:
        store.add(
            [
                Chunk(
                    content="Tom gets up at 10 o'clock on Sunday.",
                    organization_id="org-test",
                    course_id="course-a",
                    document_id="doc-a",
                    section_title="Tom's Day",
                    chunk_index=0,
                    metadata={"document_title": "Practice Reading"},
                )
            ]
        )

        same_course = store.search("Tom's morning routine", "org-test", "course-a", limit=5)
        other_course = store.search("Tom's morning routine", "org-test", "course-b", limit=5)

        assert len(same_course) == 1
        assert other_course == []
    finally:
        store.vector_db.drop()
