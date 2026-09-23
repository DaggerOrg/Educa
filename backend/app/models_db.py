"""SQLAlchemy ORM models for the entities in docs/entity-diagram/README.md
that were previously either in-memory dicts (User, Course/Module/Lesson)
or only speced, not built (Enrollment, Quiz/QuizItem/QuizAttempt/Response).

`Quiz`/`QuizItem` implement the entity diagram's "proposed assessment
fix": a `Quiz` row is immutable once created -- `quiz.py`'s
`generate_lesson_quiz` tool creates a new `Quiz` (new version) rather than
editing an existing one, so a `QuizAttempt` always grades against the
exact item set a student saw. `QuizAttempt`/`Response` are written once at
submission and never recomputed (see `record_quiz_attempt` in app/store.py).

Slides stay embedded as a JSON column on `Lesson`, same shape as today's
in-memory `Lesson.content.slides[]` -- normalizing `Slide` into its own
table isn't needed for anything this phase does.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("user"))
    email: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str]
    password_hash: Mapped[str]
    role: Mapped[str]  # "teacher" | "student"


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("course"))
    teacher_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str]
    audience: Mapped[str] = mapped_column(default="")
    created_at: Mapped[datetime] = mapped_column(default=_now)

    modules: Mapped[list["Module"]] = relationship(
        back_populates="course", order_by="Module.week_number", cascade="all, delete-orphan"
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="course", cascade="all, delete-orphan")


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("module"))
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"))
    week_number: Mapped[int]
    title: Mapped[str]

    course: Mapped["Course"] = relationship(back_populates="modules")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="module", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("lesson"))
    module_id: Mapped[str] = mapped_column(ForeignKey("modules.id"))
    title: Mapped[str]
    objective: Mapped[str] = mapped_column(default="")
    slides: Mapped[list | None] = mapped_column(JSON, default=None)
    speaker_notes: Mapped[str | None] = mapped_column(default=None)
    approved: Mapped[bool] = mapped_column(default=False)
    published: Mapped[bool] = mapped_column(default=False)

    module: Mapped["Module"] = relationship(back_populates="lessons")
    quizzes: Mapped[list["Quiz"]] = relationship(back_populates="lesson", cascade="all, delete-orphan")
    exercises: Mapped[list["LessonExercise"]] = relationship(back_populates="lesson", cascade="all, delete-orphan")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("course_id", "student_id", name="uq_enrollment_course_student"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("enrollment"))
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(default="active")
    enrolled_at: Mapped[datetime] = mapped_column(default=_now)

    course: Mapped["Course"] = relationship(back_populates="enrollments")


class Quiz(Base):
    """Immutable once created -- regenerating a lesson's quiz inserts a new
    row with `version = previous + 1` rather than editing this one. The
    "current" quiz for a lesson is the highest-`version` row."""

    __tablename__ = "quizzes"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("quiz"))
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"))
    version: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=_now)

    lesson: Mapped["Lesson"] = relationship(back_populates="quizzes")
    items: Mapped[list["QuizItem"]] = relationship(back_populates="quiz", cascade="all, delete-orphan")


class QuizItem(Base):
    __tablename__ = "quiz_items"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("quizitem"))
    quiz_id: Mapped[str] = mapped_column(ForeignKey("quizzes.id"))
    kind: Mapped[str] = mapped_column(default="multiple_choice")
    prompt: Mapped[str]
    options: Mapped[list] = mapped_column(JSON)
    correct_answer: Mapped[int] = mapped_column(JSON)  # 0-based index into options, for kind="multiple_choice"

    quiz: Mapped["Quiz"] = relationship(back_populates="items")


class LessonExercise(Base):
    """The Exercises Builder feature -- deliberately its own table rather
    than another `QuizItem`. `Quiz` is version-immutable and
    `_current_quiz_item` in app/store.py always reads the highest-version
    row as "the" lesson quiz; if exercises_agent's output shared that
    relationship it would collide with quiz_agent's own versions and could
    silently replace the quiz students see. Exercises instead just
    accumulate here, one row per generated item, never versioned.

    `options`/`correct_answer` are used for kind in ("multiple_choice",
    "true_false"); `back` is used for kind == "flashcard". Exactly one of
    the two pairs is populated per row, enforced by
    agents/exercises/tools.py's `ExerciseDraft` validator, not by a DB
    constraint (same "validate in the Pydantic tool model" convention as
    `QuizDraft`)."""

    __tablename__ = "lesson_exercises"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("exercise"))
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"))
    kind: Mapped[str]
    prompt: Mapped[str]
    options: Mapped[list | None] = mapped_column(JSON, default=None)
    correct_answer: Mapped[int | None] = mapped_column(JSON, default=None)
    back: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    lesson: Mapped["Lesson"] = relationship(back_populates="exercises")


class CreativeAsset(Base):
    """AI Creative: a personal, cross-course media library -- deliberately
    not tied to a Course/Lesson, unlike LessonExercise. `storage_path` is a
    relative path under backend/tmp/creative_uploads/ (see app/creative.py);
    the row is metadata, the bytes live on disk, same "no external blob
    storage dependency" spirit as the rest of this prototype."""

    __tablename__ = "creative_assets"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("asset"))
    teacher_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str]  # "image" | "video"
    filename: Mapped[str]
    content_type: Mapped[str]
    storage_path: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=_now)


class TeacherPersona(Base):
    """One per teacher: an enrolled video/voice likeness (a short talking
    clip doubles as both, matching how real avatar providers like HeyGen
    actually ask for training data) plus an explicit consent timestamp.
    No avatar-rendering provider is wired up (see app/persona.py) -- the
    frontend shows a clearly-labeled mock playback, same honest split as
    AI Creative's "Generate"."""

    __tablename__ = "teacher_personas"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("persona"))
    teacher_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    name: Mapped[str]
    training_asset_id: Mapped[str] = mapped_column(ForeignKey("creative_assets.id"))
    consented_at: Mapped[datetime]
    created_at: Mapped[datetime] = mapped_column(default=_now)


