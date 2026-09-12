import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchCourse, fetchStudentLesson } from "../api.ts";
import type { Session } from "../auth.ts";
import type { Course, Lesson, StudentLesson } from "../types.ts";
import QuizTaker from "./QuizTaker.tsx";

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
    <div className="educa-page">
      <Link to={`/educa/courses/${courseId}`} className="hint-inline educa-back">← Back to course</Link>
      <h2 className="educa-page-title">{lesson.title}</h2>
      <p className="panel-objective">{lesson.objective}</p>

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
        <QuizTaker lessonId={lessonId} quiz={studentLesson.quiz} />
      ) : (
        <p className="hint">No quiz for this lesson.</p>
      )}
    </div>
  );
}
