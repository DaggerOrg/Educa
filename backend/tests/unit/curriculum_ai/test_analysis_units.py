"""Chapter segmentation and quote grounding -- pure functions, no DB/queue."""

import io
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://educa:educa@localhost:55432/educa")
sys.path.insert(0, str(Path(__file__).parents[3]))

from curriculum_ai.analysis import units as units_module  # noqa: E402
from curriculum_ai.analysis.grounding import is_grounded  # noqa: E402
from curriculum_ai.analysis.units import plan_units, units_from_pdf  # noqa: E402

BODY = "lorem ipsum dolor " * 40  # ~700 chars, comfortably over MIN_UNIT_CHARS


@pytest.mark.unit
def test_splits_on_chapter_headings_and_joins_a_lone_number_with_the_next_line():
    pages = [f"Chapter {i // 4 + 1}\nTitle {i // 4 + 1}\n{BODY}" if i % 4 == 0 else BODY for i in range(12)]
    units = plan_units(pages)
    assert [(u.title, u.page_start, u.page_end) for u in units] == [
        ("Chapter 1: Title 1", 1, 4),
        ("Chapter 2: Title 2", 5, 8),
        ("Chapter 3: Title 3", 9, 12),
    ]


@pytest.mark.unit
def test_outline_beats_headings_and_leading_pages_become_front_matter():
    pages = [f"Chapter {i}\n{BODY}" for i in range(1, 11)]
    units = plan_units(pages, outline_starts=[("Basics", 3), ("Advanced", 7)])
    assert [(u.title, u.page_start, u.page_end) for u in units] == [
        ("Front matter", 1, 2),
        ("Basics", 3, 6),
        ("Advanced", 7, 10),
    ]


@pytest.mark.unit
def test_unstructured_text_falls_back_to_page_windows():
    units = plan_units([BODY] * 25)
    assert [(u.page_start, u.page_end) for u in units] == [(1, 10), (11, 20), (21, 25)]


@pytest.mark.unit
def test_oversized_unit_is_split_on_page_boundaries_without_gaps():
    units = plan_units([BODY] * 40, outline_starts=[("Big", 1), ("Tail", 41)])
    assert [(u.title, u.page_start, u.page_end) for u in units] == [
        ("Big (part 1)", 1, units_module.MAX_UNIT_PAGES),
        ("Big (part 2)", units_module.MAX_UNIT_PAGES + 1, 40),
    ]


@pytest.mark.unit
def test_tiny_units_are_dropped():
    pages = [BODY] * 4 + ["Chapter 2"] + [BODY] * 4
    units = plan_units(pages, outline_starts=[("Ch1", 1), ("Blank divider", 5), ("Ch2", 6)])
    assert [u.title for u in units] == ["Ch1", "Ch2"]


@pytest.mark.unit
def test_pages_are_marked_so_agents_can_cite_and_plain_text_strips_them():
    (unit,) = plan_units(["alpha " * 100, "beta " * 100], outline_starts=[])
    assert "[page 1]\nalpha" in unit.text and "[page 2]\nbeta" in unit.text
    assert "[page" not in unit.plain_text


@pytest.mark.unit
def test_no_extractable_text_yields_no_units():
    assert plan_units(["", "  \n"]) == []


@pytest.mark.unit
def test_reads_top_level_bookmarks_from_a_real_pdf():
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(6):
        writer.add_blank_page(200, 200)
    writer.add_outline_item("Intro", 0)
    child = writer.add_outline_item("Nested", 1)  # parent of the next line; only top level counts
    writer.add_outline_item("Deep", 1, parent=child)
    writer.add_outline_item("Second", 3)
    buffer = io.BytesIO()
    writer.write(buffer)

    from pypdf import PdfReader

    starts = units_module._outline_starts(PdfReader(io.BytesIO(buffer.getvalue())))
    assert starts == [("Intro", 1), ("Nested", 2), ("Second", 4)]
    assert units_from_pdf(buffer.getvalue()) == []  # blank pages: nothing to analyze


@pytest.mark.unit
@pytest.mark.parametrize(
    "quote, expected",
    [
        ("the rate of change of velocity", True),
        ("The  rate of change\nof velocity", True),  # whitespace/line-break differences
        ("Rate of change of veloc-\nity is called acceleration", True),  # hyphenation across a line break
        ("first-order ﬁnite difference", True),  # ligature in the source
        ("velocity never changes at all", False),  # a paraphrase, not in the text
        ("velocity", False),  # too short to mean anything
        ("", False),
    ],
)
def test_grounding(quote, expected):
    source = (
        "Acceleration is the rate of change of velocity. Rate of change of velocity is called "
        "acceleration. A first-order ﬁnite difference approximates it."
    )
    assert is_grounded(quote, source) is expected
