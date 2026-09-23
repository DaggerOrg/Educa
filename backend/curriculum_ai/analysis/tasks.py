"""The background job that runs the faculty panel over an uploaded PDF.

Called by an RQ worker (jobs/worker.py) but free of RQ imports, so tests
call `analyze_document(...)` directly -- same shape as processing.py, and
it borrows that module's fencing idea: every enqueue mints a fresh
`job_id` stamped onto the `StudyGuideRun` first, the job atomically claims
the run (queued -> running for exactly that job_id), and re-checks it still
owns the run before each write. A redelivered, duplicated, or superseded
job therefore exits without touching anything.

Re-running never destroys teacher work. Each run replaces the *unreviewed*
entries (`proposed` and never edited) and skips re-proposing anything the
teacher already approved, edited, or rejected.
"""

from __future__ import annotations

from sqlalchemy import delete, select, update

from app.agents.faculty.panel import FacultyPanel, PanelResult
from app import usage
from app.db.session import SessionLocal

from ..logging_config import get_logger
from ..models import Document, Project, StudyGuideEntry, StudyGuideRun, StudyGuideRunStatus, StudyGuideUnit
from ..storage import get_storage
from .grounding import is_grounded
from .units import Unit, units_from_pdf

logger = get_logger(__name__)


def _norm_title(title: str) -> str:
    return " ".join(title.casefold().split())


def _claim(run_id: str, job_id: str) -> bool:
    with SessionLocal() as session:
        claimed = session.execute(
            update(StudyGuideRun)
            .where(
                StudyGuideRun.id == run_id,
                StudyGuideRun.job_id == job_id,
                StudyGuideRun.status == StudyGuideRunStatus.QUEUED.value,
            )
            .values(status=StudyGuideRunStatus.RUNNING.value)
        )
        session.commit()
        return claimed.rowcount == 1


def _still_current(session, run_id: str, job_id: str) -> StudyGuideRun | None:
    run = session.get(StudyGuideRun, run_id)
    return run if run is not None and run.job_id == job_id else None


def _fail(run_id: str, job_id: str, error: str) -> None:
    with SessionLocal() as session:
        run = _still_current(session, run_id, job_id)
        if run is not None:
            run.status = StudyGuideRunStatus.FAILED.value
            run.error = error[:2000]
            session.commit()


def _entry_rows(document_id: str, order: int, unit: Unit, result: PanelResult) -> list[StudyGuideEntry]:
    plain = unit.plain_text
    rows: list[StudyGuideEntry] = []

    def add(kind: str, title: str, entry) -> None:
        data = entry.model_dump(exclude={"evidence_quote", "page"})
        in_range = unit.page_start <= entry.page <= unit.page_end
        rows.append(
            StudyGuideEntry(
                document_id=document_id,
                kind=kind,
                unit_order=order,
                unit_title=unit.title,
                title=title,
                data=data,
                evidence_quote=entry.evidence_quote,
                # A page outside the chapter is a model slip; fall back to the chapter's own range.
                page_start=entry.page if in_range else unit.page_start,
                page_end=entry.page if in_range else unit.page_end,
                grounded=is_grounded(entry.evidence_quote, plain),
            )
        )

    for concept in result.concepts:
        add("concept", concept.name, concept)
    for theory in result.theories:
        add("theory", theory.name, theory)
    for exercise in result.exercises:
        add("exercise", exercise.title, exercise)
    return rows


def analyze_document(run_id: str, job_id: str, panel: FacultyPanel | None = None) -> None:
    if not _claim(run_id, job_id):
        logger.info("analyze_document(run=%s, job=%s): not claimed -- skipping", run_id, job_id)
        return
    logger.info("analyze_document(run=%s, job=%s): claimed", run_id, job_id)
    try:
        _run(run_id, job_id, panel)
    except Exception as exc:  # noqa: BLE001 - always land in FAILED with the real error, never crash the worker
        logger.exception("analyze_document(run=%s, job=%s): failed", run_id, job_id)
        _fail(run_id, job_id, f"{type(exc).__name__}: {exc}")


