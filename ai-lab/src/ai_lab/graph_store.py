"""A small in-memory knowledge graph over the same concepts as the sample
docs, built with NetworkX - nodes are concepts, edges are labeled
relationships.
"""

import networkx as nx

CONCEPT_EDGES = [
    ("Transformer", "Self-Attention", "uses"),
    ("Self-Attention", "Attention Weights", "computes"),
    ("RAG", "Vector Database", "depends on"),
    ("RAG", "LLM", "depends on"),
    ("RAG", "Knowledge Graph", "can combine with"),
    ("GraphRAG", "RAG", "extends"),
    ("GraphRAG", "Knowledge Graph", "depends on"),
    ("Vector Database", "Embeddings", "stores"),
    ("Embeddings", "Transformer", "produced by"),
    ("Chroma", "Vector Database", "is a"),
    ("Neo4j", "Knowledge Graph", "is a"),
    ("NetworkX", "Knowledge Graph", "is a"),
    ("LLM", "Transformer", "is built from"),
]


def build_concept_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    for source, target, relation in CONCEPT_EDGES:
        graph.add_edge(source, target, relation=relation)
    return graph


def describe_neighbors(graph: nx.DiGraph, concept: str) -> list[str]:
    """Human-readable outgoing relationships for one concept."""
    return [
        f"{concept} --{data['relation']}--> {target}"
        for target, data in graph[concept].items()
    ]


def most_central_concepts(graph: nx.DiGraph, top_n: int = 5) -> list[tuple[str, float]]:
    scores = nx.degree_centrality(graph)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_n]


def graph_context(graph: nx.DiGraph, concept: str) -> str:
    """Flatten a concept's neighborhood into text, for feeding to an LLM."""
    if concept not in graph:
        return f"No graph data for '{concept}'."
    lines = describe_neighbors(graph, concept)
    lines += [
        f"{source} --{data['relation']}--> {concept}"
        for source, _, data in graph.in_edges(concept, data=True)
    ]
    return "\n".join(lines) if lines else f"'{concept}' has no known relationships."
