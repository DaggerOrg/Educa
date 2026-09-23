"""Module story videos end to end against the real app and Postgres. The model
call and the job queue are replaced (a recorder and a fake queue) so no LLM
or worker is involved; the render job itself is called directly, the way a
worker would."""

import pytest

from module_video import renderers, service
from module_video.models import ModuleVideo, VideoStatus
from module_video.render import render_module_video
from module_video.renderers.base import RenderedVideo
from module_video.schemas import Scene, StoryScript
from app.db.session import SessionLocal


def _script(n=3, title="The habit story"):
    return StoryScript(
        title=title,
        hook="Ever notice how Sam's mornings never change?",
        scenes=[
            Scene(narration=f"Scene {i}: Sam wakes up and brushes his teeth.", on_screen_text="Sam's routine", visual="a bathroom", seconds=8)
            for i in range(n)
        ],
        takeaway="We use the simple present for routines.",
    )


class FakeQueue:
    def __init__(self):
        self.jobs = []
        self.fail = False

    def enqueue(self, fn, *args, **kwargs):
        if self.fail:
            from redis.exceptions import ConnectionError as RedisConnectionError

            raise RedisConnectionError("redis is down")
        self.jobs.append((fn, args, kwargs))


@pytest.fixture
def fakes(monkeypatch):
    queue = FakeQueue()
    calls = []

    def fake_run_structured(*, agent_name, user_id, instructions, prompt, output):
        calls.append({"prompt": prompt, "user": user_id})
        return _script()

    monkeypatch.setattr(service, "run_structured", fake_run_structured)
    monkeypatch.setattr(service, "get_queue", lambda: queue)
    return {"queue": queue, "model_calls": calls}


def _api(world, suffix=""):
    return f"/api/modules/{world['module_id']}/story-video{suffix}"


def _row(world):
    with SessionLocal() as session:
        return session.query(ModuleVideo).filter_by(module_id=world["module_id"]).one()


def _ready_story(client, world, fakes):
    """Drive a story to READY through the API + the render job."""
    headers = world["teacher"]["headers"]
    client.post(_api(world, "/script"), headers=headers, json={})
    client.post(_api(world, "/approve"), headers=headers)
    client.post(_api(world, "/render"), headers=headers)
    _, (video_id, job_id), _ = fakes["queue"].jobs[-1]
    render_module_video(video_id, job_id)
    return video_id, job_id


# ---- script ----------------------------------------------------------------------


