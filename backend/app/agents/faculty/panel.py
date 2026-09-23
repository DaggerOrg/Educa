"""Runs the faculty over one chapter: the three specialists read the chapter
in parallel, then the chair reads their findings and writes the summary.

Takes plain values (title, pages, text), not curriculum_ai's `Unit`, so this
package stays independent of the ingestion pipeline that calls it.

Failure policy: a specialist that errors (after Agno's own model fallbacks)
costs the teacher only that specialist's slice of the chapter -- the other
two still land, and the error is reported in `PanelResult.errors`. Only when
all three fail does `analyze_chapter` raise, so a chapter is never recorded
as analyzed when nothing came back.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import List, Optional

from .agents import build_chair, build_concept_analyst, build_exercise_lecturer, build_theory_professor
from .schemas import (
    ChairSummary,
    ConceptAnalysis,
    ConceptEntry,
    ExerciseBreakdown,
    ExerciseEntry,
    TheoryBreakdown,
    TheoryEntry,
)


class PanelError(RuntimeError):
    pass


@dataclass
class PanelResult:
    concepts: List[ConceptEntry] = field(default_factory=list)
    theories: List[TheoryEntry] = field(default_factory=list)
    exercises: List[ExerciseEntry] = field(default_factory=list)
    chair: Optional[ChairSummary] = None
    errors: List[str] = field(default_factory=list)
    input_tokens: int = 0  # summed over every specialist run that completed; feeds app/usage.py
    output_tokens: int = 0


def _chapter_prompt(title: str, page_start: int, page_end: int, text: str) -> str:
    return f"Chapter: {title} (pages {page_start}-{page_end})\n\n<source_text>\n{text}\n</source_text>"


def _findings_prompt(title: str, result: PanelResult) -> str:
    lines = [f"Chapter: {title}", "<findings>"]
    lines += [f"Concept: {c.name} -- {c.definition}" for c in result.concepts]
    lines += [f"Theory: {t.name} -- {t.statement}" for t in result.theories]
    lines += [f"Exercise ({e.difficulty}): {e.title}" for e in result.exercises]
    lines.append("</findings>")
    return "\n".join(lines)


def _run(agent, schema, prompt: str):
    """Returns (content, input_tokens, output_tokens)."""
    output = agent.run(prompt)
    if not isinstance(output.content, schema):
        raise ValueError(f"{agent.name} did not return a valid {schema.__name__}")
    metrics = getattr(output, "metrics", None)
    return output.content, getattr(metrics, "input_tokens", 0) or 0, getattr(metrics, "output_tokens", 0) or 0


class FacultyPanel:
    """Agents are injectable so the orchestration can be tested without a
    model; by default the real four are built once and reused across
    chapters."""

    def __init__(self, concept_analyst=None, theory_professor=None, exercise_lecturer=None, chair=None):
        self.concept_analyst = concept_analyst or build_concept_analyst()
        self.theory_professor = theory_professor or build_theory_professor()
        self.exercise_lecturer = exercise_lecturer or build_exercise_lecturer()
        self.chair = chair or build_chair()

    @property
    def model_id(self) -> str:
        return getattr(self.concept_analyst.model, "id", "unknown")

    @staticmethod
    def _tally(result: PanelResult, run_output):
        content, input_tokens, output_tokens = run_output
        result.input_tokens += input_tokens
        result.output_tokens += output_tokens
        return content

    def analyze_chapter(self, title: str, page_start: int, page_end: int, text: str) -> PanelResult:
        prompt = _chapter_prompt(title, page_start, page_end, text)
        jobs = {
            "concept_analyst": (self.concept_analyst, ConceptAnalysis),
            "theory_professor": (self.theory_professor, TheoryBreakdown),
            "exercise_lecturer": (self.exercise_lecturer, ExerciseBreakdown),
        }
        result = PanelResult()

        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            futures = {name: pool.submit(_run, agent, schema, prompt) for name, (agent, schema) in jobs.items()}
            outputs = {}
            for name, future in futures.items():
                try:
                    outputs[name] = self._tally(result, future.result())
                except Exception as exc:  # noqa: BLE001 - one specialist failing must not sink the chapter
                    result.errors.append(f"{name}: {type(exc).__name__}: {exc}")

        if not outputs:
            raise PanelError("; ".join(result.errors))

        if "concept_analyst" in outputs:
            result.concepts = outputs["concept_analyst"].concepts
        if "theory_professor" in outputs:
            result.theories = outputs["theory_professor"].theories
        if "exercise_lecturer" in outputs:
            result.exercises = outputs["exercise_lecturer"].exercises

        if result.concepts or result.theories or result.exercises:
            try:
                result.chair = self._tally(result, _run(self.chair, ChairSummary, _findings_prompt(title, result)))
            except Exception as exc:  # noqa: BLE001 - the summary is a nicety; the findings stand without it
                result.errors.append(f"faculty_chair: {type(exc).__name__}: {exc}")
        return result
