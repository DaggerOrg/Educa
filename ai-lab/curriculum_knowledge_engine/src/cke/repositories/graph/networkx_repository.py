"""In-memory graph backend built on NetworkX, with simple JSON persistence.

This is the default `GraphRepository` implementation - no external service
required. Every concept and edge is validated Pydantic data before it ever
touches the graph, so the graph itself only ever needs to store one JSON
blob per node/edge under the key `"data"`; nothing here re-derives domain
fields from raw NetworkX attributes.

Design note: prerequisite semantics only apply to `RelationType.REQUIRES`
edges. Cycle detection, prerequisite chains, and centrality all operate on
the sub-digraph of REQUIRES edges; `RELATES_TO` / `PART_OF` / `EXTENDS`
edges are stored and returned but never constrained to be acyclic - they're
associative, not load-bearing for learning order.
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock

import networkx as nx

from cke.domain.enums import RelationType
from cke.domain.exceptions import CyclicPrerequisiteError, NotFoundError, UnreachableGoalError
from cke.domain.models import Concept, PrerequisiteEdge
from cke.logging_config import get_logger
from cke.repositories.interfaces import GraphRepository

logger = get_logger(__name__)


class NetworkXGraphRepository(GraphRepository):
    def __init__(self, persist_path: Path | None = None):
        self._graph: nx.DiGraph = nx.DiGraph()
        self._persist_path = persist_path
        self._lock = RLock()
        if persist_path is not None and persist_path.exists():
            self.load(persist_path)

    @property
    def persist_path(self) -> Path | None:
        """None means this instance is intentionally in-memory-only (e.g.
        in tests) - callers that auto-persist opportunistically, like
        `CurriculumIngestionService`, check this rather than assuming
        `save()` is always safe to call with no arguments."""
        return self._persist_path

    # --- concepts -----------------------------------------------------

    def upsert_concept(self, concept: Concept) -> None:
        with self._lock:
            self._graph.add_node(concept.id, data=concept.model_dump(mode="json"))

    def get_concept(self, concept_id: str) -> Concept | None:
        node = self._graph.nodes.get(concept_id)
        if node is None:
            return None
        return Concept.model_validate(node["data"])

    def all_concepts(self) -> list[Concept]:
        return [Concept.model_validate(d["data"]) for _, d in self._graph.nodes(data=True)]

    def clear(self) -> None:
        with self._lock:
            self._graph.clear()

    # --- edges ----------------------------------------------------------

    def upsert_edge(self, edge: PrerequisiteEdge) -> None:
        with self._lock:
            if edge.source_id not in self._graph:
                raise NotFoundError("Concept", edge.source_id)
            if edge.target_id not in self._graph:
                raise NotFoundError("Concept", edge.target_id)

            previous = self._graph.get_edge_data(edge.source_id, edge.target_id)
            self._graph.add_edge(
                edge.source_id, edge.target_id, data=edge.model_dump(mode="json")
            )

            if edge.relation == RelationType.REQUIRES and not self._requires_subgraph_is_acyclic():
                cycle = self._find_requires_cycle()
                # Roll back so a rejected edge never corrupts the graph.
                if previous is None:
                    self._graph.remove_edge(edge.source_id, edge.target_id)
                else:
                    self._graph.add_edge(edge.source_id, edge.target_id, **previous)
                raise CyclicPrerequisiteError(cycle)

    def all_edges(self) -> list[PrerequisiteEdge]:
        return [PrerequisiteEdge.model_validate(d["data"]) for _, _, d in self._graph.edges(data=True)]

    def get_prerequisites(self, concept_id: str) -> list[Concept]:
        self._require_node(concept_id)
        prereqs = []
        for _, target, data in self._graph.out_edges(concept_id, data=True):
            if data["data"]["relation"] == RelationType.REQUIRES:
                concept = self.get_concept(target)
                if concept is not None:
                    prereqs.append(concept)
        return prereqs

    def get_dependents(self, concept_id: str) -> list[Concept]:
        self._require_node(concept_id)
        dependents = []
        for source, _, data in self._graph.in_edges(concept_id, data=True):
            if data["data"]["relation"] == RelationType.REQUIRES:
                concept = self.get_concept(source)
                if concept is not None:
                    dependents.append(concept)
        return dependents

    # --- graph algorithms ------------------------------------------------

    def shortest_prerequisite_chain(
        self, known_concept_ids: set[str], goal_concept_id: str
    ) -> list[str]:
        self._require_node(goal_concept_id)
        if goal_concept_id in known_concept_ids:
            return []

        requires_graph = self._requires_subgraph()
        transitive_prereqs = (
            nx.descendants(requires_graph, goal_concept_id)
            if goal_concept_id in requires_graph
            else set()
        )
        still_needed = {c for c in transitive_prereqs if c not in known_concept_ids}

        dangling = [c for c in still_needed if c not in self._graph]
        if dangling:
            raise UnreachableGoalError(goal_concept_id, dangling)

        needed_nodes = still_needed | {goal_concept_id}
        ordering_graph = requires_graph.subgraph(needed_nodes).reverse(copy=True)
        # Reversed REQUIRES edges point prerequisite -> dependent, so a
        # topological sort yields prerequisites first, goal concept last.
        return list(nx.topological_sort(ordering_graph))

    def most_central_concepts(self, top_n: int = 10) -> list[tuple[Concept, float]]:
        requires_graph = self._requires_subgraph()
        scored: list[tuple[str, int]] = []
        for node_id in self._graph.nodes:
            dependent_count = (
                len(nx.ancestors(requires_graph, node_id)) if node_id in requires_graph else 0
            )
            scored.append((node_id, dependent_count))
        scored.sort(key=lambda pair: pair[1], reverse=True)

        results = []
        for node_id, score in scored[:top_n]:
            concept = self.get_concept(node_id)
            if concept is not None:
                results.append((concept, float(score)))
        return results

    def neighbors_context(self, concept_id: str, *, hops: int = 1) -> list[PrerequisiteEdge]:
        self._require_node(concept_id)
        ego = nx.ego_graph(self._graph, concept_id, radius=hops, undirected=True)
        return [PrerequisiteEdge.model_validate(d["data"]) for _, _, d in ego.edges(data=True)]

    # --- persistence ------------------------------------------------------

    def save(self, path: Path | None = None) -> None:
        target = path or self._persist_path
        if target is None:
            raise ValueError("No persist path configured for this repository instance.")
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "concepts": [c.model_dump(mode="json") for c in self.all_concepts()],
            "edges": [e.model_dump(mode="json") for e in self.all_edges()],
        }
        target.write_text(json.dumps(payload, indent=2))
        logger.info(
            "Saved graph: %d concepts, %d edges -> %s",
            len(payload["concepts"]),
            len(payload["edges"]),
            target,
        )

    def load(self, path: Path) -> None:
        data = json.loads(path.read_text())
        with self._lock:
            self._graph.clear()
            for raw_concept in data.get("concepts", []):
                self.upsert_concept(Concept.model_validate(raw_concept))
            for raw_edge in data.get("edges", []):
                self.upsert_edge(PrerequisiteEdge.model_validate(raw_edge))
        logger.info(
            "Loaded graph: %d concepts, %d edges <- %s",
            len(data.get("concepts", [])),
            len(data.get("edges", [])),
            path,
        )

    # --- internals -----------------------------------------------------

    def _require_node(self, concept_id: str) -> None:
        if concept_id not in self._graph:
            raise NotFoundError("Concept", concept_id)

    def _requires_subgraph(self) -> nx.DiGraph:
        requires_edges = [
            (u, v)
            for u, v, data in self._graph.edges(data=True)
            if data["data"]["relation"] == RelationType.REQUIRES
        ]
        if not requires_edges:
            empty = nx.DiGraph()
            empty.add_nodes_from(self._graph.nodes)
            return empty
        return self._graph.edge_subgraph(requires_edges).copy()

    def _requires_subgraph_is_acyclic(self) -> bool:
        return nx.is_directed_acyclic_graph(self._requires_subgraph())

    def _find_requires_cycle(self) -> list[str]:
        requires_graph = self._requires_subgraph()
        cycle_edges = nx.find_cycle(requires_graph)
        nodes = [edge[0] for edge in cycle_edges]
        nodes.append(cycle_edges[-1][1])
        return nodes
