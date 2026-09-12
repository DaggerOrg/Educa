import { ToolCallStatus, useHumanInTheLoop } from "@copilotkit/react-core/v2";
import type { ReactNode } from "react";
import { findLesson } from "../App.tsx";
import type { Course } from "../types.ts";
import { IconCheck, IconClose } from "./icons.tsx";

// The four agent tools -- create_syllabus/update_syllabus (curriculum_agent,
// backend/app/agent/tools.py), generate_lesson_slides (lesson_content_agent,
// lesson_content_tools.py), and generate_lesson_quiz (quiz_agent,
// quiz_tools.py) -- all require confirmation: Agno pauses the run and
// re-emits the call as a normal AG-UI tool call, which these render as an
// approve/reject card. Calling `respond({ accepted })` resends the run with
// that as the tool result, which backend/app/os/interfaces/agui's resume
// path reads to confirm or reject the paused tool.

interface WeekDraft {
  week?: number;
  title?: string;
  lessons?: { title?: string; objective?: string }[];
}

interface SyllabusArgs extends Record<string, unknown> {
  title?: string;
  audience?: string;
  weeks?: WeekDraft[];
}

interface SlideDraft {
  heading?: string;
  bullets?: string[];
}

interface QuizDraft {
  question?: string;
  options?: string[];
  correctIndex?: number;
}

interface LessonSlidesArgs extends Record<string, unknown> {
  lesson_id?: string;
  slides?: SlideDraft[];
  speaker_notes?: string;
}

interface LessonQuizArgs extends Record<string, unknown> {
  lesson_id?: string;
  quiz?: QuizDraft;
}

interface ExerciseDraft {
  kind?: "multiple_choice" | "true_false" | "flashcard";
  prompt?: string;
  options?: string[];
  correct_answer?: number;
  back?: string;
}

interface LessonExercisesArgs extends Record<string, unknown> {
  lesson_id?: string;
  exercises?: ExerciseDraft[];
}

