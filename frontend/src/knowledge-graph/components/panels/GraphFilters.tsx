import { ALL_CEFR, ALL_NODE_TYPES, ALL_SKILLS, ALL_STATUSES } from "../../hooks/useGraphFilters.ts";
import { NODE_TYPE_LABELS, STATUS_LABELS, type CefrLevel, type KnowledgeNodeType, type KnowledgeStatus } from "../../types/knowledgeGraph.ts";

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

function Chip({ label, on, onToggle }: { label: string; on: boolean; onToggle: () => void }) {
  return (
    <button type="button" className={`kg-chip${on ? " is-on" : ""}`} aria-pressed={on} onClick={onToggle}>
      {label}
    </button>
  );
}

// Toggle chips instead of one checkbox per value: same filters, a fraction of
// the height, and the on/off state reads at a glance.
export default function GraphFilters({
  nodeTypes, cefr, skills, statuses, onToggleNodeType, onToggleCefr, onToggleSkill, onToggleStatus,
}: GraphFiltersProps) {
  return (
    <div className="kg-filters">
      <div className="kg-filter-group">
        <span className="field-label">Type</span>
        <div className="kg-chips">
          {ALL_NODE_TYPES.map((t) => (
            <Chip key={t} label={NODE_TYPE_LABELS[t]} on={nodeTypes.has(t)} onToggle={() => onToggleNodeType(t)} />
          ))}
        </div>
      </div>

      <div className="kg-filter-group">
        <span className="field-label">Review status</span>
        <div className="kg-chips">
          {ALL_STATUSES.map((s) => (
            <Chip key={s} label={STATUS_LABELS[s]} on={statuses.has(s)} onToggle={() => onToggleStatus(s)} />
          ))}
        </div>
      </div>

      <div className="kg-filter-group">
        <span className="field-label">CEFR level</span>
        <div className="kg-chips">
          {ALL_CEFR.map((l) => (
            <Chip key={l} label={l} on={cefr.has(l)} onToggle={() => onToggleCefr(l)} />
          ))}
        </div>
      </div>

      <div className="kg-filter-group">
        <span className="field-label">Skill</span>
        <div className="kg-chips">
          {ALL_SKILLS.map((s) => (
            <Chip key={s} label={s} on={skills.has(s)} onToggle={() => onToggleSkill(s)} />
          ))}
        </div>
      </div>
    </div>
  );
}
