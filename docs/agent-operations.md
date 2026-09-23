# Agent operations: safety, state, cost, audit

How the AI agents are kept safe and observable. For what each agent does see
`backend/app/agents/team.py`; for the PDF breakdown agents see
[study-guide.md](study-guide.md).

## Safety properties (enforced by tests)

`backend/tests/unit/test_agent_contracts.py` runs offline in CI (no API key)
and fails if any of these regress:

- Every content-changing tool has `requires_confirmation=True`; only an explicit
  read-only allowlist (`list_quiz_attempts`) may run without a teacher's approval.
- The coordinator's routing instructions name every member by its real delegation id.
- Every agent has a rate-limit fallback (`on_rate_limit`), not only `on_error`.
- Every tool and structured-output schema is free of the shapes Gemini rejects
  (arrays without `items`; schema `default`s on structured outputs).
- Agents that read uploaded material carry the untrusted-text rule (`agents/safety.py`).

These do **not** measure answer quality -- that needs live-model evals (see "Not done").

## Untrusted text

Uploaded PDFs can contain instructions. Two layers:

1. **Prompt rule** (`agents/safety.py`) on the coordinator and every agent that
   handles material: quoted source text is evidence, never instructions. This lowers
   risk; it cannot remove it.
2. **Structural backstop**: content-changing tools need teacher approval, and tools
   take the acting user from the authenticated request, never from model output.

The student TA (`teaching_assistant.py`) treats the student's browser as untrusted:
history is schema-validated (`user`/`assistant` roles, 2000 chars/turn, 40 turns),
only the last 20 turns reach the prompt, and every turn is HTML-escaped inside tags so
a message cannot close its tag or forge an "assistant" turn.

## State

`agents/storage.py` -- one shared Agno store for every agent, the team, and
`chat_history.py`. It holds paused-for-approval runs and Ask AI history, in Postgres
(`AGENT_DB=sqlite` for the old local file). Conversations recorded in the old SQLite
file before this move are not copied over; set `AGENT_DB=sqlite` to read them.

## Cost controls

`app/usage.py` records tokens per user and agent in `agent_usage`.

| Agent | Recorded | Capped |
|---|---|---|
| Teaching Assistant (students) | yes | `TA_DAILY_TOKEN_CAP` per student per UTC day (default 200,000; `0` = off) -> HTTP 429 |
| Faculty panel (teachers' PDF analysis) | yes | no |
| Chat team (AG-UI) | **no** | no |

The cap is checked before a run and recorded after, so concurrent requests can overshoot
by one run.

## Audit trail

Each approved content-changing tool writes one `agent_audit_log` row (tool, target id,
summary) after its change is saved. `GET /api/audit` returns the signed-in teacher's own
entries, newest first. If the audit write fails it is logged as `AUDIT WRITE FAILED` and
the change stands -- the tool doesn't report failure for something that happened.

## Not done

- **Live-model evals.** No golden set for routing or output quality; nothing compares a
  model or prompt change before/after. Needs an API key to run.
- **Chat team usage isn't metered or capped**, and no `tool_call_limit` is set (the
  coordinator's legitimate multi-step drafts couldn't be safely tuned without live runs).
- **Output moderation** for the student TA.
- **Data-processing terms:** feedback and quiz data goes to Gemini; confirm the plan's
  data-use terms suit student data before real use.
