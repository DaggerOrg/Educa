import FlagBadge from "../canvas/FlagBadge.tsx";
import { STATUS_LABELS, type KnowledgeStatus } from "../../types/knowledgeGraph.ts";

const STATUS_ORDER: KnowledgeStatus[] = ["teacher_approved", "needs_review", "ai_generated", "teacher_reviewed"];
const STATUS_DOT_CLASS: Record<KnowledgeStatus, string> = {
  teacher_approved: "kg-legend-dot-approved",
  needs_review: "kg-legend-dot-review",
  ai_generated: "kg-legend-dot-ai",
  teacher_reviewed: "kg-legend-dot-reviewed",
};

export default function GraphLegend() {
  return (
    <div className="kg-legend">
      <span className="field-label">Legend</span>
      <div className="kg-legend-list">
        {STATUS_ORDER.map((s) => (
          <div className="kg-legend-row" key={s}>
            <span className={`kg-legend-dot ${STATUS_DOT_CLASS[s]}`} />
            {STATUS_LABELS[s]}
          </div>
        ))}
      </div>
      <div className="kg-legend-list">
        <div className="kg-legend-row">
          <FlagBadge role="start" />
          Nothing comes before it
        </div>
        <div className="kg-legend-row">
          <FlagBadge role="end" />
          Nothing builds on it
        </div>
      </div>
      <p className="hint-inline">Dashed amber edges are AI-inferred and awaiting approval.</p>
    </div>
  );
}
