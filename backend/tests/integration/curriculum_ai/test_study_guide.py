"""The faculty pipeline end to end against real Postgres: chapters, entries,
grounding flags, re-run safety, job fencing, and the HTTP review flow. The
panel is a stub -- no model calls -- and the RQ queue is faked where a test
only needs to see what would be enqueued.
"""

import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).parents[3]))

from app.agents.faculty.panel import PanelResult  # noqa: E402
from app.agents.faculty.schemas import ChairSummary, ConceptEntry, ExerciseEntry, TheoryEntry  # noqa: E402
from app.auth import security, store  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from curriculum_ai import service  # noqa: E402
from curriculum_ai.analysis import service as analysis_service  # noqa: E402
from curriculum_ai.analysis.tasks import analyze_document  # noqa: E402
from curriculum_ai.models import StudyGuideEntry, StudyGuideRun, StudyGuideUnit  # noqa: E402
from curriculum_ai.processing import process_document  # noqa: E402


class FakePanel:
    """Emits one grounded concept, one ungrounded theory (page outside the
    chapter), and one exercise per chapter. `fail_titles` makes those
    chapters raise, the way an all-specialists-down chapter does."""

    model_id = "fake-model"

    def __init__(self, fail_titles=(), concept_name="Acceleration"):
        self.fail_titles, self.concept_name, self.calls = set(fail_titles), concept_name, []

    def analyze_chapter(self, title, page_start, page_end, text):
        self.calls.append(title)
        if title in self.fail_titles:
            raise RuntimeError("all specialists down")
        first_page_text = text.split("\n", 1)[1][:80]
        return PanelResult(
            concepts=[
                ConceptEntry(
                    name=self.concept_name, definition="d", explanation="e",
                    evidence_quote=first_page_text, page=page_start,
                )
            ],
            theories=[
                TheoryEntry(
                    name="Made-up law", statement="s", intuition="i",
                    evidence_quote="a sentence that is nowhere in this book", page=page_end + 99,
                )
            ],
            exercises=[
                ExerciseEntry(
                    kind="practice_problem", title=f"Problem in {title}", problem="p",
                    difficulty="introductory", final_answer="", evidence_quote=first_page_text, page=page_start,
                )
            ],
            chair=ChairSummary(summary=f"About {title}", learning_objectives=["Students will be able to X"]),
        )


class FakeQueue:
    def __init__(self):
        self.enqueued = []

    def enqueue(self, fn, *args, **kwargs):
        self.enqueued.append((fn, args, kwargs))


@pytest.fixture
def fake_queue(monkeypatch):
    queue = FakeQueue()
    monkeypatch.setattr(analysis_service, "get_queue", lambda: queue)
    return queue


@pytest.fixture
def ready_doc(teacher, sample_pdf_bytes):
    doc = service.upload_document(
        teacher["project_id"], teacher["user_id"], "textbook.pdf", sample_pdf_bytes, "application/pdf"
    )
    process_document(doc.id, doc.processing_job_id)
    return doc


def _run(doc, fake_queue, panel):
    """Start a run through the service, then execute it as the worker would."""
    run = analysis_service.enqueue_analysis(doc.id)
    _, args, _ = fake_queue.enqueued[-1]
    analyze_document(*args, panel=panel)
    with SessionLocal() as session:
        return session.get(StudyGuideRun, run.id)


def _entries(doc_id):
    with SessionLocal() as session:
        return list(session.scalars(select(StudyGuideEntry).where(StudyGuideEntry.document_id == doc_id)))


@pytest.mark.integration
def test_analysis_saves_chapters_cited_entries_and_flags_ungrounded_quotes(ready_doc, fake_queue):
    run = _run(ready_doc, fake_queue, FakePanel())

    assert run.status == "completed" and run.error is None
    assert (run.total_units, run.completed_units, run.model_id) == (3, 3, "fake-model")

    with SessionLocal() as session:
        units = list(
            session.scalars(
                select(StudyGuideUnit).where(StudyGuideUnit.document_id == ready_doc.id).order_by(StudyGuideUnit.order_index)
            )
        )
    assert [u.title for u in units] == ["Pages 1–10", "Pages 11–20", "Pages 21–21"]
    assert all(u.status == "done" and u.summary == f"About {u.title}" for u in units)
    assert units[0].learning_objectives == ["Students will be able to X"]

    by_kind = {e.kind: e for e in _entries(ready_doc.id) if e.unit_order == 0}
    concept, theory = by_kind["concept"], by_kind["theory"]
    assert concept.grounded and (concept.page_start, concept.page_end) == (1, 1)
    assert concept.data["definition"] == "d" and "evidence_quote" not in concept.data
    # The fabricated quote is flagged, and its out-of-chapter page falls back to the chapter's range.
    assert not theory.grounded and (theory.page_start, theory.page_end) == (1, 10)
    assert {e.review_status for e in _entries(ready_doc.id)} == {"proposed"}


