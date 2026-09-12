import { IconClose } from "../../components/icons.tsx";
import type { KnowledgeSource } from "../types/knowledgeGraph.ts";

const DOCUMENT_TYPE_LABELS: Record<KnowledgeSource["documentType"], string> = {
  textbook: "Textbook",
  teacher_guide: "Teacher Guide",
  worksheet: "Worksheet",
  exam: "Exam",
  lecture_note: "Lecture Note",
};

const EVIDENCE_TYPE_LABELS: Record<KnowledgeSource["evidenceType"], string> = {
  explicit: "Source Explicit",
  llm_inferred: "LLM Inferred",
  teacher_added: "Teacher Added",
};

interface SourceEvidenceProps {
  source: KnowledgeSource;
  onClose: () => void;
}

export default function SourceEvidence({ source, onClose }: SourceEvidenceProps) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span>Source</span>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            <IconClose />
          </button>
        </div>

        <p className="kg-source-doc">{source.documentName}</p>
        <p className="hint-inline">
          {DOCUMENT_TYPE_LABELS[source.documentType]}
          {source.unit && ` • ${source.unit}`}
          {source.chapter && ` • ${source.chapter}`}
          {source.page !== undefined && ` • Page ${source.page}`}
        </p>

        {source.excerpt && (
          <div className="kg-source-excerpt">
            <span className="field-label">Extracted evidence</span>
            <p>&ldquo;{source.excerpt}&rdquo;</p>
          </div>
        )}

        <span className={`status-pill kg-evidence-${source.evidenceType.replace("_", "-")}`}>
          {EVIDENCE_TYPE_LABELS[source.evidenceType]}
        </span>

        <p className="hint-inline kg-source-footer">A PDF viewer isn't built yet — this will open the actual page later.</p>
      </div>
    </div>
  );
}
