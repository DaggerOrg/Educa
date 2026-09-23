"""Read access to the curriculum agent's past conversations, so a teacher
can browse and resume a prior Ask AI thread instead of losing it once the
chat drawer closes -- see agents/storage.py for where
Agno actually persists these (agno_sessions/agno_runs).

Ownership: a session only shows up in a teacher's history once
`request.state.user_id` (set by auth/context.py's `set_current_user`) has
tagged it at creation. Sessions created before that wiring existed carry
`user_id=NULL` ("unowned" per Agno's own `assert_session_writable`) and
simply don't appear in anyone's history -- there's no real owner to
attribute them to.
"""
from agno.db.base import SessionType

from .agents.storage import build_agent_db

_TEAM_ID = "curriculum-team"

_TITLE_MAX_CHARS = 80

# CopilotKit's `useConfigureSuggestions` (App.tsx) fires its own hidden agent
# run after every real turn to compute the "what to ask next" chips -- it
# shows up in Agno's session history exactly like a real turn (its own
# run, its own synthesized "user" instruction text), but a teacher never
# typed it and never saw it, so it must never surface as a chat bubble.
# `delegate_task_to_member` is the team's own internal hand-off call, not
# something generated for the teacher either.
_SUGGEST_TOOL = "copilotkitSuggest"
_INTERNAL_TOOLS = {_SUGGEST_TOOL, "delegate_task_to_member"}

# The AG-UI transport (agent.addMessage + copilotkit.runAgent -- see
# Home.tsx/App.tsx) never populates Agno's own `run.input.input_content`;
# the teacher's actual text ends up as the last "user" message in
# `run.messages`, followed by a JSON blob of UI-state context the frontend
# appends to every turn (see App.tsx's useAgentContext). Strip that suffix
# off before showing it back.
_CONTEXT_MARKER = "\n\n<additional context>"

_TOOL_LABELS = {
    "create_syllabus": "Created the course syllabus",
    "update_syllabus": "Updated the course syllabus",
    "generate_lesson_slides": "Generated lesson slides",
    "generate_lesson_quiz": "Generated a lesson quiz",
    "generate_lesson_exercises": "Generated lesson exercises",
}


def _db():
    # The same store agents/team.py's Team(db=...) writes to (agents/storage.py).
    return build_agent_db()


def _is_top_level(run) -> bool:
    # A delegated specialist (quiz-agent, lesson-content-agent, ...) gets its
    # own row in `session.runs` too, tagged with the top-level run's id as
    # `parent_run_id` -- only a `parent_run_id is None` run was actually
    # caused directly by something the teacher typed.
    return getattr(run, "parent_run_id", None) is None


def _real_tool_names(run) -> list[str]:
    return [t.tool_name for t in (getattr(run, "tools", None) or []) if t.tool_name not in _INTERNAL_TOOLS]


def _is_suggestion_only(run) -> bool:
    tools = getattr(run, "tools", None) or []
    return bool(tools) and all(t.tool_name == _SUGGEST_TOOL for t in tools)


def _human_text(run) -> str:
    if run.input and run.input.input_content:
        return run.input.input_content.strip()
    for message in reversed(run.messages or []):
        if message.role == "user":
            content = message.content or ""
            idx = content.find(_CONTEXT_MARKER)
            return (content[:idx] if idx != -1 else content).strip()
    return ""


def _describe_tool_call(tool) -> str | None:
    """A best-effort, human-readable summary of a generative tool call.

    The approval card a teacher saw live (a drafted quiz question, slide
    deck, or syllabus) is real UI built client-side from the tool call's
    *arguments* -- the run's own reply text is often empty, since the
    content lives in the call, not a message. Without this, that turn would
    just go silent when the teacher scrolls back to it."""
    name = tool.tool_name
    args = tool.tool_args or {}
    if name == "generate_lesson_quiz":
        question = (args.get("quiz") or {}).get("question")
        return f'Generated a lesson quiz: "{question}"' if question else _TOOL_LABELS[name]
    if name == "generate_lesson_slides":
        headings = [s["heading"] for s in (args.get("slides") or []) if s.get("heading")]
        count = len(args.get("slides") or [])
        return f"Generated {count} lesson slide(s)" + (": " + ", ".join(headings) if headings else "")
    if name == "generate_lesson_exercises":
        return f"Generated {len(args.get('exercises') or [])} exercise(s)"
    if name in ("create_syllabus", "update_syllabus"):
        weeks = args.get("weeks") or []
        title = args.get("title")
        suffix = f" — {title}" if title else ""
        return f"{_TOOL_LABELS[name]}{suffix} ({len(weeks)} week{'s' if len(weeks) != 1 else ''})"
    return _TOOL_LABELS.get(name, name.replace("_", " ").capitalize())


