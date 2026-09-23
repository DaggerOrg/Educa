import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchCourse, fetchMyEnrolledCourses, fetchMyQuizAttempts, fetchStudentLesson } from "../api.ts";
import type { Session } from "../auth.ts";
import CourseTabs from "./CourseTabs.tsx";
import { aggregateGrade, getRoster, getSubmissions, seededScore, type RosterStudent } from "./traditionalData.ts";

interface GradebookProps {
  session: Session;
}

interface LessonColumn {
  lessonId: string;
  lessonTitle: string;
}

function gradeTier(grade: number): string {
  if (grade >= 80) return "grade-good";
  if (grade >= 60) return "grade-ok";
  return "grade-low";
}

function GradePill({ value }: { value: number | null }) {
  if (value == null) return <span className="hint-inline">—</span>;
  return <span className={`grade-pill ${gradeTier(value)}`}>{Math.round(value)}%</span>;
}

export default function Gradebook({ session }: GradebookProps) {
  const { courseId = "" } = useParams<{ courseId: string }>();
  const isTeacher = session.user.role === "teacher";
  const [title, setTitle] = useState("");
  const [quizColumns, setQuizColumns] = useState<LessonColumn[]>([]);
  const [assignmentColumns, setAssignmentColumns] = useState<LessonColumn[]>([]);
  const [roster, setRoster] = useState<RosterStudent[]>([]);
  const [quizScores, setQuizScores] = useState<Record<string, Record<string, number>>>({});
  const [assignmentScores, setAssignmentScores] = useState<Record<string, Record<string, number>>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadTeacher() {
      const course = await fetchCourse(courseId);
      if (cancelled) return;
      setTitle(course.title);

      const quizCols: LessonColumn[] = [];
      const asgCols: LessonColumn[] = [];
      for (const w of course.weeks) {
        for (const l of w.lessons) {
          if (!l.published) continue;
          asgCols.push({ lessonId: l.id, lessonTitle: l.title });
          if (l.content?.quiz) quizCols.push({ lessonId: l.id, lessonTitle: l.title });
        }
      }
      setQuizColumns(quizCols);
      setAssignmentColumns(asgCols);

      const rosterList = getRoster(courseId);
      setRoster(rosterList);

      const qScores: Record<string, Record<string, number>> = {};
      for (const s of rosterList) {
        qScores[s.id] = {};
        for (const col of quizCols) qScores[s.id][col.lessonId] = seededScore(`${courseId}-${s.id}-${col.lessonId}`);
      }
      setQuizScores(qScores);

      const aScores: Record<string, Record<string, number>> = {};
      for (const col of asgCols) {
        for (const sub of getSubmissions(courseId, col.lessonId)) {
          if (sub.grade == null) continue;
          aScores[sub.studentId] = aScores[sub.studentId] ?? {};
          aScores[sub.studentId][col.lessonId] = sub.grade;
        }
      }
      setAssignmentScores(aScores);
    }

    async function loadStudent() {
      const mine = await fetchMyEnrolledCourses();
      const course = mine.find((c) => c.id === courseId);
      if (!course) {
        if (!cancelled) setError("Course not found, or you're not enrolled.");
        return;
      }
      if (cancelled) return;
      setTitle(course.title);

      const lessons = course.weeks.flatMap((w) => w.lessons);
      const details = await Promise.all(lessons.map((l) => fetchStudentLesson(courseId, l.id).catch(() => null)));
      if (cancelled) return;

      const quizCols: LessonColumn[] = [];
      const asgCols: LessonColumn[] = [];
      const qScore: Record<string, number> = {};

      for (let i = 0; i < details.length; i++) {
        const detail = details[i];
        if (!detail) continue;
        asgCols.push({ lessonId: lessons[i].id, lessonTitle: lessons[i].title });
        if (detail.quiz) {
          quizCols.push({ lessonId: lessons[i].id, lessonTitle: lessons[i].title });
          const attempts = await fetchMyQuizAttempts(lessons[i].id).catch(() => []);
          if (attempts.length) {
            const best = attempts.reduce((a, b) => (b.score / b.maxScore > a.score / a.maxScore ? b : a));
            qScore[lessons[i].id] = (best.score / best.maxScore) * 100;
          }
        }
      }
      if (cancelled) return;
      setQuizColumns(quizCols);
      setAssignmentColumns(asgCols);
      setQuizScores({ [session.user.id]: qScore });

      const aScore: Record<string, number> = {};
      for (const col of asgCols) {
        const mine2 = getSubmissions(courseId, col.lessonId).find((s) => s.studentId === session.user.id);
        if (mine2?.grade != null) aScore[col.lessonId] = mine2.grade;
      }
      setAssignmentScores({ [session.user.id]: aScore });
      setRoster([{ id: session.user.id, name: session.user.name, email: session.user.email, method: "self", enrolledAt: "" }]);
    }

    setLoading(true);
    setError(null);
    (isTeacher ? loadTeacher() : loadStudent())
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [courseId, isTeacher, session.user.id, session.user.name, session.user.email]);

  return (
    <div className="educa-page">
      <Link to={`/educa/courses/${courseId}`} className="hint-inline educa-back">← Back to course</Link>
      <h2 className="educa-page-title">{title || "Gradebook"}</h2>
      <CourseTabs courseId={courseId} isTeacher={isTeacher} />

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <p className="hint">Loading…</p>
      ) : roster.length === 0 ? (
        <p className="hint">No students enrolled yet.</p>
      ) : quizColumns.length === 0 && assignmentColumns.length === 0 ? (
        <p className="hint">Nothing graded yet — publish a lesson with a quiz or assignment to see grades here.</p>
      ) : (
        <>
          <div className="gradebook-scroll">
            <table className="gradebook-table">
              <thead>
                <tr>
                  <th>Student</th>
                  {quizColumns.map((c) => (
                    <th key={`q-${c.lessonId}`}>{c.lessonTitle}<span className="hint-inline">Quiz</span></th>
                  ))}
                  {assignmentColumns.map((c) => (
                    <th key={`a-${c.lessonId}`}>{c.lessonTitle}<span className="hint-inline">Assignment</span></th>
                  ))}
                  <th>Course grade</th>
                </tr>
              </thead>
              <tbody>
                {roster.map((s) => {
                  const qVals = quizColumns
                    .map((c) => quizScores[s.id]?.[c.lessonId])
                    .filter((v): v is number => v != null);
                  const aVals = assignmentColumns
                    .map((c) => assignmentScores[s.id]?.[c.lessonId])
                    .filter((v): v is number => v != null);
                  const overall = aggregateGrade(qVals, aVals);
                  return (
                    <tr key={s.id}>
                      <td>{s.name}</td>
                      {quizColumns.map((c) => (
                        <td key={c.lessonId}><GradePill value={quizScores[s.id]?.[c.lessonId] ?? null} /></td>
                      ))}
                      {assignmentColumns.map((c) => (
                        <td key={c.lessonId}><GradePill value={assignmentScores[s.id]?.[c.lessonId] ?? null} /></td>
                      ))}
                      <td><GradePill value={overall} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="hint gradebook-footnote">
            Course grade weights quizzes 60% and assignments 40%, averaging only graded items.
          </p>
        </>
      )}
    </div>
  );
}
