"""Vector search 101: embed a few sentences into Chroma and run a similarity
search. No Claude API key needed - Chroma's bundled default embedding
model runs locally.

Run: python examples/01_vector_search.py
"""

from ai_lab.vector_store import add_texts, similarity_search

SENTENCES = [
    "Transformers use self-attention to process a whole sequence in parallel.",
    "A vector database finds the nearest neighbors to a query embedding.",
    "Chroma is a local, open-source embedding database good for prototyping.",
    "A knowledge graph represents entities as nodes and relationships as edges.",
    "NetworkX is a Python library for building and analyzing graphs in memory.",
]

TOPICS = ["transformers", "vectors", "vectors", "graphs", "graphs"]


def main():
    add_texts(SENTENCES, metadatas=[{"topic": t} for t in TOPICS])

    query = "How do I search for similar text with embeddings?"
    print(f"Query: {query!r}\n")

    results = similarity_search(query, top_k=2)
    for doc, distance in zip(results["documents"][0], results["distances"][0]):
        print(f"  (distance={distance:.4f}) {doc}")

    print("\nSame query, filtered to topic='graphs':\n")
    filtered = similarity_search(query, top_k=2, where={"topic": "graphs"})
    for doc, distance in zip(filtered["documents"][0], filtered["distances"][0]):
        print(f"  (distance={distance:.4f}) {doc}")


if __name__ == "__main__":
    main()
