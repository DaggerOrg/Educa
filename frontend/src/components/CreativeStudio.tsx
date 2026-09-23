import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  creativeAssetFileUrl,
  deleteCreativeAsset,
  fetchMyPersona,
  listCreativeAssets,
  upsertPersona,
  uploadCreativeAsset,
} from "../api.ts";
import { getToken } from "../auth.ts";
import type { CreativeAsset, TeacherPersona } from "../types.ts";
import { IconClose, IconSparkle } from "./icons.tsx";

const STYLE_OPTIONS = ["Photorealistic", "Illustration", "Cinematic", "3D Render"];

interface MockPreview {
  id: string;
  kind: "image" | "video";
  prompt: string;
  style: string;
}

// The file route requires the same Authorization header as every other
// API call -- a plain <img src="..."> can't send custom headers, so real
// uploaded assets are fetched as authenticated blobs instead of linked
// directly. Mock (generated) previews never call the backend at all.
function AssetThumbnail({ asset }: { asset: CreativeAsset }) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  useEffect(() => {
    let revoked = "";
    const token = getToken();
    fetch(creativeAssetFileUrl(asset.id), { headers: token ? { Authorization: `Bearer ${token}` } : undefined })
      .then((res) => (res.ok ? res.blob() : Promise.reject(res)))
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        revoked = url;
        setBlobUrl(url);
      })
      .catch(() => setBlobUrl(null));
    return () => {
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [asset.id]);

  if (!blobUrl) return <div className="creative-thumb creative-thumb-loading" />;
  return asset.kind === "video" ? (
    <video className="creative-thumb" src={blobUrl} controls />
  ) : (
    <img className="creative-thumb" src={blobUrl} alt={asset.filename} />
  );
}

