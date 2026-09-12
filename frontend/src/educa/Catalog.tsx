import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { enrollInCourse, fetchCatalog, fetchMyEnrolledCourses } from "../api.ts";
import type { Session } from "../auth.ts";
import type { CoursePreview } from "../types.ts";

interface CatalogProps {
  session: Session;
}

export default function Catalog({ session }: CatalogProps) {
  const isStudent = session.user.role === "student";
  const [courses, setCourses] = useState<CoursePreview[] | null>(null);
  const [enrolledIds, setEnrolledIds] = useState<Set<string>>(() => new Set());
  const [enrollingId, setEnrollingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [catalog, mine] = await Promise.all([
        fetchCatalog(),
        isStudent ? fetchMyEnrolledCourses() : Promise.resolve<CoursePreview[]>([]),
      ]);
      setCourses(catalog);
      setEnrolledIds(new Set(mine.map((c) => c.id)));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [isStudent]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleEnroll(courseId: string) {
    setEnrollingId(courseId);
    try {
      await enrollInCourse(courseId);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setEnrollingId(null);
    }
  }

  return (
    <div className="educa-page">
      <h2 className="educa-page-title">Catalog</h2>
      <p className="hint">Every published course, open to enroll.</p>
      {error && <div className="error-banner">{error}</div>}

      {!courses ? (
        <p className="hint">Loading…</p>
      ) : courses.length === 0 ? (
        <p className="hint">Nothing published yet — check back soon.</p>
      ) : (
        <div className="course-card-grid">
          {courses.map((c) => {
            const lessonTotal = c.weeks.reduce((n, w) => n + w.lessons.length, 0);
            const enrolled = enrolledIds.has(c.id);
            return (
              <div className="course-card course-card-catalog" key={c.id}>
                <Link to={`/educa/courses/${c.id}`} className="course-card-link">
                  <h3>{c.title}</h3>
                  <p className="course-card-audience">{c.audience}</p>
                  <span className="hint-inline">{lessonTotal} lesson(s) published</span>
                </Link>
                {isStudent && (
                  <button
                    type="button"
                    className={`btn ${enrolled ? "" : "btn-primary"}`}
                    disabled={enrolled || enrollingId === c.id}
                    onClick={() => handleEnroll(c.id)}
                  >
                    {enrolled ? "Enrolled" : enrollingId === c.id ? "Enrolling…" : "Enroll"}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
