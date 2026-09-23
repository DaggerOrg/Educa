"""FastAPI app for Educa.

Mounts Agno's AG-UI router for the curriculum team (the only thing that
calls the LLM) alongside the plain REST routes that own direct edits, the
publish gate, and the student-facing catalog/enrollment/quiz-attempt flow
-- see ARCH-01 SS03/SS09 for why publishing is a dedicated server-side
action the agent cannot call on its own, and docs/entity-diagram/README.md
for the Enrollment/Quiz/QuizAttempt/Response entities this file now
persists via store.py instead of the old single in-memory course.

Every route below (including the AGUI router) requires a real account --
`/api/course`-style routes used to be deliberately open ("the React
frontend has no auth wiring"), but the frontend now does, and courses are
real per-teacher data, not one shared demo course.
"""
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

from agno.os.interfaces.agui import AGUI  # noqa: E402
from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Query, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from . import audit, chat_history, creative, kg_boards, knowledge, liveblocks_auth, marketplace, persona, store, teaching_assistant, usage  # noqa: E402
from .agents.team import build_team  # noqa: E402
from .auth.context import require_role, set_current_user  # noqa: E402
from .auth.routes import router as auth_router  # noqa: E402
from .db import init_db  # noqa: E402
from curriculum_ai.router import router as curriculum_router  # noqa: E402
from module_video.router import router as module_video_router  # noqa: E402
from rag.router import router as rag_router  # noqa: E402
from student_ai.router import router as student_ai_router  # noqa: E402

init_db()

