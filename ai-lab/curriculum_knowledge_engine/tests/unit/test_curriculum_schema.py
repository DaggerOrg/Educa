import pytest
from pydantic import ValidationError

from cke.ingestion.curriculum_schema import ConceptSpec, CurriculumSpec, LessonSpec, ModuleSpec


def test_valid_spec_parses():
    spec = CurriculumSpec(
        id="c1",
        title="Course",
        concepts=[ConceptSpec(name="A"), ConceptSpec(name="B", requires=["A"])],
        modules=[
            ModuleSpec(
                id="m1",
                title="Module",
                lessons=[LessonSpec(id="l1", title="Lesson", content="content", teaches=["A"])],
            )
        ],
    )
    assert spec.concepts[1].requires == ["A"]


def test_concept_requiring_unknown_concept_is_rejected():
    with pytest.raises(ValidationError, match="unknown concept"):
        CurriculumSpec(
            id="c1",
            title="Course",
            concepts=[ConceptSpec(name="A", requires=["Nonexistent"])],
        )


def test_lesson_teaching_unknown_concept_is_rejected():
    with pytest.raises(ValidationError, match="unknown concept"):
        CurriculumSpec(
            id="c1",
            title="Course",
            concepts=[ConceptSpec(name="A")],
            modules=[
                ModuleSpec(
                    id="m1",
                    title="Module",
                    lessons=[
                        LessonSpec(id="l1", title="Lesson", content="content", teaches=["Nonexistent"])
                    ],
                )
            ],
        )


def test_from_file_loads_yaml(tmp_path):
    yaml_content = """
id: c1
title: Course From File
concepts:
  - name: A
modules:
  - id: m1
    title: Module
    lessons:
      - id: l1
        title: Lesson
        content: Some content here.
        teaches: [A]
"""
    path = tmp_path / "spec.yaml"
    path.write_text(yaml_content)

    spec = CurriculumSpec.from_file(path)
    assert spec.title == "Course From File"
    assert spec.modules[0].lessons[0].teaches == ["A"]


def test_from_file_loads_json(tmp_path):
    import json

    data = {
        "id": "c1",
        "title": "Course From JSON",
        "concepts": [{"name": "A"}],
    }
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(data))

    spec = CurriculumSpec.from_file(path)
    assert spec.title == "Course From JSON"


def test_sample_curriculum_file_is_valid():
    from cke.config import get_settings

    spec = CurriculumSpec.from_file(get_settings().sample_curriculum_path)
    assert spec.id == "ai-engineering-foundations"
    assert len(spec.concepts) > 10
    assert len(spec.modules) >= 5
