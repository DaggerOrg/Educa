# Educa RAG foundation

This package is the first incremental RAG slice. It keeps parsing, section-aware
chunking, and the application service independent from FastAPI and Agno. The
`AgnoPgVectorStore` adapter uses Agno's `PgVector` with hybrid search and
applies organization/course metadata filters on every search.

Embeddings default to a local `sentence-transformers` model
(`rag/embeddings.py`, `RAG_EMBEDDER_PROVIDER=local`) - no API key or billing
needed. Set `RAG_EMBEDDER_PROVIDER=openai` (with a funded `OPENAI_API_KEY`)
to use OpenAI's hosted embeddings instead. The two aren't interchangeable on
a table that already has rows - the vector column's dimension (384 local,
1536 OpenAI) is fixed at table-creation time, so switching providers means
re-ingesting, not just changing the env var.

Example wiring:

```python
from rag.service import DocumentService
from rag.store import AgnoPgVectorStore

service = DocumentService(AgnoPgVectorStore())
service.ingest("chapter.pdf", data, "org-1", "doc-1", "course-1")
results = service.search("What is slip?", "org-1", "course-1")
```

The existing `app/materials/` API remains unchanged until this package is
connected to tenant-aware document records in a later phase.