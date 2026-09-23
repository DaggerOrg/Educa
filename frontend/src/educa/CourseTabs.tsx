import { NavLink } from "react-router-dom";

interface CourseTabsProps {
  courseId: string;
  isTeacher: boolean;
}

export default function CourseTabs({ courseId, isTeacher }: CourseTabsProps) {
  const tabClass = ({ isActive }: { isActive: boolean }) => `course-tab${isActive ? " is-active" : ""}`;

  return (
    <nav className="course-tabs">
      <NavLink to={`/educa/courses/${courseId}`} end className={tabClass}>
        Content
      </NavLink>
      <NavLink to={`/educa/courses/${courseId}/gradebook`} className={tabClass}>
        {isTeacher ? "Gradebook" : "My grades"}
      </NavLink>
      {isTeacher && (
        <NavLink to={`/educa/courses/${courseId}/roster`} className={tabClass}>
          Roster
        </NavLink>
      )}
    </nav>
  );
}
