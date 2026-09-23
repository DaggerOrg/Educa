import { useState } from "react";
import { IconClose } from "../../../components/icons.tsx";

interface DeleteConfirmationDialogProps {
  title: string;
  description: string;
  onCancel: () => void;
  onConfirm: () => Promise<void>;
}

export default function DeleteConfirmationDialog({ title, description, onCancel, onConfirm }: DeleteConfirmationDialogProps) {
  const [deleting, setDeleting] = useState(false);

  async function handleConfirm() {
    setDeleting(true);
    try {
      await onConfirm();
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span>{title}</span>
          <button type="button" className="modal-close" onClick={onCancel} aria-label="Close">
            <IconClose />
          </button>
        </div>
        <p className="hint">{description}</p>
        <div className="kg-dialog-actions">
          <button type="button" className="btn" onClick={onCancel}>Cancel</button>
          <button type="button" className="btn kg-btn-danger" onClick={handleConfirm} disabled={deleting}>
            {deleting ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}
