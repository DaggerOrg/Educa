"""GraphRAG: combine structured context from a NetworkX knowledge graph with
unstructured context from vector retrieval, and hand both to Claude - the
pattern described in data/sample_docs/knowledge_graphs.txt.

Requires ANTHROPIC_API_KEY (or `ant auth login`) for the generation step.
Run: python examples/04_graph_rag.py
"""

from ai_lab.claude import ask_claude
from ai_lab.graph_store import build_concept_graph, graph_context
from ai_lab.rag import build_index, retrieve

CONCEPT = "GraphRAG"
QUESTION = "What is GraphRAG, what does it depend on, and why combine a graph with a vector store?"

SYSTEM_PROMPT = (
    "Answer using ONLY the graph relationships and text chunks given below. "
    "Point out which parts of your answer came from the graph vs. the text."
)


def main():
    graph = build_concept_graph()
    graph_facts = graph_context(graph, CONCEPT)

    print("Building vector index from data/sample_docs ...")
    index = build_index()
    nodes = retrieve(QUESTION, index, top_k=2)
    text_chunks = "\n\n".join(f"[{i + 1}] {n.get_content()}" for i, n in enumerate(nodes))

    prompt = (
        f"Graph relationships for '{CONCEPT}':\n{graph_facts}\n\n"
        f"Retrieved text chunks:\n{text_chunks}\n\n"
        f"Question: {QUESTION}"
    )

    print(f"\nQuestion: {QUESTION}\n")
    print(ask_claude(prompt, system=SYSTEM_PROMPT, max_tokens=1024))


if __name__ == "__main__":
    main()