function PersonaEnrollment({ assets }: { assets: CreativeAsset[] }) {
  const [persona, setPersona] = useState<TeacherPersona | null>(null);
  const [name, setName] = useState("");
  const [trainingAssetId, setTrainingAssetId] = useState("");
  const [consented, setConsented] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const videos = assets.filter((a) => a.kind === "video");

  useEffect(() => {
    fetchMyPersona()
      .then((p) => {
        setPersona(p);
        setName(p.name);
        setTrainingAssetId(p.trainingAssetId);
      })
      .catch(() => setPersona(null));
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !trainingAssetId || !consented) return;
    setSaving(true);
    setError(null);
    try {
      const saved = await upsertPersona(name.trim(), trainingAssetId, consented);
      setPersona(saved);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save your persona");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="home-prompt-section">
      <h2>Teacher Persona</h2>
      <p className="hint">
        Enroll a short video of yourself talking — it doubles as both your likeness and voice
        sample. No avatar-rendering provider is connected yet, so students see a clearly-labeled
        preview, not a real generated video.
      </p>
      {videos.length === 0 ? (
        <p className="hint-inline">
          Upload a short talking-head video from the "Studio" tab first, then come back here to
          enroll it.
        </p>
      ) : (
        <form className="auth-form persona-form" onSubmit={handleSave}>
          <label className="field-label" htmlFor="persona-name">Persona name</label>
          <input
            id="persona-name"
            className="auth-input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Prof. Ada"
            required
          />
          <label className="field-label" htmlFor="persona-video">Training video</label>
          <select
            id="persona-video"
            className="auth-input"
            value={trainingAssetId}
            onChange={(e) => setTrainingAssetId(e.target.value)}
            required
          >
            <option value="" disabled>Choose a video…</option>
            {videos.map((v) => (
              <option key={v.id} value={v.id}>{v.filename}</option>
            ))}
          </select>
          <label className="check-row persona-consent">
            <input type="checkbox" checked={consented} onChange={(e) => setConsented(e.target.checked)} />
            I consent to this video being used to create an AI persona of myself for my students.
          </label>
          {error && <div className="error-banner">{error}</div>}
          <button type="submit" className="btn btn-primary" disabled={saving || !consented}>
            {saving ? "Saving…" : persona ? "Update persona" : "Create persona"}
          </button>
          {persona && <span className="hint-inline">Enrolled since {new Date(persona.consentedAt).toLocaleDateString()}.</span>}
        </form>
      )}
    </div>
  );
}

export default function CreativeStudio() {
  const [studioTab, setStudioTab] = useState<"studio" | "persona">("studio");
  const [assets, setAssets] = useState<CreativeAsset[]>([]);
  const [previews, setPreviews] = useState<MockPreview[]>([]);
  const [prompt, setPrompt] = useState("");
  const [kind, setKind] = useState<"image" | "video">("image");
  const [style, setStyle] = useState(STYLE_OPTIONS[0]);
  const [generating, setGenerating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      setAssets(await listCreativeAssets());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function handleGenerate() {
    const text = prompt.trim();
    if (!text || generating) return;
    setGenerating(true);
    // No generation provider is connected (see backend/app/creative.py) --
    // this is a deliberate, clearly-labeled UI mockup: a short simulated
    // delay, then a client-only preview card that's never sent to the
    // backend and won't survive a refresh.
    setTimeout(() => {
      setPreviews((prev) => [{ id: crypto.randomUUID(), kind, prompt: text, style }, ...prev]);
      setPrompt("");
      setGenerating(false);
    }, 900);
  }

  async function handleFileChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await uploadCreativeAsset(file);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id: string) {
    await deleteCreativeAsset(id);
    refresh();
  }

  return (
    <div className="creative-studio">
      <div className="routine-tabs creative-studio-tabs">
        <button
          type="button"
          className={`routine-tab${studioTab === "studio" ? " is-active" : ""}`}
          onClick={() => setStudioTab("studio")}
        >
          Studio
        </button>
        <button
          type="button"
          className={`routine-tab${studioTab === "persona" ? " is-active" : ""}`}
          onClick={() => setStudioTab("persona")}
        >
          Teacher Persona
        </button>
      </div>

      {studioTab === "persona" ? (
        <PersonaEnrollment assets={assets} />
      ) : (
        <>
      <div className="home-prompt-section">
        <h2>AI Creative</h2>
        <p className="hint">
          Describe an image or video for your course, or bring in something you made on
          another platform.
        </p>
        <div className="creative-controls">
          <div className="creative-kind-toggle">
            <button
              type="button"
              className={`routine-tab${kind === "image" ? " is-active" : ""}`}
              onClick={() => setKind("image")}
            >
              Image
            </button>
            <button
              type="button"
              className={`routine-tab${kind === "video" ? " is-active" : ""}`}
              onClick={() => setKind("video")}
            >
              Video
            </button>
          </div>
          <select className="course-switcher" value={style} onChange={(e) => setStyle(e.target.value)}>
            {STYLE_OPTIONS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <form
          className="home-prompt-form"
          onSubmit={(e) => {
            e.preventDefault();
            handleGenerate();
          }}
        >
          <input
            className="auth-input home-prompt-input"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={`Describe the ${kind} you want to create…`}
            disabled={generating}
          />
          <button type="submit" className="btn btn-primary" disabled={generating || !prompt.trim()}>
            <IconSparkle /> {generating ? "Generating…" : "Generate"}
          </button>
        </form>

        <div className="upload-control">
          <input
            ref={fileInput}
            type="file"
            accept="image/*,video/*"
            onChange={handleFileChosen}
            disabled={uploading}
            hidden
            id="creative-upload-input"
          />
          <label htmlFor="creative-upload-input" className={`btn${uploading ? "" : " is-clickable"}`}>
            {uploading ? "Uploading…" : "Upload from another platform"}
          </label>
          <span className="upload-hint">Image up to 25MB, video up to 200MB</span>
        </div>
        {error && <div className="error-banner">{error}</div>}
      </div>

      <div className="creative-gallery">
        {previews.map((p) => (
          <div className="creative-card creative-card-preview" key={p.id}>
            <div className={`creative-thumb creative-thumb-mock creative-thumb-mock-${p.kind}`}>
              <IconSparkle />
            </div>
            <span className="status-pill creative-preview-badge">Preview — not connected to a generation provider yet</span>
            <p className="hint-inline">{p.prompt}</p>
            <span className="creative-card-meta">{p.style}</span>
          </div>
        ))}
        {assets.map((a) => (
          <div className="creative-card" key={a.id}>
            <AssetThumbnail asset={a} />
            <div className="creative-card-footer">
              <span className="creative-card-meta">{a.filename}</span>
              <button type="button" className="material-delete" onClick={() => handleDelete(a.id)} aria-label={`Delete ${a.filename}`}>
                <IconClose />
              </button>
            </div>
          </div>
        ))}
        {assets.length === 0 && previews.length === 0 && (
          <p className="hint">Nothing here yet — generate a preview above, or upload something you already have.</p>
        )}
      </div>
        </>
      )}
    </div>
  );
}
