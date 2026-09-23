import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchMyEnrolledCourses, listMyCourses } from "../api.ts";
import type { Session } from "../auth.ts";
import type { Course, CoursePreview } from "../types.ts";
import { getCompletedLessonIds, getRoster } from "./traditionalData.ts";

interface DashboardProps {
  session: Session;
}

function lessonCount(weeks: { lessons: unknown[] }[]): number {
  return weeks.reduce((n, w) => n + w.lessons.length, 0);
}

export default function Dashboard({ session }: DashboardProps) {
  const isTeacher = session.user.role === "teacher";
  const [courses, setCourses] = useState<(Course | CoursePreview)[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (isTeacher ? listMyCourses() : fetchMyEnrolledCourses())
      .then((data) => { if (!cancelled) setCourses(data); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); });
    return () => { cancelled = true; };
  }, [isTeacher]);

  return (
    <div className="educa-page">
      <h2 className="educa-page-title">{isTeacher ? "My courses" : "My learning"}</h2>
      {error && <div className="error-banner">{error}</div>}

      {!courses ? (
        <p className="hint">Loading…</p>
      ) : courses.length === 0 ? (
        <div className="educa-empty">
          <p className="hint">
            {isTeacher
              ? "You haven't published anything yet. Build a course with the AI in Studio, then publish a lesson to see it here."
              : "You're not enrolled in anything yet."}
          </p>
          <Link to={isTeacher ? "/" : "/educa/catalog"} className="btn btn-primary">
            {isTeacher ? "Open Studio" : "Browse the catalog"}
          </Link>
        </div>
      ) : (
        <div className="course-card-grid">
          {courses.map((c) => {
            const total = lessonCount(c.weeks);
            const done = isTeacher
              ? 0
              : c.weeks.reduce((n, w) => {
                  const completed = getCompletedLessonIds(session.user.id, c.id);
                  return n + w.lessons.filter((l) => completed.has(l.id)).length;
                }, 0);
            return (
              <Link to={`/educa/courses/${c.id}`} className="course-card" key={c.id}>
                <h3>{c.title}</h3>
                <p className="course-card-audience">{c.audience}</p>
                <span className="hint-inline">
                  {total} lesson(s){isTeacher ? "" : " published"}
                  {isTeacher && ` · ${getRoster(c.id).length} enrolled`}
                </span>
                {!isTeacher && total > 0 && (
                  <div className="progress-bar progress-bar-sm">
                    <div className="progress-bar-fill" style={{ width: `${Math.round((done / total) * 100)}%` }} />
                  </div>
                )}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