@pytest.mark.integration
def test_generate_script_writes_a_draft_from_the_modules_lessons(client, world, fakes):
    response = client.post(_api(world, "/script"), headers=world["teacher"]["headers"], json={"style": "playful"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft" and len(body["script"]["scenes"]) == 3

    prompt = fakes["model_calls"][0]["prompt"]
    assert "Simple present" in prompt and "We add -s for he/she/it" in prompt and "playful" in prompt
    assert "SECRETQUIZQUESTION" not in prompt  # the quiz never reaches the story writer


@pytest.mark.integration
def test_only_the_owning_teacher_can_touch_a_modules_story(client, world, fakes):
    other = world["other_teacher"]["headers"]
    assert client.post(_api(world, "/script"), headers=other, json={}).status_code == 403
    assert client.get(_api(world), headers=other).status_code == 403
    assert client.get(_api(world), headers=world["student"]["headers"]).status_code == 403  # students: wrong role
    assert fakes["model_calls"] == []


@pytest.mark.integration
def test_unknown_module_is_a_404(client, world, fakes):
    assert client.get("/api/modules/module_nope/story-video", headers=world["teacher"]["headers"]).status_code == 404


@pytest.mark.integration
def test_editing_the_script_normalizes_it_and_returns_it_to_draft(client, world, fakes):
    headers = world["teacher"]["headers"]
    client.post(_api(world, "/script"), headers=headers, json={})
    client.post(_api(world, "/approve"), headers=headers)

    edited = {"script": {"title": " New ", "hook": "h", "takeaway": "t", "scenes": [
        {"narration": " Hi ", "on_screen_text": "x", "visual": "y", "seconds": 500}]}}
    response = client.put(_api(world, "/script"), headers=headers, json=edited)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "draft"
    assert body["script"]["title"] == "New" and body["script"]["scenes"][0]["seconds"] == 30

    empty = {"script": {**edited["script"], "scenes": []}}
    assert client.put(_api(world, "/script"), headers=headers, json=empty).status_code == 400


# ---- approve / render flow ------------------------------------------------------------------


@pytest.mark.integration
def test_cannot_render_before_the_script_is_approved(client, world, fakes):
    headers = world["teacher"]["headers"]
    assert client.post(_api(world, "/render"), headers=headers).status_code == 400  # nothing yet
    client.post(_api(world, "/script"), headers=headers, json={})
    assert client.post(_api(world, "/render"), headers=headers).status_code == 400  # draft
    assert fakes["queue"].jobs == []


@pytest.mark.integration
def test_render_queues_a_job_and_the_job_makes_a_storyboard(client, world, fakes):
    headers = world["teacher"]["headers"]
    client.post(_api(world, "/script"), headers=headers, json={})
    assert client.post(_api(world, "/approve"), headers=headers).json()["status"] == "approved"

    queued = client.post(_api(world, "/render"), headers=headers)
    assert queued.status_code == 200 and queued.json()["status"] == "queued"
    assert client.post(_api(world, "/render"), headers=headers).status_code == 400  # already rendering

    fn, (video_id, job_id), kwargs = fakes["queue"].jobs[0]
    assert fn is render_module_video and kwargs["job_id"] == job_id

    render_module_video(video_id, job_id)
    done = client.get(_api(world), headers=headers).json()
    assert done["status"] == "ready" and done["kind"] == "storyboard"


@pytest.mark.integration
def test_render_job_is_idempotent_and_ignores_stale_job_ids(client, world, fakes):
    headers = world["teacher"]["headers"]
    video_id, job_id = _ready_story(client, world, fakes)
    assert _row(world).status == VideoStatus.READY.value

    render_module_video(video_id, job_id)  # redelivery of a finished job: a no-op
    render_module_video(video_id, "some-other-job")  # a job that isn't the current one: a no-op
    assert _row(world).status == VideoStatus.READY.value

    client.post(_api(world, "/render"), headers=headers)  # re-render -> new job id, back to queued
    render_module_video(video_id, job_id)  # the OLD job id must not claim the new render
    assert _row(world).status == VideoStatus.QUEUED.value


@pytest.mark.integration
def test_editing_while_queued_drops_the_pending_render(client, world, fakes):
    headers = world["teacher"]["headers"]
    client.post(_api(world, "/script"), headers=headers, json={})
    client.post(_api(world, "/approve"), headers=headers)
    client.post(_api(world, "/render"), headers=headers)
    _, (video_id, job_id), _ = fakes["queue"].jobs[0]

    client.put(_api(world, "/script"), headers=headers, json={"script": _script(2).model_dump()})
    render_module_video(video_id, job_id)  # the worker finally gets to the stale job

    row = _row(world)
    assert row.status == VideoStatus.DRAFT.value and row.result is None


@pytest.mark.integration
def test_a_render_failure_is_recorded_and_can_be_retried(client, world, fakes, monkeypatch):
    class Broken:
        key = "broken"

        def render(self, request):
            raise RuntimeError("provider exploded")

    monkeypatch.setitem(renderers._RENDERERS, "broken", Broken)
    monkeypatch.setenv("VIDEO_PROVIDER", "broken")
    headers = world["teacher"]["headers"]
    client.post(_api(world, "/script"), headers=headers, json={})
    client.post(_api(world, "/approve"), headers=headers)
    client.post(_api(world, "/render"), headers=headers)
    _, (video_id, job_id), _ = fakes["queue"].jobs[-1]

    render_module_video(video_id, job_id)
    failed = client.get(_api(world), headers=headers).json()
    assert failed["status"] == "failed" and "provider exploded" in failed["error"]

    monkeypatch.delenv("VIDEO_PROVIDER")
    assert client.post(_api(world, "/render"), headers=headers).json()["status"] == "queued"  # retry allowed


@pytest.mark.integration
def test_queue_outage_marks_the_story_failed_instead_of_leaving_it_queued(client, world, fakes):
    headers = world["teacher"]["headers"]
    client.post(_api(world, "/script"), headers=headers, json={})
    client.post(_api(world, "/approve"), headers=headers)
    fakes["queue"].fail = True

    assert client.post(_api(world, "/render"), headers=headers).status_code == 503
    row = _row(world)
    assert row.status == VideoStatus.FAILED.value and "queue" in row.error


# ---- student side ----------------------------------------------------------------------------------------


@pytest.mark.integration
def test_students_only_see_ready_stories_in_their_own_courses(client, world, fakes):
    student = world["student"]["headers"]
    list_url = f"/api/courses/{world['course_id']}/story-videos"
    watch_url = f"/api/courses/{world['course_id']}/modules/{world['module_id']}/story-video"

    assert client.get(list_url, headers=student).json() == []  # nothing yet
    client.post(_api(world, "/script"), headers=world["teacher"]["headers"], json={})
    assert client.get(watch_url, headers=student).status_code == 404  # a draft isn't visible

    _ready_story(client, world, fakes)
    listed = client.get(list_url, headers=student).json()
    assert [(v["moduleId"], v["kind"], v["title"]) for v in listed] == [(world["module_id"], "storyboard", "Everyday routines")]

    watched = client.get(watch_url, headers=student).json()
    assert watched["kind"] == "storyboard" and len(watched["script"]["scenes"]) == 3
    assert "name" in watched["narrator"]

    outsider = world["other_student"]["headers"]
    assert client.get(list_url, headers=outsider).status_code == 403
    assert client.get(watch_url, headers=outsider).status_code == 403
    assert client.get(list_url, headers=world["teacher"]["headers"]).status_code == 403  # wrong role


@pytest.mark.integration
def test_a_real_video_is_stored_served_to_students_and_cleaned_up(client, world, fakes, monkeypatch, tmp_path):
    import curriculum_ai.storage as storage_module
    from curriculum_ai.storage.local import LocalDiskStorage

    store = LocalDiskStorage(root=tmp_path / "videos")
    monkeypatch.setattr(storage_module, "_storage", store)

    class FakeProvider:
        key = "fake"

        def render(self, request):
            return RenderedVideo(kind="video", video_bytes=b"\x00\x00fake-mp4-bytes", content_type="video/mp4")

    monkeypatch.setitem(renderers._RENDERERS, "fake", FakeProvider)
    monkeypatch.setenv("VIDEO_PROVIDER", "fake")

    _ready_story(client, world, fakes)
    key = _row(world).result["storage_key"]
    assert store.get(key) == b"\x00\x00fake-mp4-bytes"

    file_url = f"/api/courses/{world['course_id']}/modules/{world['module_id']}/story-video/file"
    response = client.get(file_url, headers=world["student"]["headers"])
    assert response.status_code == 200 and response.content == b"\x00\x00fake-mp4-bytes"
    assert response.headers["content-type"] == "video/mp4"
    assert client.get(file_url, headers=world["other_student"]["headers"]).status_code == 403

    assert client.delete(_api(world), headers=world["teacher"]["headers"]).status_code == 200
    with pytest.raises(FileNotFoundError):
        store.get(key)  # the stored file went with the story


@pytest.mark.integration
def test_a_storyboard_has_no_file_to_download(client, world, fakes):
    _ready_story(client, world, fakes)
    file_url = f"/api/courses/{world['course_id']}/modules/{world['module_id']}/story-video/file"
    assert client.get(file_url, headers=world["student"]["headers"]).status_code == 404
