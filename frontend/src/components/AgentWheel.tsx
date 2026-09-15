import { IconSparkle } from "./icons.tsx";
import { AGENT_REGISTRY } from "../agentRegistry.ts";
import type { CourseTool } from "./CourseToolsRail.tsx";
import type { Section } from "../App.tsx";

interface AgentWheelProps {
  section: Section;
  courseTool: CourseTool;
  isRunning: boolean;
  disabledAgentKeys: Set<string>;
  onActivate: () => void;
  onOpenAgentInfo: (key: string) => void;
}

const RADIUS = 42;
const ICON_SIZE = 34;

export default function AgentWheel({
  section,
  courseTool,
  isRunning,
  disabledAgentKeys,
  onActivate,
  onOpenAgentInfo,
}: AgentWheelProps) {
  // Agents outside the current context simply aren't rendered -- there's no
  // way for the frontend to know which curriculum_team member is actually
  // handling a given run (it's one Team behind one AG-UI agent id), so
  // "active" is a per-context statement ("something relevant to this screen
  // is running"), not a claim about one specific specialist. A teacher can
  // also turn an agent off entirely from Settings -> AI Agents.
  const visible = AGENT_REGISTRY.filter((a) => {
    if (disabledAgentKeys.has(a.key)) return false;
    if (!a.sections.includes(section)) return false;
    if (section === "course" && a.courseTools && !a.courseTools.includes(courseTool)) return false;
    return true;
  });

  if (visible.length === 0) return null;

  const angleStep = 360 / visible.length;

  return (
    <div className={`agent-wheel${isRunning ? " is-active" : ""}`}>
      <div className="agent-wheel-ring">
        {visible.map((a, i) => {
          const angleDeg = i * angleStep - 90;
          const rad = (angleDeg * Math.PI) / 180;
          const x = RADIUS * Math.cos(rad);
          const y = RADIUS * Math.sin(rad);
          return (
            <button
              type="button"
              key={a.key}
              className={`agent-wheel-icon agent-wheel-icon--${a.hue}${isRunning ? " is-running" : ""}`}
              style={{ left: `calc(50% + ${x}px - ${ICON_SIZE / 2}px)`, top: `calc(50% + ${y}px - ${ICON_SIZE / 2}px)` }}
              onClick={() => onOpenAgentInfo(a.key)}
            >
              {a.glyph}
            </button>
          );
        })}
      </div>
      <button type="button" className="agent-wheel-hub" onClick={onActivate}>
        <IconSparkle />
      </button>
    </div>
  );
}
