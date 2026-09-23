"""Fixed-size, word-count chunking with overlap - the standard first-pass
RAG chunking strategy. Lesson content here is short-to-medium prose (not
huge documents), so a simple sliding window over whitespace-split words is
both correct and easy to reason about; there's no need for a tokenizer-
aware splitter at this scale.
"""

from __future__ import annotations

from cke.domain.models import KnowledgeChunk, Lesson

DEFAULT_CHUNK_SIZE_WORDS = 120
DEFAULT_OVERLAP_WORDS = 20


def chunk_text(
    text: str,
    *,
    chunk_size_words: int = DEFAULT_CHUNK_SIZE_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> list[str]:
    if chunk_size_words <= 0:
        raise ValueError("chunk_size_words must be positive")
    if overlap_words < 0 or overlap_words >= chunk_size_words:
        raise ValueError("overlap_words must be >= 0 and < chunk_size_words")

    words = text.split()
    if not words:
        return []

    stride = chunk_size_words - overlap_words
    chunks: list[str] = []
    start = 0
    while start < len(words):
        window = words[start : start + chunk_size_words]
        chunks.append(" ".join(window))
        if start + chunk_size_words >= len(words):
            break
        start += stride
    return chunks


def chunk_lesson(
    lesson: Lesson,
    *,
    course_id: str,
    chunk_size_words: int = DEFAULT_CHUNK_SIZE_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> list[KnowledgeChunk]:
    texts = chunk_text(
        lesson.content, chunk_size_words=chunk_size_words, overlap_words=overlap_words
    )
    return [
        KnowledgeChunk(
            id=f"{lesson.id}::chunk-{index}",
            text=text,
            lesson_id=lesson.id,
            lesson_title=lesson.title,
            module_id=lesson.module_id,
            course_id=course_id,
            chunk_index=index,
            concept_ids=list(lesson.concept_ids),
        )
        for index, text in enumerate(texts)
    ]