function parseResult(result: string): { accepted?: boolean } | null {
  try {
    const parsed = JSON.parse(result);
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

interface ApprovalCardProps {
  label: string;
  status: ToolCallStatus;
  result: string | undefined;
  respond: ((result: unknown) => Promise<void>) | undefined;
  children: ReactNode;
}

function ApprovalCard({ label, status, result, respond, children }: ApprovalCardProps) {
  const resolved = status === ToolCallStatus.Complete && result ? parseResult(result) : null;

  return (
    <div className="hitl-card">
      <div className="hitl-card-label">{label}</div>
      <div className="hitl-card-body">{children}</div>
      {status === ToolCallStatus.InProgress && <p className="hint">Drafting…</p>}
      {status === ToolCallStatus.Executing && respond && (
        <div className="hitl-card-actions">
          <button type="button" className="btn" onClick={() => respond({ accepted: false })}>
            <IconClose /> Reject
          </button>
          <button type="button" className="btn btn-primary" onClick={() => respond({ accepted: true })}>
            <IconCheck /> Approve
          </button>
        </div>
      )}
      {status === ToolCallStatus.Complete && (
        <span className={`status-pill ${resolved?.accepted ? "status-approved" : "status-draft"}`}>
          {resolved?.accepted ? "Approved" : "Rejected"}
        </span>
      )}
    </div>
  );
}

function SyllabusPreview({ args }: { args: SyllabusArgs }) {
  return (
    <>
      {args.title && <p className="hitl-field"><strong>{args.title}</strong></p>}
      {args.audience && <p className="hitl-field-sub">{args.audience}</p>}
      {(args.weeks ?? []).map((w, i) => (
        <div className="hitl-week" key={w.week ?? i}>
          <div className="week-head">Week {w.week} — {w.title}</div>
          <ul className="hitl-lesson-list">
            {(w.lessons ?? []).map((l, li) => <li key={li}>{l.title}</li>)}
          </ul>
        </div>
      ))}
    </>
  );
}

function LessonSlidesPreview({ args, lessonTitle }: { args: LessonSlidesArgs; lessonTitle: string | null }) {
  return (
    <>
      {lessonTitle && <p className="hitl-field"><strong>{lessonTitle}</strong></p>}
      <div className="slides-list">
        {(args.slides ?? []).map((s: SlideDraft, i: number) => (
          <div className="slide-card" key={i}>
            <h4>{s.heading}</h4>
            <ul>{(s.bullets ?? []).map((b: string, bi: number) => <li key={bi}>{b}</li>)}</ul>
          </div>
        ))}
      </div>
      {args.speaker_notes && (
        <div className="notes-block">
          <label className="field-label">Speaker notes</label>
          <p>{args.speaker_notes}</p>
        </div>
      )}
    </>
  );
}

function LessonQuizPreview({ args, lessonTitle }: { args: LessonQuizArgs; lessonTitle: string | null }) {
  const quiz = args.quiz;
  return (
    <>
      {lessonTitle && <p className="hitl-field"><strong>{lessonTitle}</strong></p>}
      {quiz && (
        <div className="quiz-block">
          <label className="field-label">Quiz</label>
          <p className="quiz-question">{quiz.question}</p>
          <ul className="quiz-options">
            {(quiz.options ?? []).map((opt: string, i: number) => (
              <li key={i} className={i === quiz.correctIndex ? "is-correct" : ""}>{opt}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

const EXERCISE_KIND_LABEL: Record<string, string> = {
  multiple_choice: "Multiple choice",
  true_false: "True / False",
  flashcard: "Flashcard",
};

function LessonExercisesPreview({ args, lessonTitle }: { args: LessonExercisesArgs; lessonTitle: string | null }) {
  return (
    <>
      {lessonTitle && <p className="hitl-field"><strong>{lessonTitle}</strong></p>}
      <div className="hitl-exercise-list">
        {(args.exercises ?? []).map((ex, i) => (
          <div className="hitl-exercise" key={i}>
            <span className={`status-pill hitl-exercise-kind exercise-kind-${ex.kind ?? "multiple_choice"}`}>
              {EXERCISE_KIND_LABEL[ex.kind ?? "multiple_choice"]}
            </span>
            <p className="quiz-question">{ex.prompt}</p>
            {ex.kind === "flashcard" ? (
              <p className="hitl-field-sub">{ex.back}</p>
            ) : (
              <ul className="quiz-options">
                {(ex.options ?? []).map((opt, oi) => (
                  <li key={oi} className={oi === ex.correct_answer ? "is-correct" : ""}>{opt}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </>
  );
}

export function useCurriculumApprovals(course: Course | null) {
  useHumanInTheLoop<SyllabusArgs>(
    {
      name: "create_syllabus",
      render: (props) => (
        <ApprovalCard label="New syllabus" status={props.status} result={props.result} respond={props.respond}>
          <SyllabusPreview args={props.args} />
        </ApprovalCard>
      ),
    },
    [],
  );

  useHumanInTheLoop<SyllabusArgs>(
    {
      name: "update_syllabus",
      render: (props) => (
        <ApprovalCard label="Syllabus update" status={props.status} result={props.result} respond={props.respond}>
          <SyllabusPreview args={props.args} />
        </ApprovalCard>
      ),
    },
    [],
  );

  useHumanInTheLoop<LessonSlidesArgs>(
    {
      name: "generate_lesson_slides",
      render: (props) => (
        <ApprovalCard label="Lesson slides" status={props.status} result={props.result} respond={props.respond}>
          <LessonSlidesPreview args={props.args} lessonTitle={course ? findLesson(course, props.args.lesson_id)?.title ?? null : null} />
        </ApprovalCard>
      ),
    },
    [course],
  );

  useHumanInTheLoop<LessonQuizArgs>(
    {
      name: "generate_lesson_quiz",
      render: (props) => (
        <ApprovalCard label="Lesson quiz" status={props.status} result={props.result} respond={props.respond}>
          <LessonQuizPreview args={props.args} lessonTitle={course ? findLesson(course, props.args.lesson_id)?.title ?? null : null} />
        </ApprovalCard>
      ),
    },
    [course],
  );

  useHumanInTheLoop<LessonExercisesArgs>(
    {
      name: "generate_lesson_exercises",
      render: (props) => (
        <ApprovalCard label="Lesson exercises" status={props.status} result={props.result} respond={props.respond}>
          <LessonExercisesPreview args={props.args} lessonTitle={course ? findLesson(course, props.args.lesson_id)?.title ?? null : null} />
        </ApprovalCard>
      ),
    },
    [course],
  );
}
