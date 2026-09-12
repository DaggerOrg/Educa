import { useState, type FormEvent } from "react";
import { IconClose } from "../../components/icons.tsx";
import { ALL_CEFR, ALL_STATUSES } from "../hooks/useGraphFilters.ts";
import { NODE_TYPE_LABELS, STATUS_LABELS } from "../types/knowledgeGraph.ts";
import type { CefrLevel, KnowledgeNode, KnowledgeNodeType, KnowledgeStatus } from "../types/knowledgeGraph.ts";

const ADDABLE_TYPES: KnowledgeNodeType[] = ["concept", "exercise", "learning_objective", "resource"];

interface NodeFormProps {
  mode: "add" | "edit";
  initial?: KnowledgeNode;
  initialType?: KnowledgeNodeType;
  onClose: () => void;
  onSave: (data: Omit<KnowledgeNode, "id"> | Partial<KnowledgeNode>) => Promise<void>;
}

export default function NodeForm({ mode, initial, initialType, onClose, onSave }: NodeFormProps) {
  const [type, setType] = useState<KnowledgeNodeType>(initial?.type ?? initialType ?? "concept");
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [category, setCategory] = useState(initial?.category ?? "");
  const [cefrLevel, setCefrLevel] = useState<CefrLevel | "">(initial?.cefrLevel ?? "");
  const [status, setStatus] = useState<KnowledgeStatus>(initial?.status ?? "teacher_approved");
  const [aliases, setAliases] = useState(initial?.aliases?.join(", ") ?? "");
  const [tags, setTags] = useState(initial?.tags?.join(", ") ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const splitList = (v: string) => v.split(",").map((s) => s.trim()).filter(Boolean);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Name is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        type,
        name: name.trim(),
        description: description.trim() || undefined,
        category: category.trim() || undefined,
        cefrLevel: cefrLevel || undefined,
        status,
        aliases: splitList(aliases),
        tags: splitList(tags),
      };
      await onSave(mode === "add" ? payload : { ...payload, id: initial?.id });
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
          <span>{mode === "add" ? `Add ${NODE_TYPE_LABELS[type]}` : `Edit ${NODE_TYPE_LABELS[type]}`}</span>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            <IconClose />
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="kg-node-name">Name</label>
          <input id="kg-node-name" className="auth-input" value={name} onChange={(e) => setName(e.target.value)} required autoFocus />

          <label className="field-label" htmlFor="kg-node-type">Type</label>
          <select
            id="kg-node-type"
            className="auth-input"
            value={type}
            onChange={(e) => setType(e.target.value as KnowledgeNodeType)}
          >
            {(mode === "add" ? ADDABLE_TYPES : [type]).map((t) => (
              <option key={t} value={t}>{NODE_TYPE_LABELS[t]}</option>
            ))}
          </select>

          <label className="field-label" htmlFor="kg-node-category">Category</label>
          <input id="kg-node-category" className="auth-input" value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g. grammar, vocabulary, activity" />

          <label className="field-label" htmlFor="kg-node-cefr">CEFR Level</label>
          <select id="kg-node-cefr" className="auth-input" value={cefrLevel} onChange={(e) => setCefrLevel(e.target.value as CefrLevel | "")}>
            <option value="">—</option>
            {ALL_CEFR.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>

          <label className="field-label" htmlFor="kg-node-description">Description</label>
          <textarea id="kg-node-description" className="auth-input modal-textarea" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />

          <label className="field-label" htmlFor="kg-node-tags">Tags</label>
          <input id="kg-node-tags" className="auth-input" value={tags} onChange={(e) => setTags(e.target.value)} placeholder="comma-separated" />

          {mode === "edit" && (
            <>
              <label className="field-label" htmlFor="kg-node-aliases">Aliases</label>
              <input id="kg-node-aliases" className="auth-input" value={aliases} onChange={(e) => setAliases(e.target.value)} placeholder="comma-separated" />

              <label className="field-label" htmlFor="kg-node-status">Status</label>
              <select id="kg-node-status" className="auth-input" value={status} onChange={(e) => setStatus(e.target.value as KnowledgeStatus)}>
                {ALL_STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
              </select>
            </>
          )}

          {error && <div className="error-banner auth-error">{error}</div>}

          <button type="submit" className="btn btn-primary auth-submit" disabled={submitting}>
            {submitting ? "Saving…" : mode === "add" ? "Add" : "Save changes"}
          </button>
        </form>
      </div>
    </div>
  );
}
