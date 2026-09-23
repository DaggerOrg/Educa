"""Knowledge graph 101: build a small concept graph with NetworkX and query
it - direct relationships, multi-hop paths, and the most-connected nodes.

No API key needed.
Run: python examples/03_knowledge_graph.py
"""

import networkx as nx

from ai_lab.graph_store import build_concept_graph, describe_neighbors, most_central_concepts


def main():
    graph = build_concept_graph()
    print(f"Graph has {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges.\n")

    print("Direct relationships for 'RAG':")
    for line in describe_neighbors(graph, "RAG"):
        print(f"  {line}")

    print("\nMulti-hop path from 'GraphRAG' to 'Embeddings':")
    path = nx.shortest_path(graph, source="GraphRAG", target="Embeddings")
    print("  " + " -> ".join(path))

    print("\nMost-connected concepts (degree centrality):")
    for concept, score in most_central_concepts(graph):
        print(f"  {concept}: {score:.3f}")


if __name__ == "__main__":
    main()
