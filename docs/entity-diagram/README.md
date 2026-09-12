# Educa — entity diagram

Every entity across the product so far, including the assessment entities
proposed for the quiz-consistency problem (`Quiz` / `QuizItem` /
`QuizAttempt` / `Response`) — not yet in `backend/app/store.py`. Rendered
version (same content, styled): [Educa Entity
Diagram](https://claude.ai/code/artifact/25c672f6-42ae-473b-918a-959be1128d8c)
artifact.

- **12** entities total
- **8** already speced or built
- **4** proposed for assessments
- **15** relationships

```mermaid
erDiagram
    USER ||--o{ COURSE : "owns (teacher)"
    USER ||--o{ ENROLLMENT : "enrolls as (student)"
    COURSE ||--o{ ENROLLMENT : "has"
    COURSE ||--o{ MODULE : "contains"
    COURSE ||--o{ SOURCEDOCUMENT : "source library"
    MODULE ||--o{ LESSON : "contains"
    LESSON ||--o{ SLIDE : "contains"
    LESSON ||--o{ ASSET : "embeds"
    LESSON ||--o| QUIZ : "has"
    LESSON }o--o{ SOURCEDOCUMENT : "grounded in"
    QUIZ ||--o{ QUIZITEM : "contains"
    QUIZ ||--o{ QUIZATTEMPT : "attempted via"
    USER ||--o{ QUIZATTEMPT : "submits (student)"
    QUIZATTEMPT ||--o{ RESPONSE : "contains"
    QUIZITEM ||--o{ RESPONSE : "answered by"

    USER {
        string id PK
        string email
        string role "teacher | student"
    }
    COURSE {
        string id PK
        string teacher_id FK
        string title
        string audience
    }
    MODULE {
        string id PK
        string course_id FK
        int week_number
        string title
    }
    LESSON {
        string id PK
        string module_id FK
        string title
        string objective
        bool approved
        bool published
    }
    SLIDE {
        string id PK
        string lesson_id FK
        string heading
        string_array bullets
    }
    SOURCEDOCUMENT {
        string id PK
        string course_id FK
        string filename
        string_array embedding_ids
    }
    ASSET {
        string id PK
        string lesson_id FK
        string desc
        string_array palette
        string motif
    }
    ENROLLMENT {
        string id PK
        string course_id FK
        string student_id FK
        string status
    }
    QUIZ {
        string id PK
        string lesson_id FK
        int version
        datetime created_at
    }
    QUIZITEM {
        string id PK
        string quiz_id FK
        string kind "multiple_choice | fill_in_blank"
        string prompt
        json correct_answer
    }
    QUIZATTEMPT {
        string id PK
        string quiz_id FK
        string student_id FK
        int score
        datetime submitted_at
    }
    RESPONSE {
        string id PK
        string attempt_id FK
        string item_id FK
        json value
        bool is_correct
    }
```

## Already speced or built

| Entity | Status |
| --- | --- |
| `User` | auth exists on frontend; role concept assumed |
| `Course` | built — single global course in the mini prototype |
| `Module` | speced (ARCH-01) — currently embedded as `Course.weeks[]` |
| `Lesson` | built |
| `Slide` | speced — currently embedded as `Lesson.content.slides[]` |
| `SourceDocument` | speced (SRS module B) — not in the mini prototype backend |
| `Asset` | speced (ARCH-01 §05 / SRS module I) — not built |
| `Enrollment` | speced — not built (no multi-student model yet) |

## Proposed — the assessment fix

| Entity | Note |
| --- | --- |
| `Quiz` | immutable once created; a regenerate makes a new version, not an edit |
| `QuizItem` | discriminated by `kind` — the fixed shape the AI must emit |
| `QuizAttempt` | written once at submission; score is a stored fact, never recomputed |
| `Response` | one row per item per attempt — what makes per-question analytics possible later |

See also: [exam-marking/](../exam-marking/README.md) sketches a further
extension on top of `Quiz`/`QuizItem`/`QuizAttempt`/`Response` — exam
scheduling/timers, paper-scan ingestion, AI marking, and a
submit-to-faculty workflow. Still ideation, not yet reflected in the
diagram above.

## Reading the diagram

`LESSON ||--o| QUIZ` means a lesson has at most one quiz (0 or 1); `QUIZ
||--o{ QUIZATTEMPT` means one quiz has many attempts (one per student,
potentially more if retakes are ever allowed). The `}o--o{` between LESSON
and SOURCEDOCUMENT is the only many-to-many: a lesson can cite several
source documents, and one document can ground several lessons.
