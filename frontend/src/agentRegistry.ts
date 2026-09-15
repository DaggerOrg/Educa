import type { CourseTool } from "./components/CourseToolsRail.tsx";
import type { Section } from "./App.tsx";

export type AgentHue = "accent" | "success" | "warning" | "destructive" | "orange";

export interface AgentDef {
  key: string;
  label: string;
  glyph: string;
  description: string;
  // Identity color -- the app's existing categorical hue tokens (see
  // styles.css's "categorical hue system" comment, built for exactly this:
  // per-feature colored icon badges). Hues are only picked to be distinct
  // *within* a group that can render together on the wheel -- see
  // sections/courseTools below -- so a few are deliberately reused across
  // mutually-exclusive contexts (e.g. curriculum/exercises/knowledge_graph
  // all use "accent").
  hue: AgentHue;
  sections: Section[];
  // Only checked when `section === "course"`; omit to show for every tool tab.
  courseTools?: CourseTool[];
}

// One entry per backend specialist (backend/app/agents/team.py's
// curriculum_team members) that has a real UI moment in Studio right now.
// `teaching_assistant.py` is deliberately excluded -- it's a separate REST
// agent with no run happening from Studio's own screens (see
// TeachingAssistantConfig.tsx, which only edits its config, never chats).
// Shared by AgentWheel.tsx (the wheel widget) and SettingsPanel.tsx's
// "AI Agents" tab (descriptions + on/off toggles) so both read one list.
export const AGENT_REGISTRY: AgentDef[] = [
  {
    key: "curriculum",
    label: "Curriculum",
    glyph: "CU",
    description: "Designs and updates your course's week-by-week syllabus structure.",
    hue: "accent",
    sections: ["courses", "course"],
    courseTools: ["syllabus"],
  },
  {
    key: "lesson_content",
    label: "Lesson Content",
    glyph: "LC",
    description: "Drafts a lesson's slides and speaker notes.",
    hue: "orange",
    sections: ["course"],
    courseTools: ["syllabus"],
  },
  {
    key: "quiz",
    label: "Quiz",
    glyph: "QZ",
    description: "Writes the graded multiple-choice question for a lesson.",
    hue: "warning",
    sections: ["course"],
    courseTools: ["syllabus"],
  },
  {
    key: "materials",
    label: "Materials",
    glyph: "MA",
    description: "Grounds syllabi and lessons in the course materials you've uploaded, instead of inventing examples.",
    hue: "success",
    sections: ["courses", "course"],
    courseTools: ["syllabus", "exercises"],
  },
  {
    key: "exercises",
    label: "Exercises",
    glyph: "EX",
    description: "Generates practice sets -- flashcards, true/false, and extra multiple-choice questions.",
    hue: "accent",
    sections: ["course"],
    courseTools: ["exercises"],
  },
  {
    key: "feedback",
    label: "Feedback",
    glyph: "FB",
    description: "Reviews student quiz attempts and writes personalized feedback.",
    hue: "destructive",
    sections: ["course"],
    courseTools: ["syllabus", "exercises"],
  },
  {
    key: "creative",
    label: "Creative",
    glyph: "CR",
    description: "Generates classroom-ready images for your lessons and courses.",
    hue: "orange",
    sections: ["creative"],
  },
  {
    key: "knowledge_graph",
    label: "Knowledge Graph",
    glyph: "KG",
    description: "Proposes a concept map for a course from its syllabus or uploaded materials.",
    hue: "accent",
    sections: ["knowledge-graph"],
  },
];

const DISABLED_AGENTS_KEY = "educa_disabled_agents";

export function loadDisabledAgentKeys(): Set<string> {
  try {
    const raw = localStorage.getItem(DISABLED_AGENTS_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

export function saveDisabledAgentKeys(keys: Set<string>) {
  try {
    localStorage.setItem(DISABLED_AGENTS_KEY, JSON.stringify([...keys]));
  } catch {
    // Non-critical: the on/off toggle just won't persist across reloads.
  }
}
