import { ALL_CEFR, ALL_NODE_TYPES, ALL_SKILLS, ALL_STATUSES } from "../hooks/useGraphFilters.ts";
import { NODE_TYPE_LABELS, STATUS_LABELS, type CefrLevel, type KnowledgeNodeType, type KnowledgeStatus } from "../types/knowledgeGraph.ts";

interface GraphFiltersProps {
  nodeTypes: Set<KnowledgeNodeType>;
  cefr: Set<CefrLevel>;
  skills: Set<string>;
  statuses: Set<KnowledgeStatus>;
  onToggleNodeType: (t: KnowledgeNodeType) => void;
  onToggleCefr: (l: CefrLevel) => void;
  onToggleSkill: (s: string) => void;
  onToggleStatus: (s: KnowledgeStatus) => void;
}

export default function GraphFilters({
  nodeTypes, cefr, skills, statuses, onToggleNodeType, onToggleCefr, onToggleSkill, onToggleStatus,
}: GraphFiltersProps) {
  return (
    <div className="kg-filters">
      <div className="kg-filter-group">
        <span className="field-label">Node types</span>
        {ALL_NODE_TYPES.map((t) => (
          <label className="check-row" key={t}>
            <input type="checkbox" checked={nodeTypes.has(t)} onChange={() => onToggleNodeType(t)} />
            {NODE_TYPE_LABELS[t]}
          </label>
        ))}
      </div>

      <div className="kg-filter-group">
        <span className="field-label">CEFR</span>
        {ALL_CEFR.map((l) => (
          <label className="check-row" key={l}>
            <input type="checkbox" checked={cefr.has(l)} onChange={() => onToggleCefr(l)} />
            {l}
          </label>
        ))}
      </div>

      <div className="kg-filter-group">
        <span className="field-label">Skill</span>
        {ALL_SKILLS.map((s) => (
          <label className="check-row" key={s}>
            <input type="checkbox" checked={skills.has(s)} onChange={() => onToggleSkill(s)} />
            {s}
          </label>
        ))}
      </div>

      <div className="kg-filter-group">
        <span className="field-label">Review status</span>
        {ALL_STATUSES.map((s) => (
          <label className="check-row" key={s}>
            <input type="checkbox" checked={statuses.has(s)} onChange={() => onToggleStatus(s)} />
            {STATUS_LABELS[s]}
          </label>
        ))}
      </div>
    </div>
  );
}
