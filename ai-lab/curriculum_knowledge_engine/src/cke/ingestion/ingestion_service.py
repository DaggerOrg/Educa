"""Orchestrates turning a `CurriculumSpec` on disk into a fully indexed
knowledge base: domain objects, an authored prerequisite graph, embedded
chunks in the vector store, and (optionally) an LLM-enriched graph layer.
"""

from __future__ import annotations

from cke.domain.enums import ConceptSource, RelationType
from cke.domain.exceptions import CurriculumIngestionError, CyclicPrerequisiteError
from cke.domain.models import Concept, Course, LearningObjective, Lesson, Module, PrerequisiteEdge, slugify
from cke.ingestion.chunker import chunk_lesson
from cke.ingestion.curriculum_schema import CurriculumSpec
from cke.ingestion.graph_extractor import extract_relationships
from cke.llm.claude_client import ClaudeClient
from cke.logging_config import get_logger
from cke.repositories.interfaces import CourseRepository, GraphRepository, VectorRepository

logger = get_logger(__name__)


class CurriculumIngestionService:
    def __init__(
        self,
        vector_repository: VectorRepository,
        graph_repository: GraphRepository,
        course_repository: CourseRepository,
        claude_client: ClaudeClient | None = None,
    ):
        self._vector_repository = vector_repository
        self._graph_repository = graph_repository
        self._course_repository = course_repository
        self._claude_client = claude_client

    def ingest(self, spec: CurriculumSpec, *, enable_llm_extraction: bool = False) -> Course:
        """Idempotent: re-ingesting the same course id replaces its chunks
        and re-applies its authored graph (upserts are safe to repeat)."""
        if enable_llm_extraction and self._claude_client is None:
            raise CurriculumIngestionError(
                "enable_llm_extraction=True requires this service to have been "
                "constructed with a ClaudeClient."
            )

        course = self._build_course(spec)
        self._upsert_authored_graph(spec)
        chunk_count = self._index_chunks(course)

        extracted_count = 0
        if enable_llm_extraction:
            extracted_count = self._extract_and_merge_graph(spec, course)

        self._course_repository.save(course)
        self._persist_graph_if_supported()

        logger.info(
            "Ingested course '%s': %d lessons, %d chunks, %d authored concepts, "
            "%d LLM-extracted edges merged",
            course.id,
            course.lesson_count,
            chunk_count,
            len(spec.concepts),
            extracted_count,
        )
        return course

    # --- steps ------------------------------------------------------------

    def _build_course(self, spec: CurriculumSpec) -> Course:
        modules: list[Module] = []
        for module_order, module_spec in enumerate(spec.modules):
            lessons: list[Lesson] = []
            for lesson_order, lesson_spec in enumerate(module_spec.lessons):
                lessons.append(
                    Lesson(
                        id=lesson_spec.id,
                        module_id=module_spec.id,
                        title=lesson_spec.title,
                        content=lesson_spec.content,
                        objectives=[
                            LearningObjective(text=o.text, bloom_level=o.bloom_level)
                            for o in lesson_spec.objectives
                        ],
                        concept_ids=[slugify(name) for name in lesson_spec.teaches],
                        estimated_minutes=lesson_spec.estimated_minutes,
                        order=lesson_order,
                    )
                )
            modules.append(
                Module(
                    id=module_spec.id,
                    course_id=spec.id,
                    title=module_spec.title,
                    description=module_spec.description,
                    lessons=lessons,
                    order=module_order,
                )
            )
        return Course(
            id=spec.id,
            title=spec.title,
            description=spec.description,
            difficulty=spec.difficulty,
            modules=modules,
        )

    def _upsert_authored_graph(self, spec: CurriculumSpec) -> None:
        for concept_spec in spec.concepts:
            concept = Concept.from_name(
                concept_spec.name,
                description=concept_spec.description,
                difficulty=concept_spec.difficulty,
                source=ConceptSource.AUTHORED,
                aliases=concept_spec.aliases,
            )
            self._graph_repository.upsert_concept(concept)

        for concept_spec in spec.concepts:
            source_id = slugify(concept_spec.name)
            for required_name in concept_spec.requires:
                edge = PrerequisiteEdge(
                    source_id=source_id,
                    target_id=slugify(required_name),
                    relation=RelationType.REQUIRES,
                    source_type=ConceptSource.AUTHORED,
                )
                try:
                    self._graph_repository.upsert_edge(edge)
                except CyclicPrerequisiteError as exc:
                    # An authored cycle is an authoring bug, not something to
                    # silently drop - the curriculum spec itself is wrong.
                    raise CurriculumIngestionError(
                        f"Curriculum '{spec.id}' has a cyclic prerequisite graph: {exc}"
                    ) from exc

    def _index_chunks(self, course: Course) -> int:
        self._vector_repository.delete_by_course(course.id)
        chunks = [
            chunk
            for lesson in course.iter_lessons()
            for chunk in chunk_lesson(lesson, course_id=course.id)
        ]
        self._vector_repository.upsert_chunks(chunks)
        return len(chunks)

    def _extract_and_merge_graph(self, spec: CurriculumSpec, course: Course) -> int:
        known_names = [concept.name for concept in spec.concepts]
        merged = 0
        for lesson in course.iter_lessons():
            try:
                result = extract_relationships(self._claude_client, lesson, known_names)
            except Exception as exc:  # noqa: BLE001 - one lesson's LLM failure shouldn't abort ingestion
                logger.warning("Graph extraction failed for lesson '%s': %s", lesson.id, exc)
                continue

            for relationship in result.relationships:
                edge = PrerequisiteEdge(
                    source_id=slugify(relationship.source_concept),
                    target_id=slugify(relationship.target_concept),
                    relation=relationship.relation,
                    source_type=ConceptSource.LLM_EXTRACTED,
                    confidence=relationship.confidence,
                    rationale=relationship.rationale,
                )
                try:
                    self._graph_repository.upsert_edge(edge)
                    merged += 1
                except CyclicPrerequisiteError:
                    logger.warning(
                        "Discarding LLM-extracted edge %s -> %s: would create a cycle",
                        edge.source_id,
                        edge.target_id,
                    )
        return merged

    def _persist_graph_if_supported(self) -> None:
        # NetworkXGraphRepository is in-memory and offers an explicit
        # save() for its JSON snapshot, but only actually persists when it
        # was constructed with a persist_path (tests often deliberately
        # omit one to stay in-memory-only); Neo4jGraphRepository is durable
        # on every write and has neither attribute. Duck-typed so this
        # service never needs to know which backend it's holding.
        save = getattr(self._graph_repository, "save", None)
        persist_path = getattr(self._graph_repository, "persist_path", None)
        if callable(save) and persist_path is not None:
            save()
