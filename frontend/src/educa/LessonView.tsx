import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchCourse, fetchCoursePersona, fetchStudentLesson } from "../api.ts";
import type { Session } from "../auth.ts";
import { IconCheck, IconEdit, IconSparkle } from "../components/icons.tsx";
import TAChat from "../components/TAChat.tsx";
import NotesPanel from "../notes/NotesPanel.tsx";
import type { Course, Lesson, StudentLesson, TeacherPersona } from "../types.ts";
import Assignment from "./Assignment.tsx";
import Discussion from "./Discussion.tsx";
import QuizTaker from "./QuizTaker.tsx";
import { getCompletedLessonIds, setLessonComplete } from "./traditionalData.ts";

interface LessonViewProps {
  session: Session;
}

function findLesson(course: Course, lessonId: string): Lesson | null {
  for (const w of course.weeks) {
    for (const l of w.lessons) {
      if (l.id === lessonId) return l;
    }
  }
  return null;
}

export default function LessonView({ session }: LessonViewProps) {
  const { courseId = "", lessonId = "" } = useParams<{ courseId: string; lessonId: string }>();
  const isTeacher = session.user.role === "teacher";
  const [studentLesson, setStudentLesson] = useState<StudentLesson | null>(null);
  const [teacherLesson, setTeacherLesson] = useState<Lesson | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [complete, setComplete] = useState(false);
  const [persona, setPersona] = useState<TeacherPersona | null>(null);
  const [watchingPersona, setWatchingPersona] = useState(false);
  const [notesOpen, setNotesOpen] = useState(false);

  useEffect(() => {
    if (!isTeacher) fetchCoursePersona(courseId).then(setPersona).catch(() => setPersona(null));
  }, [courseId, isTeacher]);

  const load = useCallback(async () => {
    setError(null);
    try {
      if (isTeacher) {
        // No dedicated single-lesson teacher endpoint -- Studio's course
        // fetch already has full content, so this just looks the lesson
        // up locally the same way Studio does (see App.tsx's findLesson).
        const course = await fetchCourse(courseId);
        setTeacherLesson(findLesson(course, lessonId));
      } else {
        setStudentLesson(await fetchStudentLesson(courseId, lessonId));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [courseId, lessonId, isTeacher]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!isTeacher) setComplete(getCompletedLessonIds(session.user.id, courseId).has(lessonId));
  }, [isTeacher, session.user.id, courseId, lessonId]);

  function toggleComplete() {
    const next = !complete;
    setLessonComplete(session.user.id, courseId, lessonId, next);
    setComplete(next);
  }

  if (error) {
    return (
      <div className="educa-page">
        <div className="error-banner">{error}</div>
      </div>
    );
  }

  const lesson = isTeacher ? teacherLesson : studentLesson;
  if (!lesson) {
    return (
      <div className="educa-page">
        <p className="hint">Loading…</p>
      </div>
    );
  }

  const slides = isTeacher ? teacherLesson?.content?.slides ?? [] : studentLesson?.slides ?? [];
  const speakerNotes = isTeacher ? teacherLesson?.content?.speakerNotes ?? "" : studentLesson?.speakerNotes ?? "";

  return (
    <div className={`educa-page${!isTeacher && notesOpen ? " has-notes" : ""}`}>
      <Link to={`/educa/courses/${courseId}`} className="hint-inline educa-back">← Back to course</Link>
      <div className="lesson-view-head">
        <h2 className="educa-page-title">{lesson.title}</h2>
        {!isTeacher && (
          <div className="lesson-view-actions">
            <button
              type="button"
              className={`btn${notesOpen ? " is-active" : ""}`}
              aria-pressed={notesOpen}
              onClick={() => setNotesOpen(!notesOpen)}
            >
              <IconEdit /> My notes
            </button>
            <button
              type="button"
              className={`btn completion-toggle${complete ? " btn-primary" : ""}`}
              onClick={toggleComplete}
            >
              <IconCheck /> {complete ? "Completed" : "Mark as complete"}
            </button>
          </div>
        )}
      </div>
      <p className="panel-objective">{lesson.objective}</p>

      {!isTeacher && persona && (
        <div className="creative-card persona-playback-card">
          {watchingPersona ? (
            <>
              <div className="creative-thumb creative-thumb-mock creative-thumb-mock-video">
                <IconSparkle />
              </div>
              <span className="status-pill creative-preview-badge">
                Preview — avatar narration isn't connected to a rendering provider yet
              </span>
            </>
          ) : (
            <button type="button" className="btn btn-primary" onClick={() => setWatchingPersona(true)}>
              <IconSparkle /> Watch {persona.name} explain this
            </button>
          )}
        </div>
      )}

      <div className="slides-list">
        {slides.map((s, i) => (
          <div className="slide-card" key={i}>
            <h4>{s.heading}</h4>
            <ul>{s.bullets.map((b, bi) => <li key={bi}>{b}</li>)}</ul>
          </div>
        ))}
      </div>

      {speakerNotes && (
        <div className="notes-block">
          <label className="field-label">Speaker notes</label>
          <p>{speakerNotes}</p>
        </div>
      )}

      {isTeacher ? (
        teacherLesson?.content?.quiz ? (
          <div className="quiz-block">
            <label className="field-label">Quiz</label>
            <p className="quiz-question">{teacherLesson.content.quiz.question}</p>
            <ul className="quiz-options">
              {teacherLesson.content.quiz.options.map((opt, i) => (
                <li key={i} className={i === teacherLesson.content!.quiz!.correctIndex ? "is-correct" : ""}>
                  {opt}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="hint">No quiz yet.</p>
        )
      ) : studentLesson?.quiz ? (
        <QuizTaker
          lessonId={lessonId}
          quiz={studentLesson.quiz}
          onResult={(res) => {
            if (res.correct) {
              setLessonComplete(session.user.id, courseId, lessonId, true);
              setComplete(true);
            }
          }}
        />
      ) : (
        <p className="hint">No quiz for this lesson.</p>
      )}

      <Assignment courseId={courseId} lessonId={lessonId} lessonTitle={lesson.title} session={session} />
      <Discussion courseId={courseId} lessonId={lessonId} lessonTitle={lesson.title} session={session} />
      {!isTeacher && <TAChat courseId={courseId} />}
      {!isTeacher && notesOpen && (
        <NotesPanel courseId={courseId} lessonId={lessonId} userId={session.user.id} onClose={() => setNotesOpen(false)} />
      )}
    </div>
  );
}
