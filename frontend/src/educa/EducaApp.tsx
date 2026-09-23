import { Link, Route, Routes } from "react-router-dom";
import type { Session } from "../auth.ts";
import ThemeToggle from "../components/ThemeToggle.tsx";
import Catalog from "./Catalog.tsx";
import CourseDetail from "./CourseDetail.tsx";
import Dashboard from "./Dashboard.tsx";
import Gradebook from "./Gradebook.tsx";
import LessonView from "./LessonView.tsx";
import Roster from "./Roster.tsx";

interface EducaAppProps {
  session: Session;
  onLogOut: () => void;
}

// The traditional, Moodle-style half of Educa: a course catalog, self-
// enrollment, reading a published lesson, and taking its quiz -- usable by
// either role, alongside (not instead of) Studio's AI authoring at "/".
// See docs/moodle/mind-map/README.md for the gap analysis this closes.
export default function EducaApp({ session, onLogOut }: EducaAppProps) {
  const isTeacher = session.user.role === "teacher";

  return (
    <div className="layout">
      <header className="topbar">
        <Link to="/educa" className="wordmark">EDUCA<span>.</span></Link>
        <div className="topbar-right">
          <Link to="/educa/catalog" className="btn">Catalog</Link>
          {isTeacher && (
            <Link to="/" className="btn ask-ai-btn">
              Studio (AI builder)
            </Link>
          )}
          <div className="topbar-account">
            <ThemeToggle />
            <span className="topbar-email">{session.user.email}</span>
            <span className="status-pill status-approved">{session.user.role}</span>
            <button type="button" className="btn topbar-logout" onClick={onLogOut}>
              Log out
            </button>
          </div>
        </div>
      </header>

      <div className="educa-body">
        <Routes>
          <Route index element={<Dashboard session={session} />} />
          <Route path="catalog" element={<Catalog session={session} />} />
          <Route path="courses/:courseId" element={<CourseDetail session={session} />} />
          <Route path="courses/:courseId/gradebook" element={<Gradebook session={session} />} />
          <Route path="courses/:courseId/roster" element={<Roster session={session} />} />
          <Route path="courses/:courseId/lessons/:lessonId" element={<LessonView session={session} />} />
        </Routes>
      </div>
    </div>
  );
}