def _run(run_id: str, job_id: str, panel: FacultyPanel | None) -> None:
    with SessionLocal() as session:
        run = _still_current(session, run_id, job_id)
        if run is None:
            return
        document_id = run.document_id
        doc = session.get(Document, document_id)
        if doc is None:
            return
        storage_key = doc.storage_key
        teacher_id = session.get(Project, doc.project_id).teacher_id

    units = units_from_pdf(get_storage().get(storage_key))
    if not units:
        raise ValueError("No readable text found in document (scanned PDFs need OCR, not yet supported)")

    panel = panel or FacultyPanel()

    with SessionLocal() as session:
        run = _still_current(session, run_id, job_id)
        if run is None:
            return
        kept = list(
            session.execute(
                select(StudyGuideEntry.kind, StudyGuideEntry.title).where(
                    StudyGuideEntry.document_id == document_id,
                    (StudyGuideEntry.review_status != "proposed") | (StudyGuideEntry.edited.is_(True)),
                )
            )
        )
        session.execute(
            delete(StudyGuideEntry).where(
                StudyGuideEntry.document_id == document_id,
                StudyGuideEntry.review_status == "proposed",
                StudyGuideEntry.edited.is_(False),
            )
        )
        session.execute(delete(StudyGuideUnit).where(StudyGuideUnit.document_id == document_id))
        unit_rows = [
            StudyGuideUnit(
                document_id=document_id, order_index=i, title=u.title, page_start=u.page_start, page_end=u.page_end
            )
            for i, u in enumerate(units)
        ]
        session.add_all(unit_rows)
        run.total_units = len(units)
        run.completed_units = 0
        run.model_id = panel.model_id
        session.commit()
        unit_ids = [row.id for row in unit_rows]

    already_decided = {(kind, _norm_title(title)) for kind, title in kept}
    failed_units = 0

    for order, (unit, unit_id) in enumerate(zip(units, unit_ids)):
        try:
            result = panel.analyze_chapter(unit.title, unit.page_start, unit.page_end, unit.text)
            error = "; ".join(result.errors) or None
            status = "done"
        except Exception as exc:  # noqa: BLE001 - one bad chapter must not abandon the rest of the book
            logger.exception("analyze_document(run=%s): unit %d %r failed", run_id, order, unit.title)
            result, error, status = None, f"{type(exc).__name__}: {exc}", "failed"
            failed_units += 1

        with SessionLocal() as session:
            run = _still_current(session, run_id, job_id)
            if run is None:
                logger.info("analyze_document(run=%s): superseded mid-run; aborting", run_id)
                return
            unit_row = session.get(StudyGuideUnit, unit_id)
            unit_row.status, unit_row.error = status, (error[:2000] if error else None)
            if result is not None:
                if result.chair is not None:
                    unit_row.summary = result.chair.summary
                    unit_row.learning_objectives = result.chair.learning_objectives
                session.add_all(
                    row
                    for row in _entry_rows(document_id, order, unit, result)
                    if (row.kind, _norm_title(row.title)) not in already_decided
                )
            run.completed_units = order + 1
            session.commit()

        if result is not None and (result.input_tokens or result.output_tokens):
            usage.record(teacher_id, "faculty_panel", panel.model_id, result.input_tokens, result.output_tokens)

    with SessionLocal() as session:
        run = _still_current(session, run_id, job_id)
        if run is None:
            return
        if failed_units == len(units):
            run.status = StudyGuideRunStatus.FAILED.value
            run.error = "Every chapter failed to analyze; see each chapter's error."
        else:
            run.status = StudyGuideRunStatus.COMPLETED.value
            run.error = f"{failed_units} of {len(units)} chapters failed." if failed_units else None
        session.commit()
    logger.info("analyze_document(run=%s): finished, %d/%d chapters ok", run_id, len(units) - failed_units, len(units))
