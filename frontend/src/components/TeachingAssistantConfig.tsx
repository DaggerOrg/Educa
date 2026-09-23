import { useEffect, useState } from "react";
import { ApiError, fetchCourseTa, upsertTeachingAssistant } from "../api.ts";
import type { TeachingAssistant } from "../types.ts";

interface TeachingAssistantConfigProps {
  courseId: string;
}

export default function TeachingAssistantConfig({ courseId }: TeachingAssistantConfigProps) {
  const [ta, setTa] = useState<TeachingAssistant | null>(null);
  const [name, setName] = useState("");
  const [instructions, setInstructions] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setTa(null);
    fetchCourseTa(courseId)
      .then((found) => {
        setTa(found);
        setName(found.name);
        setInstructions(found.instructions);
      })
      .catch(() => {
        setName("");
        setInstructions("Be a friendly, patient Teaching Assistant. Give hints and explanations, never final quiz answers. Encourage the student and point them back to the lesson content.");
      });
  }, [courseId]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !instructions.trim()) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const result = await upsertTeachingAssistant(courseId, name.trim(), instructions.trim());
      setTa(result);
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="exercises-builder-main">
      <div className="exercises-builder-head">
        <div>
          <h2>AI Teaching Assistant</h2>
          <p className="hint">
            Set up an AI persona students can chat with for this course — questions, hints,
            concept explanations, modeled on a university TA. Real and working: it's grounded in
            this course's published lessons and never shares quiz answers.
          </p>
        </div>
      </div>

      <form className="auth-form" onSubmit={handleSave}>
        <label className="field-label" htmlFor="ta-name">Name</label>
        <input
          id="ta-name"
          className="auth-input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. TA Sam"
          required
        />
        <label className="field-label" htmlFor="ta-instructions">Instructions / personality</label>
        <textarea
          id="ta-instructions"
          className="auth-input modal-textarea"
          rows={6}
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
          required
        />
        {error && <div className="error-banner">{error}</div>}
        <button type="submit" className="btn btn-primary" disabled={saving || !name.trim() || !instructions.trim()}>
          {saving ? "Saving…" : ta ? "Update Teaching Assistant" : "Create Teaching Assistant"}
        </button>
        {saved && <span className="hint-inline">Saved — students enrolled in this course can now ask {name}.</span>}
      </form>
    </div>
  );
}
