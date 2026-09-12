import { useState } from "react";
import { IconChevronLeft, IconEdit, IconObjective } from "./icons.tsx";

export type CourseTool = "syllabus" | "exercises";

interface ToolEntry {
  key: CourseTool;
  label: string;
  icon: typeof IconEdit;
}

// Extensible on purpose -- add another entry here for the next
// course-builder tool. "Syllabus" isn't really a separate feature (it's
// today's existing Syllabus/Lesson drill-down), but it needs a slot in
// this rail too so there's a way back to it once another tool is active.
const TOOLS: ToolEntry[] = [
  { key: "syllabus", label: "Syllabus", icon: IconEdit },
  { key: "exercises", label: "Exercises Builder", icon: IconObjective },
];

interface CourseToolsRailProps {
  active: CourseTool;
  onSelect: (tool: CourseTool) => void;
}

export default function CourseToolsRail({ active, onSelect }: CourseToolsRailProps) {
  const [expanded, setExpanded] = useState(true);

  return (
    <nav className={`tools-rail${expanded ? "" : " is-collapsed"}`}>
      <div className="tools-rail-items">
        {TOOLS.map(({ key, label, icon: Icon }) => (
          <button
            type="button"
            key={key}
            className={`nav-drawer-btn${active === key ? " is-active" : ""}`}
            title={label}
            aria-current={active === key ? "page" : undefined}
            onClick={() => onSelect(key)}
          >
            <Icon />
            <span className="nav-drawer-label">{label}</span>
          </button>
        ))}
      </div>
      <button
        type="button"
        className="nav-drawer-toggle"
        title={expanded ? "Collapse tools" : "Expand tools"}
        aria-label={expanded ? "Collapse tools" : "Expand tools"}
        onClick={() => setExpanded((v) => !v)}
      >
        <IconChevronLeft className="nav-drawer-toggle-icon" />
      </button>
    </nav>
  );
}