@pytest.mark.integration
def test_rerun_replaces_unreviewed_entries_but_never_teacher_decisions(ready_doc, fake_queue):
    _run(ready_doc, fake_queue, FakePanel())
    with SessionLocal() as session:
        concepts = list(
            session.scalars(
                select(StudyGuideEntry).where(StudyGuideEntry.document_id == ready_doc.id, StudyGuideEntry.kind == "concept")
                .order_by(StudyGuideEntry.unit_order)
            )
        )
        concepts[0].review_status = "approved"
        concepts[1].review_status = "rejected"
        exercise = session.scalar(
            select(StudyGuideEntry).where(StudyGuideEntry.document_id == ready_doc.id, StudyGuideEntry.kind == "exercise")
        )
        exercise.edited = True
        exercise.title = "My better title"
        session.commit()
        approved_id, rejected_id, edited_id = concepts[0].id, concepts[1].id, exercise.id

    run = _run(ready_doc, fake_queue, FakePanel())
    assert run.status == "completed"

    entries = {e.id: e for e in _entries(ready_doc.id)}
    # Decided entries survive untouched...
    assert entries[approved_id].review_status == "approved"
    assert entries[rejected_id].review_status == "rejected"
    assert entries[edited_id].title == "My better title"
    # ...and the re-run does not re-propose a concept the teacher already approved or rejected.
    concepts = [e for e in entries.values() if e.kind == "concept"]
    assert sorted(e.review_status for e in concepts) == ["approved", "rejected"] and len(concepts) == 2
    # Unreviewed entries were replaced, not duplicated: 3 theories (one per chapter), not 6.
    assert len([e for e in entries.values() if e.kind == "theory"]) == 3


@pytest.mark.integration
def test_a_failed_chapter_is_recorded_and_the_rest_continue(ready_doc, fake_queue):
    run = _run(ready_doc, fake_queue, FakePanel(fail_titles={"Pages 11–20"}))
    assert run.status == "completed" and run.error == "1 of 3 chapters failed."
    with SessionLocal() as session:
        statuses = {
            u.title: (u.status, u.error)
            for u in session.scalars(select(StudyGuideUnit).where(StudyGuideUnit.document_id == ready_doc.id))
        }
    assert statuses["Pages 11–20"] == ("failed", "RuntimeError: all specialists down")
    assert statuses["Pages 1–10"][0] == statuses["Pages 21–21"][0] == "done"
    assert {e.unit_order for e in _entries(ready_doc.id)} == {0, 2}


@pytest.mark.integration
def test_every_chapter_failing_fails_the_run(ready_doc, fake_queue):
    run = _run(ready_doc, fake_queue, FakePanel(fail_titles={"Pages 1–10", "Pages 11–20", "Pages 21–21"}))
    assert run.status == "failed" and "Every chapter failed" in run.error


@pytest.mark.integration
def test_a_job_that_does_not_own_the_run_does_nothing(ready_doc, fake_queue):
    analysis_service.enqueue_analysis(ready_doc.id)
    run_id = fake_queue.enqueued[-1][1][0]
    panel = FakePanel()

    analyze_document(run_id, "some-other-job-id", panel=panel)  # superseded / redelivered under a stale id
    assert panel.calls == []
    with SessionLocal() as session:
        assert session.get(StudyGuideRun, run_id).status == "queued"

    analyze_document(*fake_queue.enqueued[-1][1], panel=panel)
    analyze_document(*fake_queue.enqueued[-1][1], panel=panel)  # duplicate delivery of the real job
    assert len(panel.calls) == 3  # ran once, not twice


@pytest.mark.integration
def test_only_ready_documents_can_be_analyzed_and_only_one_run_at_a_time(teacher, sample_pdf_bytes, fake_queue):
    doc = service.upload_document(
        teacher["project_id"], teacher["user_id"], "textbook.pdf", sample_pdf_bytes, "application/pdf"
    )
    with pytest.raises(ValueError, match="must be ready"):
        analysis_service.start_analysis(teacher["project_id"], doc.id, teacher["user_id"])

    process_document(doc.id, doc.processing_job_id)
    analysis_service.start_analysis(teacher["project_id"], doc.id, teacher["user_id"])
    with pytest.raises(ValueError, match="already in progress"):
        analysis_service.start_analysis(teacher["project_id"], doc.id, teacher["user_id"])
    assert len(fake_queue.enqueued) == 1