app = FastAPI(title="Educa API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serves POST /agui (run the team, streaming ag-ui-protocol events) and
# GET /status. The React app's HttpAgent (see frontend/src/App.tsx) points
# straight at this. Teacher-only: `require_role("teacher")` also sets the
# contextvar in auth/context.py that the four agent tools read for
# ownership checks (see agents/curriculum/tools.py and friends).
app.include_router(AGUI(team=build_team()).get_router(), dependencies=[Depends(require_role("teacher"))])
app.include_router(auth_router)
app.include_router(rag_router)
app.include_router(curriculum_router)
app.include_router(student_ai_router)
app.include_router(module_video_router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


def _course_or_404(course_id: str) -> dict:
    course = store.get_course(course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    return course


def _owned_or_403(course: dict, user: dict) -> dict:
    if course["teacherId"] != user["id"]:
        raise HTTPException(403, "You don't own this course")
    return course


# ---- Teacher routes ---------------------------------------------------

teacher = APIRouter(prefix="/api")


@teacher.get("/courses/mine")
def list_my_courses(user: dict = Depends(require_role("teacher"))):
    return store.list_courses_for_teacher(user["id"])


@teacher.get("/courses/{course_id}")
def get_my_course(course_id: str, user: dict = Depends(require_role("teacher"))):
    return _owned_or_403(_course_or_404(course_id), user)


class LessonEdit(BaseModel):
    title: str | None = None
    objective: str | None = None


@teacher.patch("/lessons/{lesson_id}")
def edit_lesson(lesson_id: str, body: LessonEdit, user: dict = Depends(require_role("teacher"))):
    try:
        lesson = store.edit_lesson(lesson_id, user["id"], body.title, body.objective)
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    return lesson


class ApprovalUpdate(BaseModel):
    approved: bool


@teacher.patch("/lessons/{lesson_id}/approval")
def set_approval(lesson_id: str, body: ApprovalUpdate, user: dict = Depends(require_role("teacher"))):
    try:
        lesson = store.set_approved(lesson_id, user["id"], body.approved)
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    return lesson


@teacher.post("/lessons/{lesson_id}/publish")
def publish(lesson_id: str, user: dict = Depends(require_role("teacher"))):
    try:
        lesson = store.publish_lesson(lesson_id, user["id"])
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    if not lesson:
        raise HTTPException(400, "Lesson must be approved and have generated content before publishing")
    return lesson


@teacher.post("/reset")
def reset(user: dict = Depends(require_role("teacher"))):
    # Scoped to the calling teacher's own courses -- a global wipe isn't
    # safe once the database holds more than one person's real data.
    store.reset_teacher_courses(user["id"])
    return {"ok": True}


@teacher.post("/materials")
async def upload_material(file: UploadFile = File(...), _: dict = Depends(require_role("teacher"))):
    # Indexes immediately -- a reference document isn't a creative AI
    # action that needs a teacher's sign-off, unlike the four course-
    # mutating agent tools. Shared across all teachers, like the rest of
    # this prototype's single knowledge base (knowledge.py) -- not yet
    # scoped per-teacher/course.
    try:
        return knowledge.add_material(file.filename, await file.read())
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@teacher.get("/materials")
def list_materials(_: dict = Depends(require_role("teacher"))):
    return knowledge.list_materials()


@teacher.delete("/materials/{material_id}")
def delete_material(material_id: str, _: dict = Depends(require_role("teacher"))):
    if not knowledge.delete_material(material_id):
        raise HTTPException(404, "Material not found")
    return {"ok": True}


# ---- AI Creative -----------------------------------------------------
# A personal, cross-course media library -- not tied to any course/lesson.
# Upload is real (see creative.py); "Generate" in the frontend is a
# client-only mockup that never calls this backend, since no AI generation
# provider's API key is configured in this project (see creative.py's
# module docstring).


@teacher.post("/creative/assets")
async def upload_creative_asset(file: UploadFile = File(...), user: dict = Depends(require_role("teacher"))):
    try:
        return creative.add_asset(user["id"], file.filename, file.content_type or "", await file.read())
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@teacher.get("/creative/assets")
def list_creative_assets(user: dict = Depends(require_role("teacher"))):
    return creative.list_assets(user["id"])


@teacher.get("/creative/assets/{asset_id}/file")
def get_creative_asset_file(asset_id: str, user: dict = Depends(require_role("teacher"))):
    asset = creative.get_asset(asset_id, user["id"])
    if not asset:
        raise HTTPException(404, "Asset not found")
    return FileResponse(asset.storage_path, media_type=asset.content_type, filename=asset.filename)


@teacher.delete("/creative/assets/{asset_id}")
def delete_creative_asset(asset_id: str, user: dict = Depends(require_role("teacher"))):
    if not creative.delete_asset(asset_id, user["id"]):
        raise HTTPException(404, "Asset not found")
    return {"ok": True}


# ---- Teacher Persona --------------------------------------------------
# A teacher's own enrolled video/voice likeness -- real enrollment data,
# but no avatar-rendering provider is wired up (see persona.py). The
# frontend shows a clearly-labeled mock playback.


class PersonaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    trainingAssetId: str
    consented: bool


@teacher.post("/persona")
def upsert_persona(body: PersonaCreate, user: dict = Depends(require_role("teacher"))):
    try:
        return persona.create_or_update_persona(user["id"], body.name, body.trainingAssetId, body.consented)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@teacher.get("/persona")
def my_persona(user: dict = Depends(require_role("teacher"))):
    return persona.get_persona(user["id"])


@teacher.delete("/persona")
def remove_persona(user: dict = Depends(require_role("teacher"))):
    if not persona.delete_persona(user["id"]):
        raise HTTPException(404, "No persona to delete")
    return {"ok": True}


# ---- AI Teaching Assistant ---------------------------------------------
# A per-course, teacher-authored AI persona students chat with. Real and
# working end-to-end -- see teaching_assistant.py for why it's a plain
# per-request Agent rather than routed through /agui's static team.


class TeachingAssistantUpsert(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    instructions: str = Field(min_length=1, max_length=4000)


@teacher.post("/courses/{course_id}/ta")
def upsert_ta(course_id: str, body: TeachingAssistantUpsert, user: dict = Depends(require_role("teacher"))):
    try:
        return teaching_assistant.create_or_update_ta(course_id, user["id"], body.name, body.instructions)
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@teacher.delete("/courses/{course_id}/ta")
def remove_ta(course_id: str, user: dict = Depends(require_role("teacher"))):
    if not teaching_assistant.delete_ta(course_id, user["id"]):
        raise HTTPException(404, "No Teaching Assistant to delete")
    return {"ok": True}


# ---- Marketplace ---------------------------------------------------------
# Teacher-to-teacher only (not the student catalog above): a teacher lists
# one of their own courses for sale, another teacher browses/searches and
# buys it, and buying hands the buyer an independent copy -- see
# marketplace.py's module docstring. Payment is mocked: `purchase` grants
# the copy immediately, no processor involved yet.


class ListingCreate(BaseModel):
    courseId: str
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    # Bounded above as a sanity ceiling against a fat-fingered or abusive
    # price, not a real business limit -- $50,000 (mocked payment, no
    # processor to enforce anything tighter yet).
    priceCents: int = Field(gt=0, le=50_000_00)


@teacher.get("/marketplace/listings")
def browse_listings(q: str | None = Query(default=None, max_length=200), user: dict = Depends(require_role("teacher"))):
    # Excludes the caller's own listings -- browsing to buy from yourself
    # isn't a real scenario, and it keeps a seller's feed from cluttering
    # their own search results.
    return marketplace.list_active_listings(q, exclude_seller_id=user["id"])


@teacher.get("/marketplace/listings/{listing_id}")
def listing_detail(listing_id: str, _: dict = Depends(require_role("teacher"))):
    listing = marketplace.get_listing(listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    return listing


@teacher.post("/marketplace/listings", status_code=201)
def create_listing(body: ListingCreate, user: dict = Depends(require_role("teacher"))):
    try:
        return marketplace.create_listing(user["id"], body.courseId, body.title, body.description, body.priceCents)
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@teacher.post("/marketplace/listings/{listing_id}/deactivate")
def deactivate_listing(listing_id: str, user: dict = Depends(require_role("teacher"))):
    try:
        listing = marketplace.deactivate_listing(listing_id, user["id"])
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e
    if not listing:
        raise HTTPException(404, "Listing not found")
    return listing


@teacher.post("/marketplace/listings/{listing_id}/purchase", status_code=201)
def purchase_listing(listing_id: str, user: dict = Depends(require_role("teacher"))):
    try:
        return marketplace.purchase_listing(listing_id, user["id"])
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@teacher.get("/marketplace/mine/listings")
def my_listings(user: dict = Depends(require_role("teacher"))):
    return marketplace.list_my_listings(user["id"])


@teacher.get("/marketplace/mine/purchases")
def my_purchases(user: dict = Depends(require_role("teacher"))):
    return marketplace.list_my_purchases(user["id"])


# ---- Liveblocks-backed features --------------------------------------------
# The lecturers' chat and the collaborative knowledge-graph boards both live
# in Liveblocks (Feeds / Storage respectively) -- this backend only mints the
# shared auth token; see liveblocks_auth.py's module docstring.


@teacher.post("/liveblocks-auth")
def liveblocks_auth_route(user: dict = Depends(require_role("teacher"))):
    return liveblocks_auth.authorize(user)


# ---- Collaborative knowledge-graph boards ----------------------------------
# Board metadata only (title/creator/timestamp) -- the graph content lives
# entirely in Liveblocks Storage; see kg_boards.py's module docstring.


class KgBoardCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class KgBoardRename(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@teacher.get("/kg-boards")
def list_kg_boards(_: dict = Depends(require_role("teacher"))):
    return kg_boards.list_boards()


@teacher.post("/kg-boards", status_code=201)
def create_kg_board(body: KgBoardCreate, user: dict = Depends(require_role("teacher"))):
    return kg_boards.create_board(user["id"], body.title)


@teacher.patch("/kg-boards/{board_id}")
def rename_kg_board(board_id: str, body: KgBoardRename, _: dict = Depends(require_role("teacher"))):
    try:
        board = kg_boards.rename_board(board_id, body.title)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not board:
        raise HTTPException(404, "Board not found")
    return board


@teacher.delete("/kg-boards/{board_id}", status_code=204)
def delete_kg_board(board_id: str, _: dict = Depends(require_role("teacher"))):
    if not kg_boards.delete_board(board_id):
        raise HTTPException(404, "Board not found")


# ---- Agent audit trail ----------------------------------------------------
# What the AI changed on this teacher's behalf -- see audit.py.


@teacher.get("/audit")
def list_audit(user: dict = Depends(require_role("teacher"))):
    return audit.list_for_user(user["id"])


# ---- Ask AI chat history --------------------------------------------------
# Read-only: the AGUI /agui route above is still the only way to actually
# talk to the agent. These just let a teacher browse and re-open a past
# session -- see chat_history.py for why a session only appears here once
# it's been attributed to a real user_id.


@teacher.get("/chat/sessions")
def list_chat_sessions(user: dict = Depends(require_role("teacher"))):
    return chat_history.list_my_sessions(user["id"])


@teacher.get("/chat/sessions/{session_id}")
def chat_session_transcript(session_id: str, user: dict = Depends(require_role("teacher"))):
    transcript = chat_history.get_session_transcript(user["id"], session_id)
    if transcript is None:
        raise HTTPException(404, "Session not found")
    return transcript


app.include_router(teacher)


# ---- Student routes -----------------------------------------------------

student = APIRouter(prefix="/api")


@student.get("/students/me/courses")
def my_enrolled_courses(user: dict = Depends(require_role("student"))):
    return store.list_enrolled_courses(user["id"])


@student.post("/courses/{course_id}/enroll")
def enroll(course_id: str, user: dict = Depends(require_role("student"))):
    _course_or_404(course_id)
    return store.enroll_student(course_id, user["id"])


@student.get("/courses/{course_id}/lessons/{lesson_id}")
def student_lesson(course_id: str, lesson_id: str, user: dict = Depends(require_role("student"))):
    lesson = store.get_published_lesson_for_student(course_id, lesson_id, user["id"])
    if not lesson:
        raise HTTPException(404, "Lesson not found, not published yet, or you're not enrolled in this course")
    return lesson


class TaTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class TaChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[TaTurn] = Field(default_factory=list, max_length=40)


@student.post("/courses/{course_id}/ta/chat")
def ta_chat(course_id: str, body: TaChatRequest, user: dict = Depends(require_role("student"))):
    if not store.is_enrolled(course_id, user["id"]):
        raise HTTPException(403, "You're not enrolled in this course")
    try:
        reply = teaching_assistant.ask(course_id, body.message, [t.model_dump() for t in body.history], user["id"])
    except usage.UsageLimitExceeded as e:
        raise HTTPException(429, "You've reached today's Teaching Assistant limit. Try again tomorrow.") from e
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(503, "The Teaching Assistant is temporarily unavailable") from e
    return {"reply": reply}


class QuizAttemptSubmit(BaseModel):
    quizItemId: str
    selectedIndex: int


@student.post("/lessons/{lesson_id}/quiz/attempts")
def submit_quiz_attempt(lesson_id: str, body: QuizAttemptSubmit, user: dict = Depends(require_role("student"))):
    try:
        return store.record_quiz_attempt(lesson_id, user["id"], body.quizItemId, body.selectedIndex)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@student.get("/lessons/{lesson_id}/quiz/attempts/me")
def my_quiz_attempts(lesson_id: str, user: dict = Depends(require_role("student"))):
    return store.list_attempts_for_student(lesson_id, user["id"])


app.include_router(student)


# ---- Shared (either role) ------------------------------------------------


@app.get("/api/courses")
def catalog(user: dict = Depends(set_current_user)):
    # Published courses only -- Moodle's self-enrol method, the simplest of
    # its four enrollment methods, matching this app's no-admin-console scope.
    return store.list_published_courses()


@app.get("/api/courses/{course_id}/persona")
def course_persona(course_id: str, user: dict = Depends(set_current_user)):
    # Either role: a student needs this to know whether to show "Watch
    # ... explain this"; the teacher previewing their own course does too.
    found = persona.get_persona_for_course(course_id)
    if not found:
        raise HTTPException(404, "No persona set up for this course's teacher")
    return found


@app.get("/api/courses/{course_id}/ta")
def course_ta(course_id: str, user: dict = Depends(set_current_user)):
    found = teaching_assistant.get_ta(course_id)
    if not found:
        raise HTTPException(404, "No Teaching Assistant set up for this course")
    return found


@app.get("/api/health")
def health():
    return {"status": "ok"}
