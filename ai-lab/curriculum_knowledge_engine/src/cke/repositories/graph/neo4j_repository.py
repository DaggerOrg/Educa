"""Production graph backend: Neo4j via the official `neo4j` driver.

Concepts become `(:Concept {id, name, description, difficulty, source,
aliases})` nodes. Each `RelationType` becomes its own relationship type
(`REQUIRES`, `RELATES_TO`, `PART_OF`, `EXTENDS`) rather than a generic
`RELATION {type: ...}` edge, so Cypher queries can filter by relationship
type natively instead of on a property - the idiomatic Neo4j modeling
choice, and the reason `shortest_prerequisite_chain` below can express
"transitive prerequisites" as a plain `-[:REQUIRES*0..]->` pattern.

This implementation is not exercised by the automated test suite (there is
no Neo4j instance in this environment) - `NetworkXGraphRepository` is.
Point `CKE_NEO4J_URI` / `CKE_NEO4J_USER` / `CKE_NEO4J_PASSWORD` at a real
instance (e.g. `docker compose up neo4j`, see ../../../docker-compose.yml)
to use it; both classes satisfy the same `GraphRepository` interface so no
other code needs to change.
"""

from __future__ import annotations

from collections import deque

from neo4j import Driver, GraphDatabase, ManagedTransaction

from cke.domain.enums import RelationType
from cke.domain.exceptions import CyclicPrerequisiteError, NotFoundError, UnreachableGoalError
from cke.domain.models import Concept, PrerequisiteEdge
from cke.logging_config import get_logger
from cke.repositories.interfaces import GraphRepository

logger = get_logger(__name__)

_CONCEPT_PROPS = ("id", "name", "description", "difficulty", "source", "aliases")


def _node_to_concept(node) -> Concept:
    props = dict(node)
    return Concept.model_validate(props)