class TeachingAssistant(Base):
    """One per course: a teacher-authored AI persona (name + instructions)
    that students chat with -- see app/teaching_assistant.py. Unlike
    TeacherPersona this is a real, working feature (a plain text chat via
    a freshly-built Agno Agent per request, not routed through the
    teacher-only /agui team) -- no rendering provider needed."""

    __tablename__ = "teaching_assistants"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("ta"))
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"), unique=True)
    teacher_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str]
    instructions: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=_now)


class QuizAttempt(Base):
    """Written once at submission -- `score`/`max_score` are stored facts,
    never recomputed if `QuizItem.correct_answer` changes later (it won't,
    since `Quiz` is immutable, but a new attempt against a newer `Quiz`
    version is a separate row, not an edit to this one)."""

    __tablename__ = "quiz_attempts"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("attempt"))
    quiz_id: Mapped[str] = mapped_column(ForeignKey("quizzes.id"))
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    score: Mapped[int]
    max_score: Mapped[int]
    submitted_at: Mapped[datetime] = mapped_column(default=_now)
    # Written after the fact by feedback_agent (see agents/feedback/tools.py)
    # or a teacher -- unlike score/max_score this can be edited/re-set, it's
    # commentary, not a graded fact the "written once" note above protects.
    feedback: Mapped[str | None] = mapped_column(default=None)

    responses: Mapped[list["Response"]] = relationship(back_populates="attempt", cascade="all, delete-orphan")


class Response(Base):
    __tablename__ = "responses"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("response"))
    attempt_id: Mapped[str] = mapped_column(ForeignKey("quiz_attempts.id"))
    item_id: Mapped[str] = mapped_column(ForeignKey("quiz_items.id"))
    value: Mapped[int] = mapped_column(JSON)  # selected option index, for kind="multiple_choice"
    is_correct: Mapped[bool]

    attempt: Mapped["QuizAttempt"] = relationship(back_populates="responses")


class KnowledgeGraphBoard(Base):
    """A saved collaborative knowledge-graph board -- metadata only (title,
    who/when). The graph itself (nodes/edges) is never stored here: it lives
    entirely in Liveblocks Storage, in a room whose id is this row's `id`
    (see frontend/src/knowledge-graph/live/LiveKnowledgeGraphCanvas.tsx and
    backend/app/liveblocks_auth.py's `kg-board:*` wildcard grant). This table
    only exists so the "history" sidebar can list/rename/delete boards
    without calling Liveblocks' REST API to enumerate rooms.

    Shared across every teacher account, like the lecturers' chat -- any
    teacher can see, open, and co-edit any board (no per-board ownership/
    permission model yet)."""

    __tablename__ = "knowledge_graph_boards"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("kgboard"))
    title: Mapped[str]
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=_now)


class Listing(Base):
    """A teacher's course, offered for sale to *other* teachers (not
    students -- this is the curriculum marketplace, separate from
    Enrollment/student access). `course_id` points at the seller's own
    live, editable course; buying a listing never touches that course --
    see `Purchase.course_id`, which is a fresh, independent copy owned by
    the buyer (see app/marketplace.py `purchase_listing`)."""

    __tablename__ = "listings"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("listing"))
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"))
    seller_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str]
    description: Mapped[str] = mapped_column(default="")
    price_cents: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    course: Mapped["Course"] = relationship()


class Purchase(Base):
    """Written once, at the (mocked -- no real payment processor yet)
    moment of purchase. `course_id` is a brand-new `Course` row deep-copied
    from `listing.course_id` at that instant, owned by `buyer_id` and reset
    to an unapproved/unpublished draft -- the buyer reviews and publishes
    it to their own students same as any course they wrote themselves.
    `price_cents` is a snapshot of what was actually paid, independent of
    `Listing.price_cents` if the seller changes the price later."""

    __tablename__ = "purchases"
    __table_args__ = (UniqueConstraint("listing_id", "buyer_id", name="uq_purchase_listing_buyer"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("purchase"))
    listing_id: Mapped[str] = mapped_column(ForeignKey("listings.id"))
    buyer_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id"))
    price_cents: Mapped[int]
    purchased_at: Mapped[datetime] = mapped_column(default=_now)


class AgentUsage(Base):
    """Tokens one agent run consumed, attributed to the user who caused it --
    the basis for per-user daily caps (app/usage.py). Only runs this backend
    invokes directly are recorded (the student TA, the faculty panel); the
    chat team runs inside Agno's AG-UI router and isn't metered here."""

    __tablename__ = "agent_usage"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("use"))
    user_id: Mapped[str] = mapped_column(index=True)
    agent: Mapped[str] = mapped_column(index=True)
    model_id: Mapped[str | None] = mapped_column(default=None)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=_now, index=True)


class AgentAuditLog(Base):
    """One row per content-changing agent action a teacher approved -- what
    was changed, by which tool, on whose behalf. Written by the tool itself
    after its change is saved (app/audit.py), so a row exists only for
    actions that really happened."""

    __tablename__ = "agent_audit_log"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: _id("aud"))
    user_id: Mapped[str] = mapped_column(index=True)
    action: Mapped[str]  # the tool name, e.g. "generate_lesson_quiz"
    target_id: Mapped[str | None] = mapped_column(default=None)
    summary: Mapped[str] = mapped_column(default="")
    created_at: Mapped[datetime] = mapped_column(default=_now, index=True)
