# Educa — API contracts (Moodle-referenced)

A snapshot of the REST API actually implemented in `backend/app/main.py`,
`backend/app/auth/routes.py`, and the AG-UI agent surface, as consumed by
`frontend/src/api.ts`. This documents **what's built**, not a proposal —
Educa's backend was migrated in parallel with this doc from a single
in-memory demo course to a real multi-course, multi-role platform
(`backend/app/models_db.py`: `User`, `Course`, `Module`, `Lesson`,
`Enrollment`, `Quiz`/`QuizItem`/`QuizAttempt`/`Response`, `Listing`/`Purchase`).
Rendered version (same content, styled): [Educa API
Contracts](https://claude.ai/code/artifact/58a2242f-2f49-43b8-a482-c3c9923dfcd6) artifact.

Each section names the closest real Moodle Web Service function(s) —
Educa doesn't mimic Moodle's RPC wire format (`wsfunction=...` on one
endpoint), it borrows Moodle's *domain model* and exposes it as idiomatic
REST, which is what a React/fetch frontend actually wants.

- **Snapshot date:** 2026-09-10. This backend has 14 concurrent sessions
  actively developing it — verify against `backend/app/main.py` before
  relying on an exact shape for new work.
- **Base URL:** `VITE_API_BASE`, default `http://localhost:8000/api`.
- **Auth:** every route except `/api/auth/signup` and `/api/auth/login`
  requires `Authorization: Bearer <JWT>` (see `frontend/src/auth.ts`'s
  `getToken()`). A missing/invalid token is `401`; a valid token with the
  wrong role for a route is `403`.
- **Errors:** non-2xx responses are `{"detail": string}` (FastAPI's
  default `HTTPException` shape) — `frontend/src/api.ts`'s `ApiError`
  reads `.detail` for its message.
- **Roles:** `"teacher" | "student"`, fixed at signup (`SignupRequest.role`
  in `backend/app/auth/models.py`) — there's no Moodle-style "assign role
  per course" yet, a user is one role platform-wide.

---

## 1. Auth — `/api/auth/*`

No Moodle equivalent (Moodle federates to the host site's own login) —
this is Educa's own JWT issuance, since it has no separate site to
delegate to.

| Method & path | Auth | Request | Response |
|---|---|---|---|
| `POST /api/auth/signup` | none | `SignupRequest` `{email, password (min 8), name, role}` | `201` `TokenResponse` `{access_token, token_type: "bearer", user: UserOut}` |
| `POST /api/auth/login` | none | `LoginRequest` `{email, password}` | `TokenResponse` (same shape) |
| `GET /api/auth/me` | any | — | `UserOut` `{id, email, name, role}` |

`UserOut`/`TokenResponse` are Pydantic models in `backend/app/auth/models.py`;
there's no matching frontend TS type yet (`frontend/src/auth.ts` stores the
raw JSON as `Session`) — worth adding an `AuthUser`-shaped type there for
symmetry with `UserOut` if `me`'s response ever gets consumed beyond login.

---

## 2. Teacher — course authoring — `/api/courses/*`, `/api/lessons/*`, `/api/reset`

Moodle parallel: `core_course_get_courses_by_field` (list/get your own
courses) + `core_course_get_contents` (a course's sections/activities) —
except here the *writes* mostly come from the AI agent (§5), not direct
REST edits. Role: `teacher` only (`require_role("teacher")`).

| Method & path | Request | Response | Notes |
|---|---|---|---|
| `GET /courses/mine` | — | `Course[]` | Full content — every lesson, draft or published, quiz answers included. Frontend: `listMyCourses()`. |
| `GET /courses/{course_id}` | — | `Course` | `403` if `course.teacherId !== caller`. Frontend: `fetchCourse(id)`. |
| `PATCH /lessons/{lesson_id}` | `LessonEdit` `{title?, objective?}` | `Lesson` | Direct inline edit (not agent-mediated) — see `SyllabusView.tsx`'s inline inputs. |
| `PATCH /lessons/{lesson_id}/approval` | `{approved: bool}` | `Lesson` | Can't un-approve once published (`store.set_approved`). |
| `POST /lessons/{lesson_id}/publish` | — | `Lesson` | `400` unless approved AND has slides AND has a quiz — this is Educa's publish gate, no Moodle equivalent (Moodle activities are visible/hidden, not gated on completeness). |
| `POST /reset` | — | `{ok: true}` | Deletes **all of the calling teacher's own courses** — scoped per-teacher now, not a global wipe. |

**`Course` shape** (`frontend/src/types.ts`):
```ts
interface Course { id: string; teacherId: string; title: string; audience: string; weeks: Week[] }
interface Week { week: number; title: string; lessons: Lesson[] }
interface Lesson { id: string; title: string; objective: string; content: LessonContent | null; approved: boolean; published: boolean }
interface LessonContent { slides: Slide[]; speakerNotes: string; quiz: Quiz | null }  // quiz null until quiz_agent drafts one
interface Quiz { question: string; options: string[]; correctIndex: number }          // answer key -- teacher-only, never sent to students
```
Moodle's rough equivalent nesting: `Course` → `Module` (a *week*, unrelated
to Moodle's own "activity module" term) → `Lesson` (an *activity*) →
slides/quiz (the activity's *content*). Educa is single-track (no course
sections/formats, no grouping/restrictions) — deliberately narrower than
Moodle's course-format flexibility for this prototype's scope.

---

## 3. Teacher — course materials — `/api/materials`

Moodle parallel: `core_files_upload` + a course's file-resource activities.
Role: `teacher`. Not per-course yet — one shared knowledge base across all
teachers (`backend/app/knowledge.py`), searched by `materials_agent`.

| Method & path | Request | Response |
|---|---|---|
| `POST /materials` | `multipart/form-data`, field `file` | `Material` `{id, filename, charCount, chunkCount}` |
| `GET /materials` | — | `Material[]` |
| `DELETE /materials/{material_id}` | — | `{ok: true}` |

---

## 4. Marketplace — `/api/marketplace/*`

No Moodle equivalent — Moodle has no teacher-to-teacher course resale.
Closest real-world analogue: Moodle's course *backup/restore* (`.mbz`)
between sites, except here `purchase_listing` does the "restore into a new
independent copy" step automatically, and it's gated by a mocked payment
rather than an admin import. Role: `teacher` (a teacher can be both seller
and, on someone else's listing, buyer).

| Method & path | Request | Response | Notes |
|---|---|---|---|
| `GET /marketplace/listings?q=` | query `q?` | `Listing[]` | Active listings, excludes caller's own. |
| `GET /marketplace/listings/{id}` | — | `ListingDetail` | Adds a syllabus **outline** (titles/objectives only) as a preview — never slides/speaker notes/quiz content. |
| `POST /marketplace/listings` | `ListingCreate` `{courseId, title, description?, priceCents}` | `201` `Listing` | `403` if you don't own `courseId`; `400` if it has no lessons yet or `priceCents <= 0`. |
| `POST /marketplace/listings/{id}/deactivate` | — | `Listing` | `403` if you're not the seller. |
| `POST /marketplace/listings/{id}/purchase` | — | `201` `Course` | Returns the **buyer's new, independent course copy** (fresh id, `approved`/`published` reset to false — the buyer re-reviews before publishing to their own students). `400` if inactive, self-purchase, or already owned. |
| `GET /marketplace/mine/listings` | — | `Listing[]` | |
| `GET /marketplace/mine/purchases` | — | `Purchase[]` | |

**Shapes** (`frontend/src/types.ts`):
```ts
interface Listing { id, courseId, sellerId, sellerName, title, description, priceCents, isActive, createdAt, weekCount, lessonCount, audience }
interface ListingDetail extends Listing { weeks: ListingWeekPreview[] }
interface Purchase { id, listingId, listingTitle: string | null, courseId, priceCents, purchasedAt }
```
Payment is fully mocked (`marketplace.py`'s module docstring flags this
explicitly) — `purchase_listing` grants the copy with no processor
involved. Wire a real one before this handles real money.

---

## 5. Student — catalog, enrollment, learning — `/api/courses`, `/api/students/*`, `/api/courses/{id}/enroll`, `/api/courses/{cid}/lessons/{lid}`, `/api/lessons/{id}/quiz/attempts*`

The actual Moodle-shaped student journey: browse → self-enroll → view a
lesson → take its quiz → see your score.

| Method & path | Role | Moodle parallel | Response |
|---|---|---|---|
| `GET /courses` | any authenticated | `core_course_get_courses` (catalog) | `CoursePreview[]` — published courses only |
| `GET /students/me/courses` | student | `core_enrol_get_users_courses` | `CoursePreview[]` — courses the caller is enrolled in |
| `POST /courses/{course_id}/enroll` | student | `enrol_self_enrol_user` (self-enrolment, the simplest of Moodle's four enrol methods — matches this app's no-admin-console scope) | `Enrollment` `{id, courseId, status}` — idempotent, re-enrolling returns the existing row |
| `GET /courses/{cid}/lessons/{lid}` | student | `core_course_get_contents` for one activity | `StudentLesson`, or `404` if not published or not enrolled |
| `POST /lessons/{lid}/quiz/attempts` | student | `mod_quiz_process_attempt` | `StudentQuizAttemptResult` |
| `GET /lessons/{lid}/quiz/attempts/me` | student | `mod_quiz_get_user_attempts` | `QuizAttemptSummary[]` |

**A course "counts as published"** once it has ≥1 published lesson —
Educa has no separate course-level publish action (`store.list_published_courses`'s
docstring).

**`CoursePreview`** is deliberately a *different* type from the teacher's
`Course` (`frontend/src/types.ts`'s comment is explicit about why):
```ts
interface CoursePreview { id, teacherId, title, audience, weeks: WeekPreview[] }
interface WeekPreview { week, title, lessons: LessonPreview[] }   // LessonPreview: {id, title, objective} -- published lessons only, no content
```
This is the same shape used for both the public catalog *and* a student's
own enrolled-course list — a lesson's real content is only ever served one
at a time via the `lessons/{id}` route below, which also strips the
answer key:
```ts
interface StudentQuiz { quizItemId: string; question: string; options: string[] }  // no correctIndex
interface StudentLesson { id, title, objective, slides: Slide[], speakerNotes, quiz: StudentQuiz | null }
```
`correctIndex` is withheld until `StudentQuizAttemptResult` comes back
from actually submitting an attempt:
```ts
interface StudentQuizAttemptResult { id, score, maxScore, correct: boolean, correctIndex: number, submittedAt }
interface QuizAttemptSummary { id, score, maxScore, submittedAt }  // no correctIndex -- history view, not a re-reveal
```
**Grading**: `record_quiz_attempt` (`store.py`) scores once at submission
against the lesson's *current* `Quiz` version and never recomputes —
`QuizAttempt`/`Response` rows are write-once, matching Moodle's own
"an attempt is graded against the quiz as it existed when taken" semantics
even if the teacher edits the quiz afterwards (which here means
`quiz_agent` drafting a new version — `Quiz` rows are immutable, see
`models_db.py`).

---

## 6. AI agent surface — `POST /agui`

Not a resource-oriented REST contract — a single `ag-ui-protocol` streaming
endpoint (Agno's `AGUI` router) that the frontend's `HttpAgent` +
CopilotKit talk to (`frontend/src/App.tsx`). This is how course/lesson
*content* actually gets authored; the REST routes in §2 only cover direct
teacher edits (title/objective tweaks, approve, publish) and reads.
Role: `teacher` only.

The four tools it can call, each pausing for an approve/reject card in the
chat before touching the database (`requires_confirmation=True` — see
`frontend/src/components/ApprovalCards.tsx`):

| Tool | Owning agent | Effect |
|---|---|---|
| `create_syllabus` | `curriculum_agent` | New `Course` + `Module`/`Lesson` rows |
| `update_syllabus` | `curriculum_agent` | Replace a course's modules/lessons, preserving hand-edited ones by title match |
| `generate_lesson_slides` | `lesson_content_agent` | Sets `Lesson.slides`/`speaker_notes` |
| `generate_lesson_quiz` | `quiz_agent` | Inserts a new immutable `Quiz`/`QuizItem` version |

No Moodle equivalent — Moodle has no built-in AI authoring layer.

---

## Open gaps vs. a real Moodle-equivalent platform

Worth knowing before assuming parity:

- **One role per user, platform-wide** — no per-course role assignment
  (Moodle: a user can be a teacher in one course and a student in another).
- **Self-enrolment only** — no enrolment keys, cohort sync, manual
  enrolment by a teacher, or unenrolment endpoint at all yet.
- **No gradebook aggregation** — quiz attempts are recorded per-lesson;
  nothing rolls them up into a course-level grade.
- **No course sections/formats, groups, or completion criteria** beyond
  "lesson is published" — Moodle's completion tracking is far richer.
- **Materials/knowledge base isn't per-course or per-teacher** — one shared
  index (§3).
- **Marketplace payment is mocked** (§4) — no real transaction ever occurs.
