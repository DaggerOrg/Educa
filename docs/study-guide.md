# Study guide: the faculty panel

After a PDF is uploaded and processed, a panel of specialist agents reads it
chapter by chapter, the way lecturers preparing a course from a textbook
would, and saves a page-cited **study guide** for the teacher to review.

## Flow

```
upload PDF ─▶ curriculum_ai processing ─▶ READY ─▶ analysis job (RQ) ─▶ study guide
                                                      │
                          units.py: split into chapters (bookmarks ▸ "Chapter N" headings ▸ 10-page windows)
                                                      │  per chapter
                     ┌──────────────┬─────────────────┼─────────────────┐
              concept_analyst  theory_professor  exercise_lecturer   (parallel)
                     └──────────────┴────────┬────────┴─────────────────┘
                                        faculty_chair  (summary + learning objectives, from the findings only)
```

- Agents: `backend/app/agents/faculty/` (`agents.py` prompts, `schemas.py`
  structured outputs, `panel.py` orchestration). They are **not** members of
  `curriculum_team`: they run as a fixed pipeline in a background job, have
  no tools, and nothing pauses for confirmation mid-run.
- Job + persistence: `backend/curriculum_ai/analysis/` (`units.py`,
  `tasks.py`, `service.py`, `grounding.py`); tables `StudyGuideRun`,
  `StudyGuideUnit`, `StudyGuideEntry` in `curriculum_ai/models.py`.
- Triggered automatically when a document reaches `READY`
  (`STUDY_GUIDE_AUTO_ANALYZE=false` turns that off) or manually via the API.
  Needs the RQ worker running: `python -m curriculum_ai.jobs.worker`.

## Trust model

- **Citations are checked.** Every entry carries a verbatim `evidence_quote`
  and page. If the quote isn't found in the chapter text, the entry is saved
  with `grounded: false` so the review UI can flag it -- it is not silently
  dropped.
- **Nothing is authoritative until reviewed.** Entries start `proposed`; a
  teacher sets `approved` / `rejected` or edits them.
- **Re-running never destroys teacher work.** A re-run replaces only
  unreviewed entries (`proposed` and never edited) and does not re-propose a
  concept/theory/exercise whose title the teacher already approved, edited,
  or rejected.
- Chapter text is wrapped in `<source_text>` and the agents are told it is
  data, never instructions (uploaded PDFs are untrusted).
- A chapter where one specialist fails still keeps the other two's results;
  a chapter where all fail is marked `failed` and the rest of the book
  continues.

## API (all under `/api/curriculum/projects/{project_id}/documents/{document_id}`, teacher-only, owner-checked)

| Method | Path | |
|---|---|---|
| `POST` | `/analysis` | Start (or restart) analysis; 202. 400 if the document isn't `ready` or a run is already active. |
| `GET` | `/analysis` | `{run, units, entries}` -- progress, chapter summaries, entries. |
| `PATCH` | `/analysis/entries/{entry_id}` | `{review_status?, title?, data?}`. `data` may only change fields the entry already has, with the same type. |

## Known limits

- **Scanned PDFs** have no text layer and fail with a clear error (OCR isn't built).
- **Chapter detection is heuristic.** Real bookmarks are best; otherwise
  "Chapter N"-style headings; otherwise 10-page windows. Phase 2/3 of
  `docs/architecture/phase-specs.md` (true heading/table/formula parsing)
  would improve it.
- The chat `materials_agent` still searches the older flat `/materials` index
  (`app/knowledge.py`); it does not read the study guide yet.
- Tested with stub agents. Structured-output schemas are verified to convert
  through the google-genai SDK, but quality against the live model hasn't
  been evaluated.
