import { useState, type FormEvent } from "react";
import { IconClose } from "../../../components/icons.tsx";
import { RELATIONSHIP_LABELS } from "../../types/knowledgeGraph.ts";
import type { KnowledgeNode, KnowledgeRelationship, KnowledgeRelationshipType } from "../../types/knowledgeGraph.ts";

const ALL_RELATIONSHIP_TYPES = Object.keys(RELATIONSHIP_LABELS) as KnowledgeRelationshipType[];

interface RelationshipFormProps {
  mode: "create" | "edit";
  sourceNode: KnowledgeNode;
  targetNode: KnowledgeNode;
  initial?: KnowledgeRelationship;
  onClose: () => void;
  onSave: (data: Omit<KnowledgeRelationship, "id"> | Partial<KnowledgeRelationship>) => Promise<void>;
}

export default function RelationshipForm({ mode, sourceNode, targetNode, initial, onClose, onSave }: RelationshipFormProps) {
  const [type, setType] = useState<KnowledgeRelationshipType>(initial?.type ?? "prerequisite_of");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "create") {
        await onSave({
          sourceId: sourceNode.id,
          targetId: targetNode.id,
          type,
          description: description.trim() || undefined,
          evidenceType: "teacher_created",
          teacherApproved: true,
        });
      } else {
        await onSave({ id: initial?.id, type, description: description.trim() || undefined });
      }
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span>{mode === "create" ? "Create Relationship" : "Edit Relationship"}</span>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            <IconClose />
          </button>
        </div>

        <div className="kg-relationship-preview">
          <span className="kg-relationship-node">{sourceNode.name}</span>
          <span className="kg-relationship-arrow">↓</span>
          <span className="kg-relationship-node">{targetNode.name}</span>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="kg-rel-type">Relationship</label>
          <select
            id="kg-rel-type"
            className="auth-input"
            value={type}
            onChange={(e) => setType(e.target.value as KnowledgeRelationshipType)}
            autoFocus
          >
            {ALL_RELATIONSHIP_TYPES.map((t) => <option key={t} value={t}>{RELATIONSHIP_LABELS[t]}</option>)}
          </select>

          <label className="field-label" htmlFor="kg-rel-description">Description</label>
          <textarea id="kg-rel-description" className="auth-input modal-textarea" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />

          {mode === "create" && (
            <>
              <span className="field-label">Evidence</span>
              <p className="hint">Teacher created</p>
            </>
          )}

          {error && <div className="error-banner auth-error">{error}</div>}

          <button type="submit" className="btn btn-primary auth-submit" disabled={submitting}>
            {submitting ? "Saving…" : mode === "create" ? "Create" : "Save changes"}
          </button>
        </form>
      </div>
    </div>
  );
}
