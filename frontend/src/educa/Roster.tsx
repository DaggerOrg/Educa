import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchCourse } from "../api.ts";
import type { Session } from "../auth.ts";
import CourseTabs from "./CourseTabs.tsx";
import { enrollBulk, enrollManually, getRoster, unenroll, type RosterStudent } from "./traditionalData.ts";

interface RosterProps {
  session: Session;
}

export default function Roster({ session }: RosterProps) {
  const { courseId = "" } = useParams<{ courseId: string }>();
  const isTeacher = session.user.role === "teacher";
  const [title, setTitle] = useState("");
  const [roster, setRoster] = useState<RosterStudent[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [bulk, setBulk] = useState("");
  const [showBulk, setShowBulk] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setRoster(getRoster(courseId));
    fetchCourse(courseId)
      .then((c) => setTitle(c.title))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [courseId]);

  function handleAdd() {
    if (!name.trim() || !email.trim()) return;
    setRoster(enrollManually(courseId, name.trim(), email.trim()));
    setName("");
    setEmail("");
  }

  function handleBulkAdd() {
    const emails = bulk.split(/[\n,]/).map((e) => e.trim()).filter(Boolean);
    if (!emails.length) return;
    setRoster(enrollBulk(courseId, emails));
    setBulk("");
    setShowBulk(false);
  }

  if (!isTeacher) {
    return (
      <div className="educa-page">
        <p className="hint">Roster is only available to teachers.</p>
      </div>
    );
  }

  return (
    <div className="educa-page">
      <Link to={`/educa/courses/${courseId}`} className="hint-inline educa-back">← Back to course</Link>
      <h2 className="educa-page-title">{title || "Roster"}</h2>
      <CourseTabs courseId={courseId} isTeacher={isTeacher} />

      {error && <div className="error-banner">{error}</div>}
      <p className="hint">{roster.length} student(s) enrolled.</p>

      <div className="roster-scroll">
        <table className="roster-table">
          <thead>
            <tr><th>Name</th><th>Email</th><th>Method</th><th>Enrolled</th><th /></tr>
          </thead>
          <tbody>
            {roster.map((s) => (
              <tr key={s.id}>
                <td>{s.name}</td>
                <td>{s.email}</td>
                <td><span className="status-pill status-draft">{s.method}</span></td>
                <td className="hint-inline">{s.enrolledAt ? new Date(s.enrolledAt).toLocaleDateString() : "—"}</td>
                <td>
                  <button type="button" className="btn roster-remove" onClick={() => setRoster(unenroll(courseId, s.id))}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="roster-forms">
        <div className="roster-form">
          <label className="field-label">Enroll a student</label>
          <div className="roster-form-row">
            <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
            <input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <button type="button" className="btn btn-primary" onClick={handleAdd}>Add</button>
          </div>
        </div>

        <div className="roster-form">
          <button type="button" className="btn" onClick={() => setShowBulk((v) => !v)}>
            {showBulk ? "Cancel bulk add" : "Bulk add (cohort)"}
          </button>
          {showBulk && (
            <div className="roster-bulk">
              <textarea
                rows={3}
                placeholder="One email per line, or comma-separated"
                value={bulk}
                onChange={(e) => setBulk(e.target.value)}
              />
              <button type="button" className="btn btn-primary" onClick={handleBulkAdd}>Add all</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
