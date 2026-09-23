"""Composition root: the one place that wires concrete repositories, the
Claude client, retrievers, and services together from `Settings`. Both the
FastAPI app (`cke.api.dependencies`) and the CLI (`cke.cli.main`) build a
`Container` and use it - so there is exactly one place backend selection,
construction order, and service wiring can go wrong, not two.
"""

from __future__ import annotations

from dataclasses import dataclass

from cke.config import Settings, get_settings
from cke.ingestion.ingestion_service import CurriculumIngestionService
from cke.llm.claude_client import ClaudeClient
from cke.repositories.factory import (
    build_course_repository,
    build_graph_repository,
    build_vector_repository,
)
from cke.repositories.interfaces import CourseRepository, GraphRepository, VectorRepository
from cke.retrieval.graph_retriever import GraphRetriever
from cke.retrieval.hybrid_retriever import HybridRetriever
from cke.retrieval.vector_retriever import VectorRetriever
from cke.services.curriculum_service import CurriculumService
from cke.services.gap_analysis_service import GapAnalysisService
from cke.services.learning_path_service import LearningPathService
from cke.services.qa_service import QAService


@dataclass
class Container:
    settings: Settings
    vector_repository: VectorRepository
    graph_repository: GraphRepository
    course_repository: CourseRepository
    claude_client: ClaudeClient

    ingestion_service: CurriculumIngestionService
    qa_service: QAService
    learning_path_service: LearningPathService
    gap_analysis_service: GapAnalysisService
    curriculum_service: CurriculumService


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()

    vector_repository = build_vector_repository(settings)
    graph_repository = build_graph_repository(settings)
    course_repository = build_course_repository(settings)
    claude_client = ClaudeClient(settings)

    vector_retriever = VectorRetriever(vector_repository, default_top_k=settings.vector_top_k)
    graph_retriever = GraphRetriever(graph_repository)
    hybrid_retriever = HybridRetriever(vector_retriever, graph_retriever)

    return Container(
        settings=settings,
        vector_repository=vector_repository,
        graph_repository=graph_repository,
        course_repository=course_repository,
        claude_client=claude_client,
        ingestion_service=CurriculumIngestionService(
            vector_repository=vector_repository,
            graph_repository=graph_repository,
            course_repository=course_repository,
            claude_client=claude_client,
        ),
        qa_service=QAService(hybrid_retriever, claude_client),
        learning_path_service=LearningPathService(
            graph_repository, vector_retriever, claude_client
        ),
        gap_analysis_service=GapAnalysisService(graph_repository),
        curriculum_service=CurriculumService(course_repository, graph_repository),
    )
