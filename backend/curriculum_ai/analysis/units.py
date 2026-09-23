"""Split a PDF into chapter-sized "units" for the faculty panel to read.

`rag/parsers.py`'s PDF parser emits one section per page, which is the
right grain for retrieval but the wrong one for a professor-style breakdown
of a textbook: the panel needs a whole chapter in view to tell a concept
from a passing mention. This module does that segmentation
deterministically -- no LLM -- in decreasing order of reliability:

1. the PDF's own bookmarks/outline (top level),
2. "Chapter N" / "Unit N" / ... headings at the top of a page,
3. fixed page windows, so an unstructured PDF still gets analyzed.

Any unit over the size caps is then split on page boundaries so one prompt
stays within a sane context. Scanned PDFs have no extractable text and come
out as zero units -- the caller reports that rather than silently
succeeding with nothing.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

MIN_UNIT_CHARS = 400  # skips near-empty units: title pages, blank dividers, lone TOC pages
WINDOW_PAGES = 10
MAX_UNIT_PAGES = 30
MAX_UNIT_CHARS = 80_000

_HEADING_RE = re.compile(
    r"^(chapter|unit|module|lesson|part)\s+([0-9]+|[ivxlc]+)\b[\s.:\-–—]*(.*)$", re.IGNORECASE
)
_HEADING_LOOKAHEAD_LINES = 5
_PAGE_MARKER_RE = re.compile(r"^\[page \d+\]\n", re.MULTILINE)


@dataclass(frozen=True)
class Unit:
    title: str
    page_start: int  # 1-based, inclusive
    page_end: int
    text: str  # each page prefixed with a "[page N]" marker so agents can cite

    @property
    def plain_text(self) -> str:
        """The text without page markers -- what a quote is checked against."""
        return _PAGE_MARKER_RE.sub("", self.text)


def _render(page_texts: list[str], start: int, end: int) -> str:
    return "\n\n".join(f"[page {n}]\n{page_texts[n - 1].strip()}" for n in range(start, end + 1))


def _heading_starts(page_texts: list[str]) -> list[tuple[str, int]]:
    starts: list[tuple[str, int]] = []
    for page_number, text in enumerate(page_texts, start=1):
        lines = [line.strip() for line in text.splitlines() if line.strip()][:_HEADING_LOOKAHEAD_LINES]
        for index, line in enumerate(lines):
            match = _HEADING_RE.match(line)
            if not match:
                continue
            # "Chapter 3" alone on a line is common; the title is usually the next line.
            title = line if match.group(3) or index + 1 >= len(lines) else f"{line}: {lines[index + 1]}"
            starts.append((title, page_number))
            break
    return starts


def _outline_starts(reader) -> list[tuple[str, int]]:
    """Top-level bookmarks as (title, 1-based page). Empty if the PDF has no
    usable outline. Nested lists in pypdf's outline are children of the
    preceding destination, so skipping them keeps only the top level."""
    try:
        outline = reader.outline
    except Exception:  # noqa: BLE001 - a malformed outline just means "no outline"
        return []
    starts: list[tuple[str, int]] = []
    for item in outline:
        if isinstance(item, list):
            continue
        try:
            page_number = reader.get_destination_page_number(item) + 1
        except Exception:  # noqa: BLE001
            continue
        title = str(getattr(item, "title", "") or "").strip()
        if title and page_number >= 1:
            starts.append((title, page_number))
    return starts


def _units_from_starts(page_texts: list[str], starts: list[tuple[str, int]]) -> list[Unit]:
    total = len(page_texts)
    # Same page bookmarked twice keeps the first title; order by page.
    by_page: dict[int, str] = {}
    for title, page in sorted(starts, key=lambda s: s[1]):
        if 1 <= page <= total:
            by_page.setdefault(page, title)
    ordered = sorted(by_page.items())
    if ordered and ordered[0][0] > 1:
        ordered.insert(0, (1, "Front matter"))

    units: list[Unit] = []
    for index, (page, title) in enumerate(ordered):
        end = ordered[index + 1][0] - 1 if index + 1 < len(ordered) else total
        units.append(Unit(title=title, page_start=page, page_end=end, text=_render(page_texts, page, end)))
    return units


def _windows(page_texts: list[str]) -> list[Unit]:
    units: list[Unit] = []
    for start in range(1, len(page_texts) + 1, WINDOW_PAGES):
        end = min(start + WINDOW_PAGES - 1, len(page_texts))
        units.append(Unit(f"Pages {start}–{end}", start, end, _render(page_texts, start, end)))
    return units


def _split_oversized(page_texts: list[str], unit: Unit) -> list[Unit]:
    pages = unit.page_end - unit.page_start + 1
    if pages <= MAX_UNIT_PAGES and len(unit.text) <= MAX_UNIT_CHARS:
        return [unit]

    parts: list[Unit] = []
    start = unit.page_start
    while start <= unit.page_end:
        end, chars = start, len(page_texts[start - 1])
        while end < unit.page_end and end - start + 1 < MAX_UNIT_PAGES and chars + len(page_texts[end]) <= MAX_UNIT_CHARS:
            end += 1
            chars += len(page_texts[end - 1])
        parts.append(Unit(f"{unit.title} (part {len(parts) + 1})", start, end, _render(page_texts, start, end)))
        start = end + 1
    return parts


def plan_units(page_texts: list[str], outline_starts: list[tuple[str, int]] | None = None) -> list[Unit]:
    """Pure segmentation over already-extracted page text -- the part worth
    unit-testing without a PDF."""
    if not any(text.strip() for text in page_texts):
        return []

    for starts in (outline_starts or [], _heading_starts(page_texts)):
        if len({page for _, page in starts}) >= 2:
            units = _units_from_starts(page_texts, starts)
            break
    else:
        units = _windows(page_texts)

    sized = [unit for unit in units if len(unit.plain_text.strip()) >= MIN_UNIT_CHARS]
    return [part for unit in sized for part in _split_oversized(page_texts, unit)]


def units_from_pdf(content: bytes) -> list[Unit]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    page_texts = [(page.extract_text() or "") for page in reader.pages]
    return plan_units(page_texts, _outline_starts(reader))
