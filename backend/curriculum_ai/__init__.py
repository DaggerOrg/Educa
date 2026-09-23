"""Document ingestion foundation for Educa's curriculum pipeline.

Phase 1 of docs/architecture/educa-ai-architecture.md: upload -> validate
-> store original bytes in object storage -> background parse -> store a
normalized parsed representation. No embeddings, no concept extraction, no
curriculum generation yet -- see the architecture doc for the full roadmap.
"""