class Neo4jGraphRepository(GraphRepository):
    def __init__(self, uri: str, user: str, password: str):
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    # --- concepts -----------------------------------------------------

    def upsert_concept(self, concept: Concept) -> None:
        query = """
        MERGE (c:Concept {id: $id})
        SET c.name = $name,
            c.description = $description,
            c.difficulty = $difficulty,
            c.source = $source,
            c.aliases = $aliases
        """
        with self._driver.session() as session:
            session.execute_write(
                lambda tx: tx.run(
                    query,
                    id=concept.id,
                    name=concept.name,
                    description=concept.description,
                    difficulty=concept.difficulty.value,
                    source=concept.source.value,
                    aliases=concept.aliases,
                )
            )

    def get_concept(self, concept_id: str) -> Concept | None:
        query = "MATCH (c:Concept {id: $id}) RETURN c"
        with self._driver.session() as session:
            record = session.run(query, id=concept_id).single()
        return _node_to_concept(record["c"]) if record else None

    def all_concepts(self) -> list[Concept]:
        query = "MATCH (c:Concept) RETURN c"
        with self._driver.session() as session:
            records = list(session.run(query))
        return [_node_to_concept(r["c"]) for r in records]

    def clear(self) -> None:
        with self._driver.session() as session:
            session.execute_write(lambda tx: tx.run("MATCH (n:Concept) DETACH DELETE n"))

    # --- edges ----------------------------------------------------------

    def upsert_edge(self, edge: PrerequisiteEdge) -> None:
        if self.get_concept(edge.source_id) is None:
            raise NotFoundError("Concept", edge.source_id)
        if self.get_concept(edge.target_id) is None:
            raise NotFoundError("Concept", edge.target_id)

        rel_type = edge.relation.name  # closed enum -> safe to interpolate as a Cypher label

        def _write(tx: ManagedTransaction):
            if edge.relation == RelationType.REQUIRES:
                # A cycle would exist iff target already (transitively)
                # requires source - i.e. a REQUIRES path already runs
                # target -> ... -> source before we add source -> target.
                cycle_check = tx.run(
                    """
                    MATCH path = (target:Concept {id: $target_id})
                                  -[:REQUIRES*]->(source:Concept {id: $source_id})
                    RETURN [n IN nodes(path) | n.id] AS ids LIMIT 1
                    """,
                    target_id=edge.target_id,
                    source_id=edge.source_id,
                ).single()
                if cycle_check is not None:
                    cycle = [edge.source_id, *cycle_check["ids"]]
                    raise CyclicPrerequisiteError(cycle)

            tx.run(
                f"""
                MATCH (source:Concept {{id: $source_id}}), (target:Concept {{id: $target_id}})
                MERGE (source)-[r:{rel_type}]->(target)
                SET r.confidence = $confidence, r.rationale = $rationale, r.source_type = $source_type
                """,
                source_id=edge.source_id,
                target_id=edge.target_id,
                confidence=edge.confidence,
                rationale=edge.rationale,
                source_type=edge.source_type.value,
            )

        with self._driver.session() as session:
            session.execute_write(_write)

    def all_edges(self) -> list[PrerequisiteEdge]:
        query = """
        MATCH (s:Concept)-[r]->(t:Concept)
        WHERE type(r) IN $rel_types
        RETURN s.id AS source_id, t.id AS target_id, type(r) AS relation,
               r.confidence AS confidence, r.rationale AS rationale, r.source_type AS source_type
        """
        with self._driver.session() as session:
            records = list(session.run(query, rel_types=[rt.name for rt in RelationType]))
        return [self._record_to_edge(r) for r in records]

    def get_prerequisites(self, concept_id: str) -> list[Concept]:
        if self.get_concept(concept_id) is None:
            raise NotFoundError("Concept", concept_id)
        query = "MATCH (:Concept {id: $id})-[:REQUIRES]->(p:Concept) RETURN p"
        with self._driver.session() as session:
            records = list(session.run(query, id=concept_id))
        return [_node_to_concept(r["p"]) for r in records]

    def get_dependents(self, concept_id: str) -> list[Concept]:
        if self.get_concept(concept_id) is None:
            raise NotFoundError("Concept", concept_id)
        query = "MATCH (:Concept {id: $id})<-[:REQUIRES]-(d:Concept) RETURN d"
        with self._driver.session() as session:
            records = list(session.run(query, id=concept_id))
        return [_node_to_concept(r["d"]) for r in records]

    # --- graph algorithms ------------------------------------------------

    def shortest_prerequisite_chain(
        self, known_concept_ids: set[str], goal_concept_id: str
    ) -> list[str]:
        if self.get_concept(goal_concept_id) is None:
            raise NotFoundError("Concept", goal_concept_id)
        if goal_concept_id in known_concept_ids:
            return []

        transitive_query = """
        MATCH (goal:Concept {id: $goal_id})-[:REQUIRES*0..]->(p:Concept)
        RETURN DISTINCT p.id AS id
        """
        with self._driver.session() as session:
            transitive_ids = {r["id"] for r in session.run(transitive_query, goal_id=goal_concept_id)}

        needed = {c for c in transitive_ids if c not in known_concept_ids} | {goal_concept_id}

        edges_query = """
        MATCH (a:Concept)-[:REQUIRES]->(b:Concept)
        WHERE a.id IN $needed AND b.id IN $needed
        RETURN a.id AS dependent, b.id AS prerequisite
        """
        with self._driver.session() as session:
            edge_records = list(session.run(edges_query, needed=list(needed)))

        # prerequisite -> dependent, so Kahn's algorithm yields prereqs first.
        forward_edges = [(r["prerequisite"], r["dependent"]) for r in edge_records]
        try:
            return _topological_sort(list(needed), forward_edges)
        except _CycleDetectedError as exc:
            raise UnreachableGoalError(goal_concept_id, exc.remaining_nodes) from exc

    def most_central_concepts(self, top_n: int = 10) -> list[tuple[Concept, float]]:
        query = """
        MATCH (c:Concept)
        OPTIONAL MATCH (dependent:Concept)-[:REQUIRES*]->(c)
        RETURN c, count(DISTINCT dependent) AS score
        ORDER BY score DESC
        LIMIT $top_n
        """
        with self._driver.session() as session:
            records = list(session.run(query, top_n=top_n))
        return [(_node_to_concept(r["c"]), float(r["score"])) for r in records]

    def neighbors_context(self, concept_id: str, *, hops: int = 1) -> list[PrerequisiteEdge]:
        if self.get_concept(concept_id) is None:
            raise NotFoundError("Concept", concept_id)
        query = f"""
        MATCH path = (c:Concept {{id: $id}})-[*1..{int(hops)}]-(:Concept)
        UNWIND relationships(path) AS rel
        WITH DISTINCT rel
        RETURN startNode(rel).id AS source_id, endNode(rel).id AS target_id, type(rel) AS relation,
               rel.confidence AS confidence, rel.rationale AS rationale, rel.source_type AS source_type
        """
        with self._driver.session() as session:
            records = list(session.run(query, id=concept_id))
        return [self._record_to_edge(r) for r in records]

    @staticmethod
    def _record_to_edge(record) -> PrerequisiteEdge:
        return PrerequisiteEdge(
            source_id=record["source_id"],
            target_id=record["target_id"],
            relation=RelationType[record["relation"]],
            confidence=record["confidence"] if record["confidence"] is not None else 1.0,
            rationale=record["rationale"] or "",
            source_type=record["source_type"] or "authored",
        )


class _CycleDetectedError(Exception):
    def __init__(self, remaining_nodes: list[str]):
        self.remaining_nodes = remaining_nodes


def _topological_sort(nodes: list[str], edges: list[tuple[str, str]]) -> list[str]:
    """Kahn's algorithm. `edges` are (prerequisite, dependent) pairs."""
    in_degree = {n: 0 for n in nodes}
    adjacency: dict[str, list[str]] = {n: [] for n in nodes}
    for prerequisite, dependent in edges:
        adjacency[prerequisite].append(dependent)
        in_degree[dependent] += 1

    queue = deque(sorted(n for n, degree in in_degree.items() if degree == 0))
    ordered: list[str] = []
    while queue:
        node = queue.popleft()
        ordered.append(node)
        for neighbor in sorted(adjacency[node]):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(ordered) != len(nodes):
        raise _CycleDetectedError([n for n in nodes if n not in ordered])
    return ordered