@pytest.mark.integration
def test_a_scanned_pdf_with_no_text_fails_clearly(teacher, ready_doc, fake_queue, monkeypatch):
    monkeypatch.setattr("curriculum_ai.analysis.tasks.units_from_pdf", lambda content: [])
    run = _run(ready_doc, fake_queue, FakePanel())
    assert run.status == "failed" and "No readable text" in run.error


@pytest.mark.integration
def test_finishing_ingestion_enqueues_the_analysis_when_enabled(teacher, sample_pdf_bytes, fake_queue, monkeypatch):
    monkeypatch.setenv("STUDY_GUIDE_AUTO_ANALYZE", "true")
    doc = service.upload_document(
        teacher["project_id"], teacher["user_id"], "textbook.pdf", sample_pdf_bytes, "application/pdf"
    )
    process_document(doc.id, doc.processing_job_id)
    assert [fn.__name__ for fn, _, _ in fake_queue.enqueued] == ["analyze_document"]


@pytest.mark.integration
def test_a_queue_outage_after_ingestion_does_not_fail_the_document(teacher, sample_pdf_bytes, monkeypatch):
    monkeypatch.setenv("STUDY_GUIDE_AUTO_ANALYZE", "true")

    class DownQueue:
        def enqueue(self, *args, **kwargs):
            raise ConnectionError("redis down")

    monkeypatch.setattr(analysis_service, "get_queue", lambda: DownQueue())
    doc = service.upload_document(
        teacher["project_id"], teacher["user_id"], "textbook.pdf", sample_pdf_bytes, "application/pdf"
    )
    process_document(doc.id, doc.processing_job_id)
    assert service.get_document(teacher["project_id"], doc.id, teacher["user_id"]).status == "ready"


# --- HTTP ---------------------------------------------------------------------


@pytest.fixture
def client(local_storage):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def other_teacher(local_storage):
    user = store.create_user(
        f"other-{uuid.uuid4().hex}@example.com", "Other", security.hash_password("testpass123"), "teacher"
    )
    return {"headers": {"Authorization": f"Bearer {security.create_access_token(user['id'])}"}}


@pytest.mark.integration
def test_review_flow_over_http(client, teacher, ready_doc, fake_queue, other_teacher):
    base = f"/api/curriculum/projects/{teacher['project_id']}/documents/{ready_doc.id}/analysis"

    assert client.get(base, headers=teacher["headers"]).json() == {"run": None, "units": [], "entries": []}

    started = client.post(base, headers=teacher["headers"])
    assert started.status_code == 202 and started.json()["status"] == "queued"
    assert client.post(base, headers=teacher["headers"]).status_code == 400  # already in progress
    analyze_document(*fake_queue.enqueued[-1][1], panel=FakePanel())

    guide = client.get(base, headers=teacher["headers"]).json()
    assert guide["run"]["status"] == "completed" and len(guide["units"]) == 3 and len(guide["entries"]) == 9
    concept = next(e for e in guide["entries"] if e["kind"] == "concept")

    entry_url = f"{base}/entries/{concept['id']}"
    approved = client.patch(entry_url, headers=teacher["headers"], json={"review_status": "approved"})
    assert approved.status_code == 200 and approved.json()["review_status"] == "approved"
    assert approved.json()["edited"] is False

    edited = client.patch(
        entry_url, headers=teacher["headers"], json={"title": "Acceleration (a)", "data": {"definition": "dv/dt"}}
    )
    assert edited.json()["title"] == "Acceleration (a)" and edited.json()["edited"] is True
    assert edited.json()["data"]["definition"] == "dv/dt" and edited.json()["data"]["explanation"] == "e"

    bad = lambda body: client.patch(entry_url, headers=teacher["headers"], json=body).status_code  # noqa: E731
    assert bad({"review_status": "published"}) == 400
    assert bad({"data": {"not_a_field": "x"}}) == 400
    assert bad({"data": {"prerequisites": "should be a list"}}) == 400
    assert bad({"title": "  "}) == 400

    # Another teacher can neither read nor change someone else's study guide.
    assert client.get(base, headers=other_teacher["headers"]).status_code == 403
    assert client.post(base, headers=other_teacher["headers"]).status_code == 403
    assert client.patch(entry_url, headers=other_teacher["headers"], json={"review_status": "rejected"}).status_code == 403
    assert client.get(base).status_code in (401, 403)
