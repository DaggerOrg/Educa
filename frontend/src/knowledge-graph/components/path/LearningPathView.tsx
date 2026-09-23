import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { IconArrowDown, IconArrowUp } from "../../../components/icons.tsx";
import { usePathDirection, type PathDirection } from "../../hooks/useGraphView.ts";
import { NODE_TYPE_LABELS, STATUS_LABELS, type KnowledgeNode, type KnowledgeRelationship } from "../../types/knowledgeGraph.ts";
import { buildLearningPath, type PathItem, type PathSection } from "../../utils/learningPath.ts";
import FlagBadge from "../canvas/FlagBadge.tsx";
import { STATUS_CLASS, TYPE_ICONS } from "../canvas/KnowledgeNode.tsx";

interface LearningPathViewProps {
  nodes: KnowledgeNode[];
  relationships: KnowledgeRelationship[];
  selectedId: string | null;
  onSelectNode: (nodeId: string) => void;
}

const DIRECTIONS: { value: PathDirection; label: string; hint: string; Icon: typeof IconArrowDown }[] = [
  { value: "down", label: "Basics at top", hint: "Start at the top and read down to the advanced", Icon: IconArrowDown },
  { value: "up", label: "Basics at bottom", hint: "Start at the bottom and climb up to the advanced", Icon: IconArrowUp },
];

const CHIPS_SHOWN = 4;

// The graph as a plain vertical list, from the basics to the advanced -- for
// reading a curriculum in order rather than exploring its connections.
export default function LearningPathView({ nodes, relationships, selectedId, onSelectNode }: LearningPathViewProps) {
  const path = useMemo(() => buildLearningPath(nodes, relationships), [nodes, relationships]);
  const [direction, setDirection] = usePathDirection();
  const scroller = useRef<HTMLDivElement>(null);

  // Open at the basics: the top when reading down, the bottom when climbing up.
  useLayoutEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTop = direction === "up" ? el.scrollHeight : 0;
  }, [direction]);

  // Picking a topic elsewhere (search, the inspector) brings its card into view.
  useLayoutEffect(() => {
    if (!selectedId) return;
    scroller.current?.querySelector(`[data-node-id="${CSS.escape(selectedId)}"]`)?.scrollIntoView({ block: "nearest" });
  }, [selectedId]);

  const stages = path.sections.filter((s) => s.kind === "stage");
  const topicCount = path.sections.filter((s) => s.kind !== "other").reduce((n, s) => n + s.items.length, 0);
  const sections = direction === "up" ? [...path.sections].reverse() : path.sections;
  const unit = path.grouping === "level" ? "level" : "step";

  return (
    <div className="kg-path" ref={scroller}>
      <div className="kg-path-inner">
        <div className="kg-path-bar">
          <div>
            <h2 className="kg-path-title">Learning path</h2>
            <p className="hint">
              {stages.length} {unit}{stages.length === 1 ? "" : "s"} · {topicCount} topic{topicCount === 1 ? "" : "s"}.{" "}
              {path.grouping === "level"
                ? "Ordered by level, then by what each topic builds on."
                : "No levels are set, so this is ordered by what each topic builds on."}
            </p>
          </div>
          <div className="kg-segmented" role="group" aria-label="Path direction">
            {DIRECTIONS.map(({ value, label, hint, Icon }) => (
              <button
                key={value}
                type="button"
                className={`kg-segmented-btn${direction === value ? " is-active" : ""}`}
                aria-pressed={direction === value}
                title={hint}
                onClick={() => setDirection(value)}
              >
                <Icon /> {label}
              </button>
            ))}
          </div>
        </div>

        {path.sections.length === 0 ? (
          <div className="empty-panel">Nothing to show yet — add a concept, or loosen the filters.</div>
        ) : (
          <ol className="kg-path-list">
            {sections.map((section) => (
              <PathSectionRow
                key={section.key}
                section={section}
                end={
                  section.kind !== "stage" || stages.length < 2 ? null
                    : section === stages[0] ? "basics"
                    : section === stages[stages.length - 1] ? "advanced"
                    : null
                }
                selectedId={selectedId}
                onSelectNode={onSelectNode}
              />
            ))}
          </ol>
        )}

        <p className="hint kg-path-foot">A reading view. Switch to Graph to connect or rearrange topics.</p>
      </div>
    </div>
  );
}

