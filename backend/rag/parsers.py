"""Format-specific parsing behind one replaceable interface."""

import io
from pathlib import Path
from typing import Protocol

from .domain import ParsedDocument, ParsedSection


class DocumentParser(Protocol):
    def parse(self, filename: str, content: bytes) -> ParsedDocument:
        """Parse bytes into a structured document."""


class TextDocumentParser:
    def parse(self, filename: str, content: bytes) -> ParsedDocument:
        text = content.decode("utf-8")
        title = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
        sections: list[ParsedSection] = []
        current_title = title or "Untitled document"
        current_lines: list[str] = []

        def flush() -> None:
            body = "\n".join(current_lines).strip()
            if body:
                sections.append(ParsedSection(current_title, body))

        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                flush()
                current_lines.clear()
                current_title = stripped.lstrip("#").strip() or current_title
            else:
                current_lines.append(line)
        flush()
        if not sections and text.strip():
            sections.append(ParsedSection(title or "Untitled document", text.strip()))
        return ParsedDocument(title or "Untitled document", sections)


class PdfDocumentParser:
    def parse(self, filename: str, content: bytes) -> ParsedDocument:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        title = Path(filename).stem.replace("_", " ").replace("-", " ").strip() or "Untitled document"
        sections = [
            ParsedSection(
                title=f"Page {page_number}",
                content=(page.extract_text() or "").strip(),
                page_start=page_number,
                page_end=page_number,
            )
            for page_number, page in enumerate(reader.pages, start=1)
            if (page.extract_text() or "").strip()
        ]
        return ParsedDocument(title, sections)


def parser_for(filename: str) -> DocumentParser:
    extension = Path(filename).suffix.lower()
    if extension == ".pdf":
        return PdfDocumentParser()
    if extension in {".txt", ".md"}:
        return TextDocumentParser()
    raise ValueError(f"Unsupported file type: {extension or '?'} (use PDF, TXT, or Markdown)")