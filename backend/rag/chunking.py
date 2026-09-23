"""Replaceable, section-aware chunking strategy."""

from .domain import Chunk, ParsedDocument


class SectionChunker:
    def __init__(self, target_characters: int = 3200, overlap_characters: int = 400):
        if target_characters <= overlap_characters:
            raise ValueError("target_characters must be greater than overlap_characters")
        self.target_characters = target_characters
        self.overlap_characters = overlap_characters

    def chunk(
        self,
        document: ParsedDocument,
        organization_id: str,
        document_id: str,
        course_id: str | None = None,
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        for section in document.sections:
            text = " ".join(section.content.split())
            start = 0
            while start < len(text):
                end = min(start + self.target_characters, len(text))
                if end < len(text):
                    boundary = text.rfind(" ", start, end)
                    if boundary > start:
                        end = boundary
                content = text[start:end].strip()
                if content:
                    chunks.append(
                        Chunk(
                            content=content,
                            organization_id=organization_id,
                            course_id=course_id,
                            document_id=document_id,
                            section_title=section.title,
                            chunk_index=len(chunks),
                            page_number=section.page_start,
                            metadata={"section_level": section.level, "document_title": document.title},
                        )
                    )
                if end >= len(text):
                    break
                start = max(start + 1, end - self.overlap_characters)
        return chunks