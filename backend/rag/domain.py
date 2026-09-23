"""Small domain models shared by ingestion and retrieval."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ParsedSection:
    title: str
    content: str
    level: int = 1
    page_start: int | None = None
    page_end: int | None = None


@dataclass(frozen=True)
class ParsedDocument:
    title: str
    sections: list[ParsedSection]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    content: str
    organization_id: str
    course_id: str | None
    document_id: str
    section_title: str
    chunk_index: int
    page_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)