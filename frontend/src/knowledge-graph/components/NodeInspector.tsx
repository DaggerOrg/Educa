import { useMemo, useState } from "react";
import { IconEdit } from "../../components/icons.tsx";
import { NODE_TYPE_LABELS, STATUS_LABELS } from "../types/knowledgeGraph.ts";
import type { KnowledgeNode, KnowledgeRelationship, KnowledgeSource } from "../types/knowledgeGraph.ts";
import SourceEvidence from "./SourceEvidence.tsx";

interface NodeInspectorProps {
  node: KnowledgeNode;
  allNodes: KnowledgeNode[];
  relationships: KnowledgeRelationship[];
  onSelectNode: (nodeId: string) => void;
  onEdit: () => void;
  onDelete: () => void;
}

interface RelatedNode {
  node: KnowledgeNode;
  via: string;
}

export default function NodeInspector({ node, allNodes, relationships, onSelectNode, onEdit, onDelete }: NodeInspectorProps) {
  const [evidence, setEvidence] = useState<KnowledgeSource | null>(null);
  const byId = useMemo(() => new Map(allNodes.map((n) => [n.id, n])), [allNodes]);

  const prerequisites: RelatedNode[] = useMemo(
    () =>
      relationships
        .filter((r) => r.type === "prerequisite_of" && r.targetId === node.id)
        .map((r) => byId.get(r.sourceId))
        .filter((n): n is KnowledgeNode => !!n)
        .map((n) => ({ node: n, via: "PREREQUISITE_OF" })),
    [relationships, node.id, byId],
  );

  const usedByNext: RelatedNode[] = useMemo(() => {
    const items: RelatedNode[] = [];
    const seen = new Set<string>();
    const add = (n: KnowledgeNode | undefined, via: string) => {
      if (n && !seen.has(n.id)) {
        seen.add(n.id);
        items.push({ node: n, via });
      }
    };
    for (const r of relationships) {
      if (r.sourceId === node.id && r.type === "prerequisite_of") add(byId.get(r.targetId), "unlocks");
      if (r.targetId === node.id && r.type === "uses") add(byId.get(r.sourceId), "uses this");
      if (r.targetId === node.id && r.type === "assesses") add(byId.get(r.sourceId), "assesses this");
      if (r.sourceId === node.id && r.type === "reinforces") add(byId.get(r.targetId), "reinforced by");
      if (r.targetId === node.id && r.type === "reinforces") add(byId.get(r.sourceId), "reinforces this");
    }
    return items;
  }, [relationships, node.id, byId]);

  const skills: KnowledgeNode[] = useMemo(
    () =>
      relationships
        .filter((r) => r.sourceId === node.id && r.type === "practices")
        .map((r) => byId.get(r.targetId))
        .filter((n): n is KnowledgeNode => !!n && n.type === "skill"),
    [relationships, node.id, byId],
  );

  return (
    <div className="kg-inspector">
      <div className="kg-inspector-head">
        <span className="kg-node-type">{NODE_TYPE_LABELS[node.type]}</span>
        <h3 className="kg-inspector-title">{node.name}</h3>
      </div>

      <dl className="kg-fact-list">
        {node.cefrLevel && (
          <>
            <dt>CEFR</dt>
            <dd>{node.cefrLevel}</dd>
          </>
        )}
        <dt>Status</dt>
        <dd>
          <span className={`status-pill kg-status-pill-${node.status.replace(/_/g, "-")}`}>{STATUS_LABELS[node.status]}</span>
        </dd>
        {node.confidence !== undefined && (
          <>
            <dt>Confidence</dt>
            <dd>{Math.round(node.confidence * 100)}%</dd>
          </>
        )}
      </dl>

      {node.description && (
        <section className="kg-inspector-section">
          <p className="kg-inspector-description">{node.description}</p>
        </section>
      )}

      {prerequisites.length > 0 && (
        <details className="kg-inspector-section" open>
          <summary className="field-label">Prerequisites</summary>
          <div className="kg-related-list">
            {prerequisites.map(({ node: n }) => (
              <button type="button" key={n.id} className="kg-related-item" onClick={() => onSelectNode(n.id)}>
                {n.name}
              </button>
            ))}
          </div>
        </details>
      )}

      {usedByNext.length > 0 && (
        <details className="kg-inspector-section" open>
          <summary className="field-label">Used by / next concepts</summary>
          <div className="kg-related-list">
            {usedByNext.map(({ node: n }) => (
              <button type="button" key={n.id} className="kg-related-item" onClick={() => onSelectNode(n.id)}>
                {n.name}
              </button>
            ))}
          </div>
        </details>
      )}

      {skills.length > 0 && (
        <details className="kg-inspector-section" open>
          <summary className="field-label">Skills</summary>
          <div className="kg-related-list">
            {skills.map((s) => (
              <button type="button" key={s.id} className="kg-related-item" onClick={() => onSelectNode(s.id)}>
                {s.name}
              </button>
            ))}
          </div>
        </details>
      )}

      {node.sources && node.sources.length > 0 && (
        <details className="kg-inspector-section" open>
          <summary className="field-label">Source materials</summary>
          <div className="kg-source-list">
            {node.sources.map((s) => (
              <button type="button" key={s.id} className="kg-source-item" onClick={() => setEvidence(s)}>
                <span className="kg-source-item-doc">{s.documentName}</span>
                <span className="kg-source-item-meta">
                  {s.unit}
                  {s.page !== undefined && ` • Page ${s.page}`}
                </span>
              </button>
            ))}
          </div>
        </details>
      )}

      {node.aliases && node.aliases.length > 0 && (
        <details className="kg-inspector-section">
          <summary className="field-label">Aliases</summary>
          <p className="hint">{node.aliases.join(", ")}</p>
        </details>
      )}

      <div className="kg-inspector-actions">
        <button type="button" className="btn btn-primary" onClick={onEdit}>
          <IconEdit /> Edit {NODE_TYPE_LABELS[node.type]}
        </button>
        <button type="button" className="btn" onClick={onDelete}>Delete</button>
      </div>

      {evidence && <SourceEvidence source={evidence} onClose={() => setEvidence(null)} />}
    </div>
  );
}
