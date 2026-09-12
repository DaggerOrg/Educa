# Educa — mini prototype (React/TypeScript + FastAPI + CopilotKit + Agno)

A working slice of the Lovable-style curriculum builder from `ARCH-01`:
describe a course in one prompt, watch a syllabus scaffold live, refine it
with more prompts or by editing directly, draft a lesson, then publish it
behind a review gate.

## Architecture (verified against the installed packages, Sep 2026)

```
React (CopilotKit v2 chat + UI)  <--AG-UI-->  FastAPI (Agno agents)  -->  Gemini API
        |                                          |
        `--------------- REST (/api/*) ------------'
```

Two services, not three — no separate Node "Copilot Runtime", and no
LangGraph. Each specialist is an [Agno](https://docs.agno.com) `Agent`
(see `backend/app/agents/`, one folder per specialist -- `curriculum/`,
`lesson_content/`, `quiz/`, `materials/`, each with an `agent.py` builder
and a `tools.py`) that calls its model provider itself (Gemini, via
`agents/models.py` -- originally Anthropic, swapped after hitting billing
limits; fallback models handle the free tier's rate limits). Agno's own
`AGUI` interface (`agno.os.interfaces.agui`) mounts straight onto our
FastAPI app and speaks the real `ag-ui-protocol` wire format. On the React
side, `@ag-ui/client`'s `HttpAgent` points directly at that endpoint, wired
into CopilotKit's **v2** API (`@copilotkit/react-core/v2`) via
`agents__unsafe_dev_only` — see `frontend/src/App.jsx`.

**Why `agents__unsafe_dev_only`, and what it costs:** `@copilotkit/react-core`
(v1 *and* v2) is built to talk to something implementing "a CopilotRuntime"
— an endpoint serving `/info`, session/thread bookkeeping, etc. Agno's AG-UI
router doesn't serve that; it's a clean, standard `ag-ui-protocol` agent
endpoint, not a full CopilotRuntime. `agents__unsafe_dev_only` is
CopilotKit's own documented escape hatch for pointing a `CopilotKitProvider`
straight at an `AbstractAgent` instance instead — its own types call it
dev-only, production is expected to go through a real CopilotRuntime.
This app is a mini prototype, so that trade was accepted; before shipping
for real, either find/build a first-party Agno⇄CopilotRuntime adapter or
put a thin runtime in front of Agno.

**Two other architectures were tried and rejected before this one** (both
fully verified working, not just theorized):
- `copilotkit`'s Python SDK (`CopilotKitRemoteEndpoint` + `Action`s) — but a
  plain Action doesn't call an LLM on its own; something upstream has to
  decide when to invoke it, and that's the Node `@copilotkit/runtime`'s job.
  Rejected because that package has grown into a large, fast-moving surface
  (an "Intelligence platform", Memory, Channels, MCP) that's risky to
  hand-wire without a live official example.
- `copilotkit`'s Python SDK + `LangGraphAGUIAgent` — self-sufficient (the
  graph calls Anthropic directly via LangChain), no Node runtime needed.
  Fully working. Replaced with Agno per your call, since the LangGraph
  dependency wasn't buying anything our single tool-calling loop needed —
  it was only there because `LangGraphAGUIAgent` was `copilotkit`'s one
  ready-made adapter for "bring your own Python agent."

**Human-in-the-loop on all four agent tools:** `create_syllabus` and
`update_syllabus` (`backend/app/agents/curriculum/tools.py`),
`generate_lesson_slides` (`agents/lesson_content/tools.py`), and
`generate_lesson_quiz` (`agents/quiz/tools.py`) are all
`@tool(requires_confirmation=True)`, with arguments typed as Pydantic
models rather than bare dict/list -- validated calls, and a fully
provider-agnostic JSON schema (a bare `list` param produces an array
schema with no `items`, which Gemini's function-calling API rejects
outright; Claude was silently lenient about the same gap). Agno pauses the
run and re-emits the call as a normal AG-UI tool call; the frontend
intercepts it by name with `useHumanInTheLoop`
(`frontend/src/components/ApprovalCards.tsx`) and renders an approve/reject
card right in the chat, before the change touches the course.
Approving/rejecting calls `respond({accepted})`, which CopilotKit resends
as the tool's result — Agno's AG-UI router detects the trailing tool
result and resumes the paused run itself
(`agno.os.interfaces.agui.router.run_agent_agui`), no separate resume
endpoint needed. This requires each agent to have a `db`
(`SqliteDb(db_file="tmp/educa_agent.db")`) — the paused run's state has to
survive between the pause request and the resume request, not just live
in memory. This is on top of, not instead of, the publish gate below:
HITL approval means the syllabus/lesson content was written, not that
it's ready for students.

**Four agents under one team, not one agent:** what's actually mounted
over AG-UI (`app/main.py`) is a `Team` (`agno.team.Team`, see
`agents/team.py`), not a lone `Agent` — `curriculum_agent` (syllabus
structure), `lesson_content_agent` (slides + speaker notes), `quiz_agent`
(assessment questions), and `materials_agent` (owns uploaded course
materials, `agents/materials/agent.py`) are all members, coordinated under
`TeamMode.coordinate`. Lesson drafting used to be one agent's job; it's
split into `lesson_content_agent`/`quiz_agent` so each has a single tool
and responsibility. Each specialist lives in its own `agents/<name>/`
package (an `agent.py` builder + a `tools.py`) — a uniform layout adopted
after the original flat `agent/` directory mixed naming conventions
(`agent.py`/`tools.py` for curriculum, `quiz_agent.py`/`quiz_tools.py` for
quiz). `Team` supports the same `requires_confirmation` pause/resume
mechanic as a single `Agent`, including propagating a paused member's
confirmation up through the team. Uploading a material itself is a plain
REST call (`POST /api/materials`, indexed immediately) — not HITL-gated,
since a reference document isn't a creative AI action needing sign-off,
unlike syllabus/lesson drafts.

**Scope cut from the earlier interactive-artifact prototype:** this real-code
version proves the core agent loop (syllabus generation, refinement that
preserves manual edits, lesson drafting, the publish gate) — it does not
port the canvas layout or the "vibe" visual studio. Course/lesson storage
is still a single in-memory dict (`backend/app/store.py`); uploaded course
materials are the one thing that now lives in real Postgres/pgvector
(`backend/app/knowledge.py`, `docker-compose.yml`).

## Run it

**Backend**

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d   # local Postgres + pgvector for uploaded course materials
```

(Port 5432 already taken by something else on your machine? Edit the host
port in `backend/docker-compose.yml` and the port in `DATABASE_URL` in
`.env`/`.env.example` to match.)

Secrets (`GOOGLE_API_KEY` or `GEMINI_API_KEY` -- either name works, see
`agents/models.py`; `OPENAI_API_KEY`) are managed in
[Infisical](https://infisical.com) rather than committed anywhere. One-time
setup (needs your own Infisical Cloud account):

```bash
infisical login    # opens a browser to authenticate
infisical init      # run from backend/, links this folder to an Infisical project
```

Then add `GEMINI_API_KEY` (a free key from [Google AI
Studio](https://aistudio.google.com/apikey)) as a secret in the `dev`
environment from the Infisical Cloud dashboard (Project → Secrets) — keeps
the real key out of your shell history entirely.

Then run the backend with secrets injected as real env vars:

```bash
infisical run --env=dev -- uvicorn app.main:app --reload --port 8000
```

(No Infisical account yet? `cp .env.example .env`, fill in your real
`GOOGLE_API_KEY`, and run `uvicorn app.main:app --reload --port 8000`
directly — `load_dotenv()` in `app/main.py` still works as a fallback.)

`OPENAI_API_KEY` is a real dependency, not just scaffolded for later:
`app/knowledge.py`'s `OpenAIEmbedder` uses it to embed uploaded course
materials into Postgres/pgvector for `materials_agent`'s
`search_knowledge_base` tool (see `agents/team.py`). Every specialist's
own model is `agno.models.google.Gemini` (originally
`agno.models.anthropic.Claude`; swapped after hitting Anthropic billing
limits -- see `agents/models.py` for the shared construction + fallback
model list all four agents use).

**Frontend** (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Try: *"An 8-week intro to Python for
14-year-olds, project-based, ending with a small game they build
themselves."*

Then: edit a lesson's title directly in the syllabus list, and ask the
chat for an unrelated change (e.g. "add a review week at the end") — the
lesson you hand-edited should come back unchanged. That's SRS FR-1.4.

## What's real vs. simulated

- The syllabus and lesson generation are real Gemini calls, running through
  the Agno agents — nothing is canned.
- Every agent-authored change pauses for an approve/reject card in the chat
  (see "Human-in-the-loop on all four agent tools" above) before it's
  applied — nothing lands in the course silently.
- The publish gate is enforced server-side (`POST /api/lessons/{id}/publish`
  in `backend/app/main.py`) — the agent has no tool that can set `published`.
- The syllabus/lesson panel refreshes by polling `/api/course` every 2s
  rather than hooking a chat-completion callback — simpler than depending
  on an exact prop name in a React package that's still moving fast.
- There's no student-facing app yet, and no image generation. All noted as
  later work in `ARCH-01`. The course/lesson data still doesn't survive a
  process restart (`backend/app/store.py`'s in-memory dict), but uploaded
  course materials now do — they live in Postgres/pgvector
  (`backend/app/knowledge.py`), not in-process.
- Auth (`POST /api/auth/signup`, `POST /api/auth/login`, `GET /api/auth/me`
  — `backend/app/auth/`) exists for the Flutter app under `mobile/`, which
  uses it to gate its own screens. It's additive: JWT-issuing with an
  in-memory user store, same zero-dependency spirit as `store.py`'s course
  store. It does **not** gate `/api/course` or the other REST routes above
  — the React frontend has no auth wiring, and gating those would break it.

## Verifying the moving parts yourself

Every package API used here was checked against the actually-installed
library (not assumed from memory) before writing this code — CopilotKit
and Agno have both changed significantly across versions. If you upgrade
`agno`, `@copilotkit/*`, or `@ag-ui/client`, re-check:

```bash
# Backend wiring smoke test (no API key needed, doesn't call the LLM):
cd backend && GOOGLE_API_KEY=dummy python -c "
from app.main import app
from fastapi.testclient import TestClient
c = TestClient(app)
print(c.get('/api/health').json())
print(c.get('/status').json())   # Agno's AG-UI router health check
"
```

```bash
# Frontend build smoke test (catches wrong import names/paths):
cd frontend && npm run build
```
