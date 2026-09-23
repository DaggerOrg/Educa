"""Admin/ops CLI - thin presentation layer over the exact same
`cke.container.Container` the API uses, so `cke-cli ingest` and
`POST /courses/ingest` always behave identically.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from cke.config import get_settings
from cke.container import build_container
from cke.domain.exceptions import CKEError
from cke.ingestion.curriculum_schema import CurriculumSpec
from cke.logging_config import configure_logging

app = typer.Typer(
    name="cke",
    help="Curriculum Knowledge Engine - admin/ops CLI.",
    no_args_is_help=True,
)
console = Console()


def _split_ids(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {piece.strip() for piece in raw.split(",") if piece.strip()}


@app.callback()
def _main(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    settings = get_settings()
    configure_logging(level="DEBUG" if verbose else settings.log_level, as_json=False)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host"),
    port: int = typer.Option(8000, help="Bind port"),
    reload: bool = typer.Option(False, help="Auto-reload on code changes (dev only)"),
) -> None:
    """Run the FastAPI service with uvicorn."""
    import uvicorn

    uvicorn.run("cke.api.app:app", host=host, port=port, reload=reload)


@app.command()
def ingest(
    file: Path | None = typer.Option(
        None, "--file", "-f", help="Curriculum YAML/JSON file (defaults to the bundled sample)"
    ),
    llm_extract: bool = typer.Option(
        False, "--llm-extract", help="Also run Claude-based graph enrichment (needs an API key)"
    ),
) -> None:
    """Ingest a curriculum spec into the vector store and concept graph."""
    settings = get_settings()
    container = build_container(settings)

    path = file or settings.sample_curriculum_path
    console.print(f"[bold]Loading curriculum spec[/bold] from {path}")
    spec = CurriculumSpec.from_file(path)

    try:
        course = container.ingestion_service.ingest(spec, enable_llm_extraction=llm_extract)
    except CKEError as exc:
        console.print(f"[bold red]Ingestion failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold green]Ingested[/bold green] '{course.title}' - "
        f"{len(course.modules)} modules, {course.lesson_count} lessons, "
        f"{course.total_minutes} minutes."
    )


@app.command()
def courses() -> None:
    """List every ingested course."""
    container = build_container()
    table = Table("ID", "Title", "Modules", "Lessons", "Minutes")
    for course in container.curriculum_service.list_courses():
        table.add_row(
            course.id, course.title, str(len(course.modules)), str(course.lesson_count), str(course.total_minutes)
        )
    console.print(table)


@app.command()
def concepts(top_central: int = typer.Option(0, help="Show only the N most foundational concepts")) -> None:
    """List concepts in the graph, optionally ranked by centrality."""
    container = build_container()
    table = Table("ID", "Name", "Difficulty", "Source", "Dependents" if top_central else "Description")

    if top_central:
        for concept, score in container.curriculum_service.most_foundational_concepts(top_n=top_central):
            table.add_row(concept.id, concept.name, concept.difficulty.value, concept.source.value, str(int(score)))
    else:
        for concept in container.curriculum_service.list_concepts():
            table.add_row(concept.id, concept.name, concept.difficulty.value, concept.source.value, concept.description)

    console.print(table)


@app.command()
def ask(
    question: str,
    course_id: str | None = typer.Option(None, help="Restrict retrieval to one course"),
) -> None:
    """Ask a grounded question against the ingested curricula (RAG + GraphRAG)."""
    container = build_container()
    try:
        result = container.qa_service.answer(question, course_id=course_id)
    except CKEError as exc:
        console.print(f"[bold red]Failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold]Q:[/bold] {result.question}")
    console.print(f"[bold]A:[/bold] {result.answer}\n")
    if result.citations:
        console.print("[bold]Citations:[/bold]")
        for i, citation in enumerate(result.citations, start=1):
            console.print(f"  [{i}] {citation.lesson_title} (score={citation.relevance_score:.2f})")


@app.command()
def path(
    goal: str = typer.Argument(..., help="Goal concept id"),
    known: str = typer.Option("", "--known", help="Comma-separated known concept ids"),
) -> None:
    """Compute a graph-ordered learning path to a goal concept."""
    container = build_container()
    try:
        plan = container.learning_path_service.build_plan(_split_ids(known), goal)
    except CKEError as exc:
        console.print(f"[bold red]Failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"[bold]{plan.summary}[/bold]\n")
    table = Table("Step", "Concept", "Minutes", "Rationale")
    for i, step in enumerate(plan.steps, start=1):
        table.add_row(str(i), step.concept.name, str(step.estimated_minutes), step.rationale)
    console.print(table)
    console.print(f"\nTotal estimated time: {plan.total_estimated_minutes} minutes")


@app.command()
def gap(
    target: str = typer.Argument(..., help="Target concept id"),
    known: str = typer.Option("", "--known", help="Comma-separated known concept ids"),
) -> None:
    """Show how ready a learner is for a target concept."""
    container = build_container()
    try:
        result = container.gap_analysis_service.analyze(_split_ids(known), target)
    except CKEError as exc:
        console.print(f"[bold red]Failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"Readiness for '{target}': [bold]{result.readiness_pct}%[/bold]")
    if result.missing_concepts:
        console.print("Missing prerequisites:")
        for concept in result.missing_concepts:
            console.print(f"  - {concept.name} ({concept.id})")
    else:
        console.print("No missing prerequisites.")


if __name__ == "__main__":
    app()