def _has_real_content(session) -> bool:
    return any(_is_top_level(r) and not _is_suggestion_only(r) for r in (session.runs or []))


def _title_for(session) -> str:
    # Same ordering caveat as get_session_transcript: sort before picking
    # the *actual* first turn, not just whichever happens to come back first.
    for run in sorted(session.runs or [], key=lambda r: r.created_at):
        if not _is_top_level(run) or _is_suggestion_only(run):
            continue
        text = _human_text(run)
        if text:
            return text[:_TITLE_MAX_CHARS] + ("…" if len(text) > _TITLE_MAX_CHARS else "")
    return "New conversation"


def list_my_sessions(user_id: str) -> list[dict]:
    sessions = _db().get_sessions(
        session_type=SessionType.TEAM,
        user_id=user_id,
        component_id=_TEAM_ID,
        sort_by="created_at",
        sort_order="desc",
    )
    return [
        {"id": s.session_id, "title": _title_for(s), "createdAt": s.created_at, "updatedAt": s.updated_at}
        for s in sessions
        # Drop sessions that only ever ran a hidden copilotkitSuggest call --
        # nothing a teacher would recognize as "a conversation" ever happened
        # in them, so listing them is pure clutter (about a fifth of all
        # sessions, in practice).
        if _has_real_content(s)
    ]


def get_session_transcript(user_id: str, session_id: str) -> list[dict] | None:
    """Returns `[{role, content}, ...]`, one entry per real teacher turn and
    one per the team's reply to it -- not the raw message log (which also
    holds the system prompt, tool-call/tool-result messages, hidden
    suggestion-generation runs, and per-specialist member sub-runs that
    aren't useful to show as a transcript on their own). Returns `None` for
    a missing session or one this teacher doesn't own, so the route can turn
    either into a plain 404."""
    session = _db().get_session(session_id=session_id, session_type=SessionType.TEAM)
    if not session or session.user_id != user_id:
        return None

    # `session.runs` isn't returned in chronological order -- sort explicitly
    # rather than trust insertion/storage order.
    all_runs = sorted(session.runs or [], key=lambda r: r.created_at)
    children_by_parent: dict[str, list] = {}
    for run in all_runs:
        parent_id = getattr(run, "parent_run_id", None)
        if parent_id:
            children_by_parent.setdefault(parent_id, []).append(run)

    turns = []
    for run in all_runs:
        if not _is_top_level(run) or _is_suggestion_only(run):
            continue

        human = _human_text(run)
        if human:
            turns.append({"role": "user", "content": human})

        lines = []
        content = run.get_content_as_string()
        if content:
            lines.append(content)
        else:
            for name in dict.fromkeys(_real_tool_names(run)):
                lines.append(_TOOL_LABELS.get(name, name.replace("_", " ").capitalize()))

        # Surface what any delegated specialist actually produced (see
        # _describe_tool_call) so an approval card the teacher saw live isn't
        # simply missing from a resumed/browsed transcript. A retried tool
        # call (same specialist call twice in one run) would otherwise show
        # its summary twice -- dedupe on the rendered text itself.
        for child in sorted(children_by_parent.get(run.run_id, []), key=lambda r: r.created_at):
            for tool in getattr(child, "tools", None) or []:
                if tool.tool_name in _INTERNAL_TOOLS:
                    continue
                description = _describe_tool_call(tool)
                if description and description not in lines:
                    lines.append(description)

        if lines:
            turns.append({"role": "assistant", "content": "\n".join(lines)})

    return turns
