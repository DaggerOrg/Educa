import { useEffect, useState, type FormEvent } from "react";
import { IconClose } from "../../../components/icons.tsx";

interface TextPromptDialogProps {
  title: string;
  label: string;
  initialValue?: string;
  submitLabel: string;
  onCancel: () => void;
  // Rejecting keeps the dialog open and shows the message, so a failed save is never silent.
  onSubmit: (value: string) => Promise<void> | void;
}

// An in-app replacement for window.prompt(), which embedded browsers (VS Code's
// Simple Browser, Electron webviews) dismiss immediately, so the action seemed to do nothing.
export default function TextPromptDialog({
  title, label, initialValue = "", submitLabel, onCancel, onSubmit,
}: TextPromptDialogProps) {
  const [value, setValue] = useState(initialValue);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onCancel]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(trimmed);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <form className="modal-card" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <div className="modal-head">
          <span>{title}</span>
          <button type="button" className="modal-close" onClick={onCancel} aria-label="Close">
            <IconClose />
          </button>
        </div>
        <label className="field-label" htmlFor="kg-prompt-input">{label}</label>
        <input
          id="kg-prompt-input"
          className="auth-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onFocus={(e) => e.currentTarget.select()}
          autoFocus
          required
        />
        {error && <div className="error-banner">{error}</div>}
        <div className="kg-dialog-actions">
          <button type="button" className="btn" onClick={onCancel}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={submitting || !value.trim()}>
            {submitting ? "Saving…" : submitLabel}
          </button>
        </div>
      </form>
    </div>
  );
}
