"""Independent document RAG foundation for Educa.

The package keeps ingestion and retrieval reusable without requiring an
Agno agent. Agno is used only by the infrastructure adapter in ``store``.
"""

from .chunking import SectionChunker
from .domain import Chunk, ParsedDocument, ParsedSection
from .service import DocumentService

__all__ = ["Chunk", "DocumentService", "ParsedDocument", "ParsedSection", "SectionChunker"]