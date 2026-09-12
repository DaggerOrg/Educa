import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { enrollInCourse, fetchCatalog, fetchCourse, fetchMyEnrolledCourses } from "../api.ts";
import type { Session } from "../auth.ts";
import type { Course, CoursePreview, Lesson } from "../types.ts";

interface CourseDetailProps {
  session: Session;
}

export default function CourseDetail({ session }: CourseDetailProps) {
  const { courseId = "" } = useParams<{ courseId: string }>();
  const isTeacher = session.user.role === "teacher";
  const [course, setCourse] = useState<Course | null>(null);
  const [preview, setPreview] = useState<CoursePreview | null>(null);
  const [enrolled, setEnrolled] = useState(false);
  const [enrolling, setEnrolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    setNotFound(false);
    try {
      if (isTeacher) {
        setCourse(await fetchCourse(courseId));
        return;
      }
      const mine = await fetchMyEnrolledCourses();
      const mineMatch = mine.find((c) => c.id === courseId);
      if (mineMatch) {
        setPreview(mineMatch);
        setEnrolled(true);
        return;
      }
      const catalog = await fetchCatalog();
      const catalogMatch = catalog.find((c) => c.id === courseId);
      if (!catalogMatch) {
        setNotFound(true);
        return;
      }
      setPreview(catalogMatch);
      setEnrolled(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [courseId, isTeacher]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleEnroll() {
    setEnrolling(true);
    try {
      await enrollInCourse(courseId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setEnrolling(false);
    }
  }

  if (error) {
    return (
      <div className="educa-page">
        <div className="error-banner">{error}</div>
      </div>
    );
  }
  if (notFound) {
    return (
      <div className="educa-page">
        <p className="hint">Course not found.</p>
      </div>
    );
  }

  const data = isTeacher ? course : preview;
  if (!data) {
    return (
      <div className="educa-page">
        <p className="hint">Loading…</p>
      </div>
    );
  }

  const canOpenLessons = isTeacher || enrolled;

  return (
    <div className="educa-page">
      <Link to={isTeacher ? "/educa" : "/educa/catalog"} className="hint-inline educa-back">← Back</Link>
      <h2 className="educa-page-title">{data.title}</h2>
      <p className="course-audience">{data.audience}</p>

      {isTeacher ? (
        <p className="hint">
          Read-only here — edit content, slides, and quizzes in <Link to="/" className="text-link">Studio</Link>.
        </p>
      ) : !enrolled ? (
        <button type="button" className="btn btn-primary" disabled={enrolling} onClick={handleEnroll}>
          {enrolling ? "Enrolling…" : "Enroll in this course"}
        </button>
      ) : null}

      {!canOpenLessons ? (
        <p className="hint">Enroll to open its lessons.</p>
      ) : (
        <div className="educa-week-list">
          {data.weeks.map((w) => (
            <div className="week-block" key={w.week}>
              <div className="week-head">
                <span className="week-head-title">Week {w.week} — {w.title}</span>
              </div>
              {w.lessons.length === 0 ? (
                <p className="hint">No published lessons yet.</p>
              ) : (
                w.lessons.map((l) => (
                  <Link
                    to={`/educa/courses/${courseId}/lessons/${l.id}`}
                    className="lesson-row educa-lesson-link"
                    key={l.id}
                  >
                    <div className="lesson-row-top">
                      <strong>{l.title}</strong>
                      {isTeacher && (() => {
                        const full = l as Lesson;
                        const status = full.published ? "published" : full.approved ? "approved" : "draft";
                        return (
                          <span className={`status-pill status-${status}`}>
                            {full.published ? "Published" : full.approved ? "Approved" : "Draft"}
                          </span>
                        );
                      })()}
                    </div>
                    <p className="lesson-objective-text">{l.objective}</p>
                  </Link>
                ))
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