function PathSectionRow({
  section, end, selectedId, onSelectNode,
}: {
  section: PathSection;
  end: "basics" | "advanced" | null;
  selectedId: string | null;
  onSelectNode: (nodeId: string) => void;
}) {
  return (
    <li className={`kg-path-section kg-path-section-${section.kind}`}>
      <div className="kg-path-marker" aria-hidden="true">{section.badge}</div>
      <section className="kg-path-body" aria-label={section.label}>
        <header className="kg-path-section-head">
          <h3>{section.label}</h3>
          <span className="kg-path-caption">{section.caption}</span>
          {end && <span className={`kg-path-tag kg-path-tag-${end}`}>{end === "basics" ? "Basics · start here" : "Most advanced"}</span>}
        </header>
        <ul className="kg-path-cards">
          {section.items.map((item) => (
            <PathCard key={item.node.id} item={item} selected={item.node.id === selectedId} onSelectNode={onSelectNode} />
          ))}
        </ul>
      </section>
    </li>
  );
}

function PathCard({ item, selected, onSelectNode }: { item: PathItem; selected: boolean; onSelectNode: (nodeId: string) => void }) {
  const { node } = item;
  const Icon = TYPE_ICONS[node.type];
  const [showAll, setShowAll] = useState(false);
  const chips = showAll ? item.support : item.support.slice(0, CHIPS_SHOWN);
  const hidden = item.support.length - chips.length;

  return (
    <li className={`kg-path-card${selected ? " is-selected" : ""}`} data-node-id={node.id}>
      {item.role && <FlagBadge role={item.role} />}
      <button type="button" className="kg-path-card-main" aria-pressed={selected} onClick={() => onSelectNode(node.id)}>
        <span className="kg-node-icon"><Icon /></span>
        <span className="kg-path-card-text">
          <span className="kg-path-card-name">{node.name}</span>
          <span className="kg-node-meta">
            {NODE_TYPE_LABELS[node.type]}
            {node.cefrLevel ? ` · ${node.cefrLevel}` : ""}
          </span>
        </span>
        <span
          className={`kg-node-dot ${STATUS_CLASS[node.status]}`}
          role="img"
          aria-label={STATUS_LABELS[node.status]}
          title={STATUS_LABELS[node.status]}
        />
      </button>
      {node.description && <p className="kg-path-desc">{node.description}</p>}
      {item.after.length > 0 && (
        <p className="kg-path-after">
          <span className="kg-path-after-label">After</span> {item.after.map((n) => n.name).join(" · ")}
        </p>
      )}
      {item.support.length > 0 && (
        <ul className="kg-path-chips" aria-label={`Practice and resources for ${node.name}`}>
          {chips.map((s) => {
            const SupportIcon = TYPE_ICONS[s.type];
            return (
              <li key={s.id}>
                <button type="button" className="kg-path-chip" title={`${NODE_TYPE_LABELS[s.type]}: ${s.name}`} onClick={() => onSelectNode(s.id)}>
                  <SupportIcon /> <span className="kg-path-chip-text">{s.name}</span>
                </button>
              </li>
            );
          })}
          {(hidden > 0 || showAll) && item.support.length > CHIPS_SHOWN && (
            <li>
              <button type="button" className="kg-path-chip kg-path-chip-more" onClick={() => setShowAll(!showAll)}>
                {showAll ? "Show less" : `+${hidden} more`}
              </button>
            </li>
          )}
        </ul>
      )}
    </li>
  );
}
