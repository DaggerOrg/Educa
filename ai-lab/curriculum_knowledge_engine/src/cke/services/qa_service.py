from __future__ import annotations

from cke.domain.models import AnswerResult
from cke.llm.claude_client import ClaudeClient
from cke.logging_config import get_logger
from cke.retrieval.hybrid_retriever import HybridRetriever

logger = get_logger(__name__)

_QA_SYSTEM_PROMPT = """\
You are the curriculum assistant for an AI engineering course. Answer the \
learner's question using ONLY the retrieved lesson excerpts and concept \
relationships provided to you - never rely on outside knowledge, even if \
you're confident about it. Cite excerpts by their bracketed number, like \
[1] or [1][3]. When the concept relationships mention a prerequisite that \
matters for the answer, say so explicitly. If the provided context does \
not contain enough information to answer, say exactly that instead of \
guessing."""

_NO_CONTEXT_ANSWER = (
    "I don't have any indexed curriculum content relevant to this question yet. "
    "Try ingesting a curriculum first, or rephrase the question."
)


class QAService:
    """Answers a learner's free-text question with a grounded, cited answer
    (RAG), enriched with the concepts' graph relationships (GraphRAG)."""

    def __init__(self, hybrid_retriever: HybridRetriever, claude_client: ClaudeClient):
        self._retriever = hybrid_retriever
        self._claude = claude_client

    def answer(
        self,
        question: str,
        *,
        course_id: str | None = None,
        top_k: int | None = None,
        graph_hops: int = 1,
    ) -> AnswerResult:
        context = self._retriever.retrieve(
            question, top_k=top_k, course_id=course_id, graph_hops=graph_hops
        )

        if context.is_empty:
            logger.info("QA request had no retrievable context: %r", question)
            return AnswerResult(question=question, answer=_NO_CONTEXT_ANSWER)

        prompt = f"{context.to_prompt_block()}\n\nQuestion: {question}"
        answer_text = self._claude.complete(prompt, system=_QA_SYSTEM_PROMPT)

        return AnswerResult(
            question=question,
            answer=answer_text,
            citations=context.citations,
            concepts_referenced=context.concept_ids,
        )
