import { CopilotChat } from "@copilotkit/react-core/v2";
import { useState } from "react";
import { findLesson } from "../App.tsx";
import type { Course, Exercise } from "../types.ts";
import ExerciseMindMap from "./ExerciseMindMap.tsx";
import { IconChat, IconClose } from "./icons.tsx";

const KIND_LABEL: Record<Exercise["kind"], string> = {
  multiple_choice: "Multiple choice",
  true_false: "True / False",
  flashcard: "Flashcard",
};

interface ExercisesBuilderProps {
  course: Course;
  selectedLessonId: string | null;
  onSelectLesson: (id: string) => void;
}

export default function ExercisesBuilder({ course, selectedLessonId, onSelectLesson }: ExercisesBuilderProps) {
  const [chatOpen, setChatOpen] = useState(false);

  const firstLessonId = course.weeks.flatMap((w) => w.lessons)[0]?.id ?? null;
  const lessonId = (selectedLessonId && findLesson(course, selectedLessonId)) ? selectedLessonId : firstLessonId;
  const lesson = findLesson(course, lessonId);
  const exercises = lesson?.content?.exercises ?? [];

  return (
    <div className="exercises-builder">
      <div className="exercises-builder-main">
        <div className="exercises-builder-head">
          <div>
            <h2>Exercises Builder</h2>
            <p className="hint">
              Ask the chat to draft practice exercises — multiple choice, true/false, or
              flashcards — for the lesson below.
            </p>
          </div>
          <button type="button" className={`btn exercises-chat-btn${chatOpen ? " is-active" : ""}`} onClick={() => setChatOpen((v) => !v)}>
            <IconChat /> Exercises chat
          </button>
        </div>

        <select
          className="course-switcher exercises-lesson-picker"
          value={lessonId ?? ""}
          onChange={(e) => onSelectLesson(e.target.value)}
        >
          {course.weeks.map((w) => (
            <optgroup key={w.week} label={`Week ${w.week} — ${w.title}`}>
              {w.lessons.map((l) => (
                <option key={l.id} value={l.id}>{l.title}</option>
              ))}
            </optgroup>
          ))}
        </select>

        {exercises.length === 0 ? (
          <p className="hint">
            No exercises yet for this lesson — open the chat and ask, e.g. “make 3 flashcards and
            a true/false question for {lesson?.title ?? "this lesson"}”.
          </p>
        ) : (
          <div className="exercises-list">
            {exercises.map((ex) => (
              <div className="exercise-card" key={ex.id}>
                <span className={`status-pill exercise-kind exercise-kind-${ex.kind}`}>{KIND_LABEL[ex.kind]}</span>
                <p className="quiz-question">{ex.prompt}</p>
                {ex.kind === "flashcard" ? (
                  <p className="hint-inline">{ex.back}</p>
                ) : (
                  <ul className="quiz-options">
                    {(ex.options ?? []).map((opt, i) => (
                      <li key={i} className={i === ex.correctAnswer ? "is-correct" : ""}>{opt}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <ExerciseMindMap lessonTitle={lesson?.title ?? null} exercises={exercises} />

      {chatOpen && (
        <>
          <div className="chat-backdrop" onClick={() => setChatOpen(false)} />
          <aside className="chat-drawer dark">
            <div className="chat-drawer-head">
              <span>Exercises chat</span>
              <button
                type="button"
                className="chat-drawer-close"
                onClick={() => setChatOpen(false)}
                aria-label="Close exercises chat"
              >
                <IconClose />
              </button>
            </div>
            {/* A distinct threadId from the main "Ask AI" drawer -- CopilotKit
                v2 caches per-thread clones, so this gets its own message/
                tool-call history and its own HITL approval cards instead of
                sharing the main chat's thread. */}
            <CopilotChat agentId="curriculum_team" threadId="exercises-builder" />
          </aside>
        </>
      )}
    </div>
  );
}
