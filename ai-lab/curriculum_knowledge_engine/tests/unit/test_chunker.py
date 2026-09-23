import pytest

from cke.domain.models import Lesson
from cke.ingestion.chunker import chunk_lesson, chunk_text


def test_chunk_text_empty_input_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_shorter_than_window_returns_one_chunk():
    text = "one two three four five"
    chunks = chunk_text(text, chunk_size_words=10, overlap_words=2)
    assert chunks == [text]


def test_chunk_text_respects_window_size():
    words = [f"w{i}" for i in range(25)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size_words=10, overlap_words=3)
    for chunk in chunks[:-1]:
        assert len(chunk.split()) == 10
    assert len(chunks[-1].split()) <= 10


def test_chunk_text_overlap_shares_words_between_consecutive_chunks():
    words = [f"w{i}" for i in range(25)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size_words=10, overlap_words=3)

    first_tail = chunks[0].split()[-3:]
    second_head = chunks[1].split()[:3]
    assert first_tail == second_head


def test_chunk_text_covers_every_word_at_least_once():
    words = [f"w{i}" for i in range(37)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size_words=10, overlap_words=2)

    covered = set()
    for chunk in chunks:
        covered.update(chunk.split())
    assert covered == set(words)


@pytest.mark.parametrize(
    "chunk_size_words,overlap_words",
    [(0, 0), (-5, 0), (10, 10), (10, 15)],
)
def test_chunk_text_rejects_invalid_window_parameters(chunk_size_words, overlap_words):
    with pytest.raises(ValueError):
        chunk_text("some text here", chunk_size_words=chunk_size_words, overlap_words=overlap_words)


def test_chunk_lesson_produces_chunks_with_lesson_metadata():
    lesson = Lesson(
        id="lesson-1",
        module_id="module-1",
        title="Test Lesson",
        content=" ".join(f"word{i}" for i in range(150)),
        concept_ids=["foundations"],
    )
    chunks = chunk_lesson(lesson, course_id="course-1", chunk_size_words=50, overlap_words=10)

    assert len(chunks) > 1
    for index, chunk in enumerate(chunks):
        assert chunk.lesson_id == "lesson-1"
        assert chunk.lesson_title == "Test Lesson"
        assert chunk.module_id == "module-1"
        assert chunk.course_id == "course-1"
        assert chunk.chunk_index == index
        assert chunk.concept_ids == ["foundations"]
        assert chunk.id == f"lesson-1::chunk-{index}"
