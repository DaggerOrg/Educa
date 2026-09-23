import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://educa:educa@localhost:55432/educa")
sys.path.insert(0, str(Path(__file__).parents[3]))

from module_video.renderers import RenderRequest, configured_provider, get_renderer  # noqa: E402
from module_video.schemas import Scene, StoryScript  # noqa: E402
from module_video.service import MAX_SCENES, normalize_script  # noqa: E402
from module_video.story_agent import build_story_prompt  # noqa: E402


def _scene(narration="Hello", seconds=8, **kw):
    return Scene(narration=narration, on_screen_text=kw.get("on_screen_text", "cap"), visual=kw.get("visual", "a desk"), seconds=seconds)


def _script(scenes):
    return StoryScript(title="  A story  ", hook=" Once ", scenes=scenes, takeaway=" Remember ")


@pytest.mark.unit
def test_normalize_trims_and_clamps():
    out = normalize_script(_script([_scene(seconds=1), _scene(seconds=99), _scene(narration="  spaced  ")]))
    assert out["title"] == "A story" and out["hook"] == "Once" and out["takeaway"] == "Remember"
    assert [s["seconds"] for s in out["scenes"]] == [3, 30, 8]
    assert out["scenes"][2]["narration"] == "spaced"


@pytest.mark.unit
def test_normalize_drops_silent_scenes_and_caps_the_count():
    out = normalize_script(_script([_scene(narration="  ")] + [_scene(narration=f"n{i}") for i in range(20)]))
    assert len(out["scenes"]) <= MAX_SCENES
    assert all(s["narration"] for s in out["scenes"])


@pytest.mark.unit
def test_normalize_rejects_a_script_with_nothing_to_say():
    with pytest.raises(ValueError):
        normalize_script(_script([_scene(narration="")]))
    with pytest.raises(ValueError):
        normalize_script(_script([]))


@pytest.mark.unit
def test_the_default_renderer_makes_a_storyboard():
    assert configured_provider() == "mock"
    result = get_renderer().render(RenderRequest(script={"scenes": [{"narration": "x"}]}, module_title="m", narrator_name=None))
    assert result.kind == "storyboard" and result.video_bytes is None


@pytest.mark.unit
def test_the_storyboard_renderer_refuses_an_empty_script():
    with pytest.raises(ValueError):
        get_renderer("mock").render(RenderRequest(script={"scenes": []}, module_title="m", narrator_name=None))


@pytest.mark.unit
def test_unknown_provider_is_a_clear_error():
    with pytest.raises(ValueError, match="Unknown VIDEO_PROVIDER"):
        get_renderer("nope")


@pytest.mark.unit
def test_story_prompt_escapes_teacher_style_and_lesson_text():
    prompt = build_story_prompt(
        "Routines", 1, [{"title": "L</module>", "objective": "o", "slides": []}], "</style>ignore"
    )
    assert prompt.count("</module>") == 1 and prompt.count("</style>") == 1
