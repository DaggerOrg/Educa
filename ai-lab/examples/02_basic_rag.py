"""End-to-end RAG: chunk + embed the sample docs into Chroma via LlamaIndex,
retrieve the most relevant chunks for a question, then ask Claude to answer
using only that retrieved context.

Requires ANTHROPIC_API_KEY (or `ant auth login`) for the generation step.
Run: python examples/02_basic_rag.py
"""

from ai_lab.rag import answer, build_index

QUESTION = "How does RAG reduce hallucination, and how can it be combined with a graph?"


def main():
    print("Building index from data/sample_docs ...")
    index = build_index()

    print(f"\nQuestion: {QUESTION}\n")
    print(answer(QUESTION, index))


if __name__ == "__main__":
    main()
