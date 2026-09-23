import { useEffect, useState } from "react";
import type { Session } from "../auth.ts";
import { getSubmissions, gradeSubmission, submitAssignment, type AssignmentSubmission } from "./traditionalData.ts";

interface AssignmentProps {
  courseId: string;
  lessonId: string;
  lessonTitle: string;
  session: Session;
}

function gradeTier(grade: number): string {
  if (grade >= 80) return "grade-good";
  if (grade >= 60) return "grade-ok";
  return "grade-low";
}

export default function Assignment({ courseId, lessonId, lessonTitle, session }: AssignmentProps) {
  const isTeacher = session.user.role === "teacher";
  const [submissions, setSubmissions] = useState<AssignmentSubmission[]>([]);
  const [text, setText] = useState("");
  const [gradeDrafts, setGradeDrafts] = useState<Record<string, string>>({});

  useEffect(() => {
    setSubmissions(getSubmissions(courseId, lessonId));
    setText("");
  }, [courseId, lessonId]);

  const mine = submissions.find((s) => s.studentId === session.user.id);

  function handleSubmit() {
    if (!text.trim()) return;
    setSubmissions(submitAssignment(courseId, lessonId, session.user.id, session.user.name, text.trim()));
  }

  function handleGrade(studentId: string) {
    const grade = Number(gradeDrafts[studentId]);
    if (Number.isNaN(grade) || grade < 0 || grade > 100) return;
    setSubmissions(gradeSubmission(courseId, lessonId, studentId, grade, ""));
  }

  return (
    <div className="assignment-block">
      <label className="field-label">Assignment</label>
      <p className="assignment-prompt">
        Submit a short written reflection: what's one way you'd apply "{lessonTitle}"?
      </p>

      {isTeacher ? (
        submissions.length === 0 ? (
          <p className="hint">No submissions yet.</p>
        ) : (
          <ul className="assignment-submission-list">
            {submissions.map((s) => (
              <li className="assignment-submission-row" key={s.studentId}>
                <div className="assignment-submission-head">
                  <strong>{s.studentName}</strong>
                  <span className="hint-inline">{new Date(s.submittedAt).toLocaleString()}</span>
                </div>
                <p>{s.text}</p>
                <div className="assignment-grade-row">
                  {s.grade != null ? (
                    <span className={`grade-pill ${gradeTier(s.grade)}`}>{s.grade}/100</span>
                  ) : (
                    <>
                      <input
                        type="number"
                        min={0}
                        max={100}
                        placeholder="Grade"
                        value={gradeDrafts[s.studentId] ?? ""}
                        onChange={(e) => setGradeDrafts((d) => ({ ...d, [s.studentId]: e.target.value }))}
                      />
                      <button type="button" className="btn" onClick={() => handleGrade(s.studentId)}>Save grade</button>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )
      ) : mine ? (
        <div className="assignment-submission-row">
          <p>{mine.text}</p>
          {mine.grade != null ? (
            <span className={`grade-pill ${gradeTier(mine.grade)}`}>
              {mine.grade}/100{mine.feedback ? ` — ${mine.feedback}` : ""}
            </span>
          ) : (
            <span className="hint-inline">Submitted — awaiting grade</span>
          )}
        </div>
      ) : (
        <div className="assignment-composer">
          <textarea rows={3} value={text} onChange={(e) => setText(e.target.value)} placeholder="Write your reflection…" />
          <button type="button" className="btn btn-primary" disabled={!text.trim()} onClick={handleSubmit}>Submit</button>
        </div>
      )}
    </div>
  );
}
