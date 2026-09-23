"""Production vector backend: Postgres + the `pgvector` extension.

Not exercised by the automated test suite (there is no Postgres instance in
this environment) - `ChromaVectorRepository` is. Point `CKE_POSTGRES_DSN`
at a real instance (e.g. `docker compose up postgres`, see
../../../docker-compose.yml) to use it; both classes satisfy the same
`VectorRepository` interface so no service code needs to change.

`table_name` is only ever set from `Settings` (operator-controlled
configuration, never end-user input), so it is safe to interpolate directly
into DDL/DML - there is no user-facing path that can set it.
"""

from __future__ import annotations

import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

from cke.domain.models import KnowledgeChunk
from cke.logging_config import get_logger
from cke.repositories.interfaces import VectorRepository

logger = get_logger(__name__)


class PgVectorRepository(VectorRepository):
    def __init__(
        self, dsn: str, table_name: str, embedding_dim: int, embedding_model_name: str
    ):
        self._dsn = dsn
        self._table = table_name
        self._embedder = SentenceTransformer(embedding_model_name)
        self._ensure_schema(embedding_dim)

    def _connect(self) -> psycopg.Connection:
        conn = psycopg.connect(self._dsn, autocommit=True)
        register_vector(conn)
        return conn

    def _ensure_schema(self, embedding_dim: int) -> None:
        with self._connect() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table} (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    lesson_id TEXT NOT NULL,
                    lesson_title TEXT NOT NULL,
                    module_id TEXT NOT NULL,
                    course_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    concept_ids TEXT NOT NULL DEFAULT '',
                    embedding vector({embedding_dim}) NOT NULL
                )
                """
            )
            conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS {self._table}_embedding_hnsw_idx
                ON {self._table} USING hnsw (embedding vector_cosine_ops)
                """
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS {self._table}_course_id_idx "
                f"ON {self._table} (course_id)"
            )
        logger.info("PgVectorRepository schema ready: table=%s dim=%d", self._table, embedding_dim)

    def _embed(self, texts: list[str]):
        return self._embedder.encode(list(texts), normalize_embeddings=True)

    def upsert_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        if not chunks:
            return
        embeddings = self._embed([chunk.text for chunk in chunks])
        sql = f"""
            INSERT INTO {self._table}
                (id, text, lesson_id, lesson_title, module_id, course_id, chunk_index, concept_ids, embedding)
            VALUES (%(id)s, %(text)s, %(lesson_id)s, %(lesson_title)s, %(module_id)s,
                    %(course_id)s, %(chunk_index)s, %(concept_ids)s, %(embedding)s)
            ON CONFLICT (id) DO UPDATE SET
                text = EXCLUDED.text,
                lesson_id = EXCLUDED.lesson_id,
                lesson_title = EXCLUDED.lesson_title,
                module_id = EXCLUDED.module_id,
                course_id = EXCLUDED.course_id,
                chunk_index = EXCLUDED.chunk_index,
                concept_ids = EXCLUDED.concept_ids,
                embedding = EXCLUDED.embedding
        """
        with self._connect() as conn:
            with conn.cursor() as cursor:
                for chunk, embedding in zip(chunks, embeddings):
                    cursor.execute(
                        sql,
                        {
                            "id": chunk.id,
                            "text": chunk.text,
                            "lesson_id": chunk.lesson_id,
                            "lesson_title": chunk.lesson_title,
                            "module_id": chunk.module_id,
                            "course_id": chunk.course_id,
                            "chunk_index": chunk.chunk_index,
                            "concept_ids": ",".join(chunk.concept_ids),
                            "embedding": embedding,
                        },
                    )
        logger.info("Upserted %d chunks into pgvector table %s", len(chunks), self._table)

    def similarity_search(
        self, query: str, *, top_k: int = 5, course_id: str | None = None
    ) -> list[tuple[KnowledgeChunk, float]]:
        query_embedding = self._embed([query])[0]
        params: dict = {"embedding": query_embedding, "top_k": top_k}
        course_filter = ""
        if course_id:
            course_filter = "AND course_id = %(course_id)s"
            params["course_id"] = course_id

        sql = f"""
            SELECT id, text, lesson_id, lesson_title, module_id, course_id, chunk_index, concept_ids,
                   1 - (embedding <=> %(embedding)s) AS similarity
            FROM {self._table}
            WHERE TRUE {course_filter}
            ORDER BY embedding <=> %(embedding)s
            LIMIT %(top_k)s
        """
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        matches: list[tuple[KnowledgeChunk, float]] = []
        for row in rows:
            (
                chunk_id, text, lesson_id, lesson_title, module_id,
                row_course_id, chunk_index, concept_ids, similarity,
            ) = row
            chunk = KnowledgeChunk(
                id=chunk_id,
                text=text,
                lesson_id=lesson_id,
                lesson_title=lesson_title,
                module_id=module_id,
                course_id=row_course_id,
                chunk_index=chunk_index,
                concept_ids=[c for c in concept_ids.split(",") if c],
            )
            matches.append((chunk, max(0.0, min(1.0, float(similarity)))))
        return matches

    def delete_by_course(self, course_id: str) -> None:
        with self._connect() as conn:
            conn.execute(f"DELETE FROM {self._table} WHERE course_id = %s", (course_id,))

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(f"SELECT COUNT(*) FROM {self._table}").fetchone()
        return row[0] if row else 0
