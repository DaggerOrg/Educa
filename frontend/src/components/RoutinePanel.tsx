import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, deleteMaterial, listMaterials, uploadMaterial } from "../api.ts";
import type { Material } from "../types.ts";
import { IconClose } from "./icons.tsx";

export default function RoutinePanel() {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [mode, setMode] = useState<"upload" | "paste">("upload");
  const [pasteText, setPasteText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      setMaterials(await listMaterials());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleFileChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await uploadMaterial(file);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function handlePasteSubmit() {
    const text = pasteText.trim();
    if (!text) return;
    setBusy(true);
    setError(null);
    try {
      const file = new File([text], `pasted-${Date.now()}.txt`, { type: "text/plain" });
      await uploadMaterial(file);
      setPasteText("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't add that");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: string) {
    await deleteMaterial(id);
    refresh();
  }

  return (
    <div className="routine-panel">
      <p className="hint">
        Upload a file, or paste notes, a textbook excerpt, or something you generated with
        ChatGPT or another AI tool. The AI grounds syllabi and lessons in these instead of
        inventing examples.
      </p>

      <div className="routine-tabs">
        <button
          type="button"
          className={`routine-tab${mode === "upload" ? " is-active" : ""}`}
          onClick={() => setMode("upload")}
        >
          Upload
        </button>
        <button
          type="button"
          className={`routine-tab${mode === "paste" ? " is-active" : ""}`}
          onClick={() => setMode("paste")}
        >
          Paste
        </button>
      </div>

      {mode === "upload" ? (
        <div className="upload-control">
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.txt,.md"
            onChange={handleFileChosen}
            disabled={busy}
            hidden
            id="material-upload-input"
          />
          <label htmlFor="material-upload-input" className={`btn btn-primary${busy ? "" : " is-clickable"}`}>
            {busy ? "Uploading…" : "Upload material"}
          </label>
          <span className="upload-hint">.pdf, .txt, or .md — up to 20MB</span>
        </div>
      ) : (
        <div className="paste-control">
          <textarea
            className="auth-input modal-textarea"
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            placeholder="Paste notes, a textbook excerpt, or something generated with ChatGPT or another AI tool…"
            rows={6}
            disabled={busy}
          />
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy || !pasteText.trim()}
            onClick={handlePasteSubmit}
          >
            {busy ? "Adding…" : "Add material"}
          </button>
        </div>
      )}

      {error && <div className="error-banner">{error}</div>}

      {materials.length === 0 ? (
        <p className="hint">No materials yet.</p>
      ) : (
        <div className="materials-list">
          {materials.map((m) => (
            <div className="material-row" key={m.id}>
              <div className="material-row-main">
                <span className="material-filename">{m.filename}</span>
                <span className="material-meta">
                  {m.chunkCount} chunk{m.chunkCount === 1 ? "" : "s"} · {m.charCount.toLocaleString()} chars
                </span>
              </div>
              <button
                type="button"
                className="material-delete"
                onClick={() => handleDelete(m.id)}
                aria-label={`Delete ${m.filename}`}
              >
                <IconClose />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
