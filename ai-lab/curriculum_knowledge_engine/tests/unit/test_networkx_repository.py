import pytest

from cke.domain.enums import ConceptSource, RelationType
from cke.domain.exceptions import CyclicPrerequisiteError, NotFoundError, UnreachableGoalError
from cke.domain.models import Concept, PrerequisiteEdge
from cke.repositories.graph.networkx_repository import NetworkXGraphRepository


def _concept(name: str) -> Concept:
    return Concept.from_name(name)


def _requires(source: str, target: str) -> PrerequisiteEdge:
    return PrerequisiteEdge(source_id=source, target_id=target, relation=RelationType.REQUIRES)


@pytest.fixture
def repo() -> NetworkXGraphRepository:
    return NetworkXGraphRepository()


def _seed_linear_chain(repo: NetworkXGraphRepository) -> None:
    # a --requires--> b --requires--> c --requires--> d
    for name in ["a", "b", "c", "d"]:
        repo.upsert_concept(_concept(name))
    repo.upsert_edge(_requires("a", "b"))
    repo.upsert_edge(_requires("b", "c"))
    repo.upsert_edge(_requires("c", "d"))


def test_upsert_and_get_concept_round_trips(repo):
    concept = Concept.from_name("Self-Attention", description="desc", aliases=["Attention"])
    repo.upsert_concept(concept)

    fetched = repo.get_concept(concept.id)
    assert fetched == concept


def test_get_concept_missing_returns_none(repo):
    assert repo.get_concept("does-not-exist") is None


def test_upsert_edge_requires_existing_concepts(repo):
    repo.upsert_concept(_concept("a"))
    with pytest.raises(NotFoundError):
        repo.upsert_edge(_requires("a", "missing"))


def test_upsert_edge_rejects_cycle_and_leaves_graph_unchanged(repo):
    _seed_linear_chain(repo)

    with pytest.raises(CyclicPrerequisiteError):
        repo.upsert_edge(_requires("d", "a"))

    # Rejected edge must not have been added.
    assert repo.get_prerequisites("d") == []
    assert repo.all_edges() == [
        _requires("a", "b"),
        _requires("b", "c"),
        _requires("c", "d"),
    ]


def test_self_loop_is_a_cycle(repo):
    repo.upsert_concept(_concept("a"))
    with pytest.raises(CyclicPrerequisiteError):
        repo.upsert_edge(_requires("a", "a"))


def test_non_requires_edges_are_not_checked_for_cycles(repo):
    repo.upsert_concept(_concept("a"))
    repo.upsert_concept(_concept("b"))
    repo.upsert_edge(PrerequisiteEdge(source_id="a", target_id="b", relation=RelationType.RELATES_TO))
    # The reverse RELATES_TO edge would be a "cycle" in an undirected sense,
    # but RELATES_TO is associative, not load-bearing for ordering - allowed.
    repo.upsert_edge(PrerequisiteEdge(source_id="b", target_id="a", relation=RelationType.RELATES_TO))
    assert len(repo.all_edges()) == 2


def test_get_prerequisites_and_dependents(repo):
    _seed_linear_chain(repo)
    assert [c.id for c in repo.get_prerequisites("b")] == ["c"]
    assert [c.id for c in repo.get_dependents("c")] == ["b"]
    assert repo.get_prerequisites("d") == []
    assert repo.get_dependents("a") == []


def test_get_prerequisites_missing_concept_raises(repo):
    with pytest.raises(NotFoundError):
        repo.get_prerequisites("nope")


def test_shortest_prerequisite_chain_orders_prerequisites_before_dependents(repo):
    _seed_linear_chain(repo)
    chain = repo.shortest_prerequisite_chain(known_concept_ids=set(), goal_concept_id="a")
    assert chain == ["d", "c", "b", "a"]


def test_shortest_prerequisite_chain_excludes_known_concepts(repo):
    _seed_linear_chain(repo)
    chain = repo.shortest_prerequisite_chain(known_concept_ids={"d", "c"}, goal_concept_id="a")
    assert chain == ["b", "a"]


def test_shortest_prerequisite_chain_goal_already_known_is_empty(repo):
    _seed_linear_chain(repo)
    assert repo.shortest_prerequisite_chain(known_concept_ids={"a"}, goal_concept_id="a") == []


def test_shortest_prerequisite_chain_unknown_goal_raises_not_found(repo):
    with pytest.raises(NotFoundError):
        repo.shortest_prerequisite_chain(set(), "nope")


def test_shortest_prerequisite_chain_with_diamond_dependencies(repo):
    #      a
    #    /   \
    #   b     c
    #    \   /
    #      d
    for name in ["a", "b", "c", "d"]:
        repo.upsert_concept(_concept(name))
    repo.upsert_edge(_requires("a", "b"))
    repo.upsert_edge(_requires("a", "c"))
    repo.upsert_edge(_requires("b", "d"))
    repo.upsert_edge(_requires("c", "d"))

    chain = repo.shortest_prerequisite_chain(set(), "a")
    assert chain[0] == "d"
    assert chain[-1] == "a"
    assert set(chain) == {"a", "b", "c", "d"}
    assert chain.index("d") < chain.index("b") < chain.index("a")
    assert chain.index("d") < chain.index("c") < chain.index("a")


def test_most_central_concepts_ranks_by_transitive_dependents(repo):
    _seed_linear_chain(repo)
    ranked = repo.most_central_concepts(top_n=4)
    ids_in_order = [concept.id for concept, _ in ranked]
    assert ids_in_order == ["d", "c", "b", "a"]
    assert dict((c.id, score) for c, score in ranked) == {"d": 3.0, "c": 2.0, "b": 1.0, "a": 0.0}


def test_neighbors_context_includes_incoming_and_outgoing_edges(repo):
    _seed_linear_chain(repo)
    edges = repo.neighbors_context("b", hops=1)
    pairs = {(e.source_id, e.target_id) for e in edges}
    assert pairs == {("a", "b"), ("b", "c")}


def test_clear_removes_everything(repo):
    _seed_linear_chain(repo)
    repo.clear()
    assert repo.all_concepts() == []
    assert repo.all_edges() == []


def test_save_and_load_round_trip(repo, tmp_path):
    _seed_linear_chain(repo)
    path = tmp_path / "graph.json"
    repo.save(path)

    reloaded = NetworkXGraphRepository()
    reloaded.load(path)

    assert {c.id for c in reloaded.all_concepts()} == {"a", "b", "c", "d"}
    assert reloaded.shortest_prerequisite_chain(set(), "a") == ["d", "c", "b", "a"]


def test_load_on_init_from_persist_path(repo, tmp_path):
    _seed_linear_chain(repo)
    path = tmp_path / "graph.json"
    repo.save(path)

    reloaded = NetworkXGraphRepository(persist_path=path)
    assert {c.id for c in reloaded.all_concepts()} == {"a", "b", "c", "d"}


def test_llm_extracted_edge_is_tagged_and_kept_separate_from_authored(repo):
    repo.upsert_concept(_concept("a"))
    repo.upsert_concept(_concept("b"))
    edge = PrerequisiteEdge(
        source_id="a",
        target_id="b",
        relation=RelationType.REQUIRES,
        source_type=ConceptSource.LLM_EXTRACTED,
        confidence=0.7,
        rationale="The lesson mentions b in passing.",
    )
    repo.upsert_edge(edge)
    [stored] = repo.all_edges()
    assert stored.source_type == ConceptSource.LLM_EXTRACTED
    assert stored.confidence == 0.7
