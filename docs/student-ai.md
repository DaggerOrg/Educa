# Student notes, AI helpers and module story videos

Three student/teacher features that share one pattern: a small backend package
on the shared SQLAlchemy `Base`, structured LLM output through
`app/agents/structured.py::run_structured`, and a per-user daily token cap in
`app/usage.py`.

| Feature | Backend | Frontend |
|---|---|---|
| Notes (Tiptap text + Excalidraw sketch), ambient note suggestions, AI helpers | `backend/student_ai/` | `frontend/src/notes/` |
| Module story videos (script → approve → render) | `backend/module_video/` | `frontend/src/story/` |

Tables (created by `init_db()`): `student_notes`, `module_videos`.

## Notes and ambient suggestions (student side)

The lesson page has a **My notes** button that opens a right-hand panel with
three tabs: Notes (Tiptap), Sketch (Excalidraw, lazy-loaded) and AI helpers.
The text and the sketch are saved separately, debounced, one row per
(student, lesson).

**Ambient suggestion.** After the student types a title-like line ("What is
present tense") and pauses about a second, with nothing written beneath it, the
client asks `POST .../notes/suggest`. A card offers summary, key points and an
example; **Accept** (or Tab) writes them under the title, **Reject** (or Esc)
dismisses. A rejected title is not asked about again in the session. The
**AI suggestions on/off** switch in the panel header turns the whole thing off;
the choice is stored per user in `localStorage` (default on). A 429 (daily
cap) stops suggestions for the rest of the session.

The suggestion grounds itself in the published lesson when it can and says so
("From your lesson" vs "General knowledge"). Quiz questions and answers are
never sent to any student-side agent.

**AI helpers** (`GET /api/student-ai/agents`, `POST .../assist/{agent}`):
explainer, practice-quiz maker, flashcards, summarizer. Each result has an
**Add to my notes** button.

Access to every student endpoint goes through
`store.get_published_lesson_for_student` (enrolled and published only).

| Route | |
|---|---|
| `GET/PUT /api/courses/{c}/lessons/{l}/notes` | load / save `{doc?, sketch?}` |
| `POST /api/courses/{c}/lessons/{l}/notes/suggest` | `{heading, surrounding}` → suggestion |
| `GET /api/student-ai/agents` | helper catalogue |
| `POST /api/courses/{c}/lessons/{l}/assist/{agent}` | run a helper |

Env: `STUDENT_AI_DAILY_TOKEN_CAP` (default 300000 tokens/user/day).

## Module story videos

A teacher opens **Story video** on a week in Studio. Flow:
`draft → approved → queued → rendering → ready | failed`.

1. **Write the story** – a script agent drafts hook, scenes (narration,
   caption, visual, seconds) and a takeaway from the module's lessons.
2. The teacher edits, saves and **approves** the script. Nothing renders
   before approval, and editing an approved script sends it back to draft.
3. **Render** enqueues `render_module_video` on the RQ queue. The worker must
   be running: `python -m curriculum_ai.jobs.worker`.
4. Students see **Watch story** on the course page once a story is `ready`.

Renderers are pluggable (`module_video/renderers/`, chosen by
`VIDEO_PROVIDER`, default `mock`). The **mock renderer produces a storyboard,
not a video**: the player steps through the scenes with captions and optional
browser text-to-speech, and labels itself as a storyboard. A real provider
returns video bytes, which are stored via `curriculum_ai.storage` and served
through an authenticated endpoint. Add a provider by implementing
`VideoRenderer` and registering it.

| Route | |
|---|---|
| `GET/DELETE /api/modules/{m}/story-video` | teacher: read / delete |
| `POST /api/modules/{m}/story-video/script` · `PUT …/script` | draft with AI / save edits |
| `POST …/approve` · `POST …/render` | approve / enqueue render |
| `GET /api/courses/{c}/story-videos` | student: modules with a ready story |
| `GET /api/courses/{c}/modules/{m}/story-video` (+ `/file`) | student: script / video bytes |

Env: `STORY_DAILY_TOKEN_CAP` (default 200000), `VIDEO_PROVIDER`.

## Tests

- Backend: `backend/tests/integration/{student_ai,module_video}/`,
  `backend/tests/unit/{student_ai,module_video}/` (LLM calls are monkeypatched).
- Frontend: `frontend/tests/e2e/student-notes.spec.ts`,
  `frontend/tests/e2e/module-story.spec.ts` (API mocked; run `npx playwright test`).

## Known limits

- On the Gemini free tier the primary model allows about 20 requests a day, so
  heavy note-taking falls through to the fallback models and then to the daily cap.
- Excalidraw loads its fonts from a CDN.
- Sketches store drawn elements only; the image tool is disabled because
  embedded images live in a separate file map that is not stored.
