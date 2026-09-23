import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { enrollInCourse, fetchCatalog, fetchCourse, fetchMyEnrolledCourses } from "../api.ts";
import type { Session } from "../auth.ts";
import { IconMedia } from "../components/icons.tsx";
import TAChat from "../components/TAChat.tsx";
import { StudentStoryViewer } from "../story/StoryPlayer.tsx";
import { listReadyStories } from "../studentAiApi.ts";
import type { Course, CoursePreview, Lesson } from "../types.ts";
import CourseTabs from "./CourseTabs.tsx";
import { getCompletedLessonIds } from "./traditionalData.ts";

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
  const [storyModules, setStoryModules] = useState<Set<string>>(() => new Set());
  const [watching, setWatching] = useState<string | null>(null);

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

  // Which modules have a story a student can watch. A failure just means no buttons.
  useEffect(() => {
    if (isTeacher || !enrolled) return;
    listReadyStories(courseId)
      .then((stories) => setStoryModules(new Set(stories.map((s) => s.moduleId))))
      .catch(() => setStoryModules(new Set()));
  }, [courseId, isTeacher, enrolled]);

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
  const completed = !isTeacher && enrolled ? getCompletedLessonIds(session.user.id, courseId) : new Set<string>();
  const totalLessons = data.weeks.reduce((n, w) => n + w.lessons.length, 0);
  const completedCount = data.weeks.reduce((n, w) => n + w.lessons.filter((l) => completed.has(l.id)).length, 0);

  return (
    <div className="educa-page">
      <Link to={isTeacher ? "/educa" : "/educa/catalog"} className="hint-inline educa-back">← Back</Link>
      <h2 className="educa-page-title">{data.title}</h2>
      <p className="course-audience">{data.audience}</p>
      <CourseTabs courseId={courseId} isTeacher={isTeacher} />
      {!isTeacher && enrolled && <TAChat courseId={courseId} />}

      {isTeacher ? (
        <p className="hint">
          Read-only here — edit content, slides, and quizzes in <Link to="/" className="text-link">Studio</Link>.
        </p>
      ) : !enrolled ? (
        <button type="button" className="btn btn-primary" disabled={enrolling} onClick={handleEnroll}>
          {enrolling ? "Enrolling…" : "Enroll in this course"}
        </button>
      ) : totalLessons > 0 ? (
        <div className="progress-block">
          <div className="progress-bar">
            <div className="progress-bar-fill" style={{ width: `${Math.round((completedCount / totalLessons) * 100)}%` }} />
          </div>
          <span className="hint-inline">{completedCount} of {totalLessons} lessons complete</span>
        </div>
      ) : null}

      {!canOpenLessons ? (
        <p className="hint">Enroll to open its lessons.</p>
      ) : (
        <div className="educa-week-list">
          {data.weeks.map((w) => (
            <div className="week-block" key={w.week}>
              <div className="week-head">
                <span className="week-head-title">Week {w.week} — {w.title}</span>
                {!isTeacher && enrolled && w.moduleId && storyModules.has(w.moduleId) && (
                  <button type="button" className="btn week-story-btn" onClick={() => setWatching(w.moduleId!)}>
                    <IconMedia /> Watch story
                  </button>
                )}
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
                      {isTeacher ? (() => {
                        const full = l as Lesson;
                        const status = full.published ? "published" : full.approved ? "approved" : "draft";
                        return (
                          <span className={`status-pill status-${status}`}>
                            {full.published ? "Published" : full.approved ? "Approved" : "Draft"}
                          </span>
                        );
                      })() : completed.has(l.id) ? (
                        <span className="status-pill status-published">Done</span>
                      ) : null}
                    </div>
                    <p className="lesson-objective-text">{l.objective}</p>
                  </Link>
                ))
              )}
            </div>
          ))}
        </div>
      )}
      {watching && <StudentStoryViewer courseId={courseId} moduleId={watching} onClose={() => setWatching(null)} />}
    </div>
  );
}
