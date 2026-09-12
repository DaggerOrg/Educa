import { useEffect, useState } from "react";
import { patchLesson } from "../api.ts";
import type { Lesson, Week } from "../types.ts";
import { IconDocument } from "./icons.tsx";

interface LessonPanelProps {
  lesson: Lesson | null;
  week: Week | null;
  onBack: () => void;
  onEdited: (id: string) => void;
  onApprove: (lessonId: string, approved: boolean) => void;
  onPublish: (lessonId: string) => void;
  onAddMaterial: () => void;
}

export default function LessonPanel({ lesson, week, onBack, onEdited, onApprove, onPublish, onAddMaterial }: LessonPanelProps) {
  const [title, setTitle] = useState(lesson?.title ?? "");
  const [objective, setObjective] = useState(lesson?.objective ?? "");

  // Keep local inputs in sync when the agent (not this page) changes the
  // lesson, or when a different lesson is opened.
  useEffect(() => setTitle(lesson?.title ?? ""), [lesson?.id, lesson?.title]);
  useEffect(() => setObjective(lesson?.objective ?? ""), [lesson?.id, lesson?.objective]);

  if (!lesson) {
    return (
      <section className="educa-page">
        <button type="button" className="hint-inline educa-back" onClick={onBack}>← Back to course</button>
        <div className="empty-panel">Select a lesson to open it.</div>
      </section>
    );
  }

  async function saveTitle() {
    if (!lesson || title === lesson.title) return;
    await patchLesson(lesson.id, { title });
    onEdited(lesson.id);
  }

  async function saveObjective() {
    if (!lesson || objective === lesson.objective) return;
    await patchLesson(lesson.id, { objective });
    onEdited(lesson.id);
  }

  return (
    <section className="educa-page">
      <button type="button" className="hint-inline educa-back" onClick={onBack}>← Back to course</button>

      <div className="panel-head">
        {week && <div className="lesson-breadcrumb">Week {week.week} — {week.title}</div>}
        <div className="panel-head-row">
          <input
            className="lesson-page-title-input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={saveTitle}
          />
          <button type="button" className="btn" onClick={onAddMaterial}>
            <IconDocument /> Add material
          </button>
        </div>
        <input
          className="lesson-page-objective-input"
          value={objective}
          onChange={(e) => setObjective(e.target.value)}
          onBlur={saveObjective}
        />
      </div>

      {!lesson.content ? (
        <p className="hint">
          Ask the chat to draft this lesson — e.g. “draft the lesson on {lesson.title}”.
        </p>
      ) : (
        <>
          <div className="slides-list">
            {lesson.content.slides.map((s, i) => (
              <div className="slide-card" key={i}>
                <h4>{s.heading}</h4>
                <ul>{s.bullets.map((b, bi) => <li key={bi}>{b}</li>)}</ul>
              </div>
            ))}
          </div>
          <div className="notes-block">
            <label className="field-label">Speaker notes</label>
            <p>{lesson.content.speakerNotes}</p>
          </div>
          {lesson.content.quiz ? (
            <div className="quiz-block">
              <label className="field-label">Quiz</label>
              <p className="quiz-question">{lesson.content.quiz.question}</p>
              <ul className="quiz-options">
                {lesson.content.quiz.options.map((opt, i) => (
                  <li key={i} className={i === lesson.content!.quiz!.correctIndex ? "is-correct" : ""}>{opt}</li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="hint">Ask the chat to draft a quiz for this lesson.</p>
          )}
        </>
      )}

      <div className="publish-block">
        <label className="check-row">
          <input
            type="checkbox"
            checked={lesson.approved}
            disabled={lesson.published}
            onChange={(e) => onApprove(lesson.id, e.target.checked)}
          />
          Reviewed — ready to publish
        </label>
        <button
          className="btn btn-primary"
          disabled={!lesson.approved || lesson.published || !lesson.content || !lesson.content.quiz}
          onClick={() => onPublish(lesson.id)}
        >
          {lesson.published ? "Published" : "Publish to students"}
        </button>
        {!lesson.approved && <span className="hint-inline">Requires review — nothing reaches students unpublished.</span>}
        {lesson.approved && lesson.content && !lesson.content.quiz && (
          <span className="hint-inline">Needs a quiz before it can be published.</span>
        )}
      </div>
    </section>
  );
}
