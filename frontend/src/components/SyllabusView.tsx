import { useState } from "react";
import type { Course, Week } from "../types.ts";
import { IconChevronDown } from "./icons.tsx";

interface SyllabusViewProps {
  course: Course;
  onSelect: (id: string) => void;
}

function countLessons(weeks: Week[]) {
  let total = 0;
  let published = 0;
  for (const w of weeks) {
    for (const l of w.lessons) {
      total += 1;
      if (l.published) published += 1;
    }
  }
  return { total, published };
}

export default function SyllabusView({ course, onSelect }: SyllabusViewProps) {
  // Weeks are expanded by default; collapsing one hides its lessons without
  // losing scroll position on long syllabi -- keyed by week number/title
  // since lessons don't carry a separate week id.
  const [collapsed, setCollapsed] = useState<Set<string | number>>(() => new Set());

  const { total, published } = countLessons(course.weeks);

  function toggleWeek(key: string | number) {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  return (
    <section className="educa-page course-overview">
      <h2 className="course-title">{course.title}</h2>
      <p className="course-audience">{course.audience || "No audience set"}</p>

      {total > 0 && (
        <div className="course-progress">
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${(published / total) * 100}%` }} />
          </div>
          <span className="progress-label">{published} of {total} lessons published</span>
        </div>
      )}

      <div className="educa-week-list">
        {course.weeks.map((w) => {
          const key = w.week ?? w.title;
          const isCollapsed = collapsed.has(key);
          const weekPublished = w.lessons.filter((l) => l.published).length;
          return (
            <div className="week-block" key={key}>
              <button type="button" className="week-head" onClick={() => toggleWeek(key)} aria-expanded={!isCollapsed}>
                <IconChevronDown className={`week-chevron${isCollapsed ? " is-collapsed" : ""}`} />
                <span className="week-head-title">Week {w.week} — {w.title}</span>
                <span className="week-head-count">{weekPublished}/{w.lessons.length}</span>
              </button>
              {!isCollapsed && (
                w.lessons.length === 0 ? (
                  <p className="hint">No lessons yet.</p>
                ) : (
                  w.lessons.map((l) => {
                    const status = l.published ? "published" : l.approved ? "approved" : "draft";
                    const statusLabel = l.published ? "Published" : l.approved ? "Approved" : "Draft";
                    return (
                      <button
                        type="button"
                        key={l.id}
                        className="lesson-row educa-lesson-link"
                        onClick={() => onSelect(l.id)}
                      >
                        <div className="lesson-row-top">
                          <strong>{l.title}</strong>
                          <span className={`status-pill status-${status}`}>{statusLabel}</span>
                        </div>
                        <p className="lesson-objective-text">{l.objective}</p>
                      </button>
                    );
                  })
                )
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
