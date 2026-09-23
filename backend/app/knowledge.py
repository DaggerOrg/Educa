"""Enterprise RAG store for uploaded course materials (textbooks, faculty
curricula), backed by Agno's own `Knowledge`/`PgVector` primitives rather
than a hand-rolled index.

Uploading is a plain, immediately-effective operation -- like editing a
lesson (`PATCH /api/lessons/{id}`), not like the four course-mutating
agent tools spread across `agents/curriculum`, `agents/lesson_content`,
and `agents/quiz`. A reference document isn't a creative AI action that
needs a teacher's sign-off; it becomes searchable the moment it's
uploaded. What's agentic is what happens with it afterwards:
`materials_agent` (`agents/materials/agent.py`) decides on its own when to
call the auto-generated `search_knowledge_base` tool while drafting.

`vector_db.create()` runs at import time and fails loudly if Postgres
isn't reachable -- this app now genuinely depends on it, same as it
depends on a Gemini API key being set (see `agents/models.py`).
"""
import hashlib
import io
import os

from agno.knowledge.document.base import Document
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.pdf_reader import PDFReader
from agno.knowledge.reader.text_reader import TextReader
from agno.vectordb.pgvector import PgVector
from agno.vectordb.search import SearchType

from rag.embeddings import build_embedder
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select

MAX_UPLOAD_BYTES = 20 * 1024 * 1024

# Same embedder selection as rag/store.py (RAG_EMBEDDER_PROVIDER, "local" by
# default) - no API key/billing needed. See rag/README.md; the two vector
# stores are otherwise independent (different tables, different feature).
vector_db = PgVector(
    table_name="course_materials",
    db_url=os.environ["DATABASE_URL"],
    embedder=build_embedder(),
    search_type=SearchType.hybrid,  # blends vector similarity with Postgres full-text
)
vector_db.create()

knowledge = Knowledge(vector_db=vector_db, max_results=5)


def _read(filename: str, content: bytes) -> list[Document]:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        return PDFReader().read(io.BytesIO(content), name=filename)
    if ext in ("txt", "md"):
        return TextReader().read(io.BytesIO(content), name=filename)
    raise ValueError(f"Unsupported file type: .{ext or '?'} (upload a .pdf, .txt, or .md)")


def add_material(filename: str, content: bytes) -> dict:
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("File too large (max 20MB)")
    docs = _read(filename, content)
    if not docs or not any(d.content.strip() for d in docs):
        raise ValueError("No readable text found in this file -- if it's a scanned PDF, it needs OCR first")
    content_hash = hashlib.sha256(content).hexdigest()
    vector_db.upsert(content_hash=content_hash, documents=docs)
    return {
        "id": content_hash,
        "filename": filename,
        "chunkCount": len(docs),
        "charCount": sum(len(d.content) for d in docs),
    }


def list_materials() -> list[dict]:
    table = vector_db.table
    stmt = (
        select(
            table.c.content_hash,
            func.max(table.c.name).label("name"),
            func.count().label("chunk_count"),
            func.sum(func.length(table.c.content)).label("char_count"),
        )
        .group_by(table.c.content_hash)
        .order_by(func.max(table.c.created_at))
    )
    with vector_db.Session() as sess:
        rows = sess.execute(stmt).all()
    return [
        {"id": r.content_hash, "filename": r.name, "chunkCount": r.chunk_count, "charCount": int(r.char_count or 0)}
        for r in rows
    ]


def delete_material(material_id: str) -> bool:
    with vector_db.Session() as sess:
        result = sess.execute(sa_delete(vector_db.table).where(vector_db.table.c.content_hash == material_id))
        sess.commit()
        return result.rowcount > 0
