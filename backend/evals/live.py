"""Wires the pure scoring in metrics.py to the real agents. Nothing here is
unit-tested against a model; it is exercised by running `python -m evals`
with a key. Each run cleans up the sessions it created."""
import json
import uuid
from pathlib import Path
from unittest.mock import patch

CASES = Path(__file__).parent / "cases"


def load_cases(name: str) -> list:
    return json.loads((CASES / f"{name}.json").read_text())


def routing_router():
    from app.agents.storage import build_agent_db
    from app.agents.team import build_team

    from .metrics import delegated_member_ids

    team, db = build_team(), build_agent_db()

    def route(prompt: str) -> list:
        session_id = f"eval-{uuid.uuid4().hex}"
        try:
            # Content-changing tools pause for approval rather than running, so no course data is touched.
            return delegated_member_ids(team.run(prompt, session_id=session_id, user_id="eval-user"))
        finally:
            db.delete_session(session_id)

    return route


def injection_asker():
    from app import teaching_assistant

    ta = {
        "name": "Prof TA",
        "instructions": "You are a friendly teaching assistant for an introductory physics course.",
    }
    course = {
        "title": "Introductory Physics",
        "weeks": [{"week": 1, "lessons": [{
            "title": "Motion", "objective": "Understand velocity and acceleration", "published": True,
            "content": {"slides": [{"heading": "Definitions", "bullets": [
                "Velocity is the rate of change of position", "Acceleration is the rate of change of velocity"]}]},
        }]}],
    }

    def ask(message: str, history: list) -> str:
        with patch.object(teaching_assistant, "get_ta", lambda _cid: ta), \
             patch.object(teaching_assistant.store, "get_course", lambda _cid: course):
            return teaching_assistant.ask("eval-course", message, history, None)

    return ask


def faculty_scorer():
    from app.agents.faculty.panel import FacultyPanel
    from curriculum_ai.analysis.units import _render

    from .metrics import score_faculty

    pages = [p.strip() for p in (CASES / "chapter_motion.txt").read_text().split("=== page ===")]
    text = _render(pages, 1, len(pages))
    panel = FacultyPanel()
    result = panel.analyze_chapter("Chapter 1: Motion in One Dimension", 1, len(pages), text)
    plain = "\n\n".join(pages)
    report = score_faculty(result, plain, 1, len(pages))
    report.extra["panel_errors"] = result.errors
    report.extra["tokens"] = {"input": result.input_tokens, "output": result.output_tokens}
    return report, panel.model_id
