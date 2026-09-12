import { useState } from "react";
import { IconCheck, IconEdit } from "../../components/icons.tsx";
import { RELATIONSHIP_LABELS } from "../types/knowledgeGraph.ts";
import type { KnowledgeNode, KnowledgeRelationship, KnowledgeSource } from "../types/knowledgeGraph.ts";
import SourceEvidence from "./SourceEvidence.tsx";

const EVIDENCE_LABELS: Record<KnowledgeRelationship["evidenceType"], string> = {
  source_explicit: "Source Explicit",
  llm_inferred: "LLM Inferred",
  teacher_created: "Teacher Created",
};

interface EdgeInspectorProps {
  relationship: KnowledgeRelationship;
  allNodes: KnowledgeNode[];
  onSelectNode: (nodeId: string) => void;
  onEdit: () => void;
  onDelete: () => void;
  onApprove: () => void;
}

export default function EdgeInspector({ relationship, allNodes, onSelectNode, onEdit, onDelete, onApprove }: EdgeInspectorProps) {
  const [evidence, setEvidence] = useState<KnowledgeSource | null>(null);
  const source = allNodes.find((n) => n.id === relationship.sourceId);
  const target = allNodes.find((n) => n.id === relationship.targetId);
  const needsApproval = relationship.evidenceType === "llm_inferred" && !relationship.teacherApproved;

  return (
    <div className="kg-inspector">
      <div className="kg-inspector-head">
        <span className="kg-node-type">Relationship</span>
        <h3 className="kg-inspector-title">{RELATIONSHIP_LABELS[relationship.type]}</h3>
      </div>

      <dl className="kg-fact-list">
        <dt>From</dt>
        <dd>
          {source ? (
            <button type="button" className="kg-related-item" onClick={() => onSelectNode(source.id)}>{source.name}</button>
          ) : "—"}
        </dd>
        <dt>To</dt>
        <dd>
          {target ? (
            <button type="button" className="kg-related-item" onClick={() => onSelectNode(target.id)}>{target.name}</button>
          ) : "—"}
        </dd>
        <dt>Evidence</dt>
        <dd>{EVIDENCE_LABELS[relationship.evidenceType]}</dd>
        {relationship.confidence !== undefined && (
          <>
            <dt>Confidence</dt>
            <dd>{Math.round(relationship.confidence * 100)}%</dd>
          </>
        )}
        <dt>Approved</dt>
        <dd>{relationship.teacherApproved ? "Yes" : "No"}</dd>
      </dl>

      {relationship.description && (
        <section className="kg-inspector-section">
          <p className="kg-inspector-description">{relationship.description}</p>
        </section>
      )}

      {relationship.sources && relationship.sources.length > 0 && (
        <details className="kg-inspector-section" open>
          <summary className="field-label">Sources</summary>
          <div className="kg-source-list">
            {relationship.sources.map((s) => (
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

      {needsApproval && (
        <div className="error-banner kg-approval-banner">
          This relationship was inferred by AI and hasn't been reviewed yet.
        </div>
      )}

      <div className="kg-inspector-actions">
        {needsApproval && (
          <button type="button" className="btn btn-primary" onClick={onApprove}>
            <IconCheck /> Approve Relationship
          </button>
        )}
        <button type="button" className="btn" onClick={onEdit}><IconEdit /> Edit Relationship</button>
        <button type="button" className="btn" onClick={onDelete}>Delete Relationship</button>
      </div>

      {evidence && <SourceEvidence source={evidence} onClose={() => setEvidence(null)} />}
    </div>
  );
}
