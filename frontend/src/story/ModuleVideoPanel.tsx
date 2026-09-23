import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../api.ts";
import { IconClose, IconPlus, IconSparkle } from "../components/icons.tsx";
import {
  approveStory,
  deleteStory,
  generateStoryScript,
  getTeacherStory,
  renderStory,
  saveStoryScript,
  type StoryScene,
  type StoryScript,
  type StoryStatus,
  type TeacherStory,
} from "../studentAiApi.ts";
import StoryPlayer from "./StoryPlayer.tsx";

interface ModuleVideoPanelProps {
  moduleId: string;
  weekLabel: string;
  onClose: () => void;
}

const MAX_SCENES = 8;
const STATUS_LABEL: Record<StoryStatus, string> = {
  draft: "Draft",
  approved: "Script approved",
  queued: "Queued",
  rendering: "Rendering",
  ready: "Ready for students",
  failed: "Failed",
};
const STATUS_CLASS: Record<StoryStatus, string> = {
  draft: "status-draft",
  approved: "status-approved",
  queued: "status-approved",
  rendering: "status-approved",
  ready: "status-published",
  failed: "status-draft",
};

const blankScene = (): StoryScene => ({ narration: "", on_screen_text: "", visual: "", seconds: 8 });

export default function ModuleVideoPanel({ moduleId, weekLabel, onClose }: ModuleVideoPanelProps) {
  const [story, setStory] = useState<TeacherStory | null | undefined>(undefined); // undefined = loading
  const [draft, setDraft] = useState<StoryScript | null>(null);
  const [dirty, setDirty] = useState(false);
  const [style, setStyle] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewing, setPreviewing] = useState(false);

  const adopt = useCallback((next: TeacherStory | null) => {
    setStory(next);
    setDraft(next?.script ?? null);
    setDirty(false);
    if (next) setStyle(next.style);
  }, []);

  useEffect(() => {
    getTeacherStory(moduleId).then(adopt).catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [moduleId, adopt]);

  // While a render is in flight, keep checking on it.
  const status = story?.status;
  useEffect(() => {
    if (status !== "queued" && status !== "rendering") return;
    const id = window.setInterval(() => {
      getTeacherStory(moduleId)
        .then((latest) => {
          if (latest && latest.status !== status) {
            setStory(latest);
            if (latest.status === "ready" || latest.status === "failed") setBusy(null);
          }
        })
        .catch(() => undefined);
    }, 2000);
    return () => window.clearInterval(id);
  }, [status, moduleId]);

  async function act(label: string, fn: () => Promise<TeacherStory | null>) {
    setBusy(label);
    setError(null);
    try {
      adopt(await fn());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "That didn't work. Try again.");
    } finally {
      setBusy(null);
    }
  }

  function edit(change: (s: StoryScript) => StoryScript) {
    setDraft((d) => (d ? change(d) : d));
    setDirty(true);
  }
  const editScene = (i: number, patch: Partial<StoryScene>) =>
    edit((s) => ({ ...s, scenes: s.scenes.map((sc, si) => (si === i ? { ...sc, ...patch } : sc)) }));

  function write() {
    if (dirty && !window.confirm("Replace your edits with a new draft?")) return;
    void act("write", () => generateStoryScript(moduleId, style));
  }

  const inFlight = status === "queued" || status === "rendering";
  const locked = busy !== null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card modal-card--wide story-editor" role="dialog" aria-label="Story video" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span>Story video — {weekLabel}</span>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            <IconClose />
          </button>
        </div>

        {error && <div className="error-banner">{error}</div>}
        {story === undefined && !error && <p className="hint">Loading…</p>}

        {story === null && (
          <div className="story-intro">
            <p className="hint">
              A short, story-style clip narrated by your avatar that explains this module. I'll draft the script from its
              lessons; you edit and approve it before anything is rendered.
            </p>
            <label className="field-label" htmlFor="story-style">Tone (optional)</label>
            <input
              id="story-style"
              className="auth-input"
              value={style}
              maxLength={300}
              placeholder="e.g. playful, for teenagers"
              onChange={(e) => setStyle(e.target.value)}
            />
            <button type="button" className="btn btn-primary" disabled={locked} onClick={write}>
              <IconSparkle /> {busy === "write" ? "Writing…" : "Write the story"}
            </button>
          </div>
        )}

        {story && draft && (
          <>
            <div className="story-status-row">
              <span className={`status-pill ${STATUS_CLASS[story.status]}`}>{STATUS_LABEL[story.status]}</span>
              {dirty && <span className="hint">Unsaved edits</span>}
            </div>
            {story.status === "queued" && (
              <p className="hint">
                Waiting for the background worker. If nothing happens, start it with{" "}
                <code>python -m curriculum_ai.jobs.worker</code>.
              </p>
            )}
            {story.status === "failed" && story.error && <div className="error-banner">{story.error}</div>}
            {story.status === "ready" && (
              <p className="hint">
                {story.kind === "video"
                  ? "Students can watch this video from the course page."
                  : "Students can play this as a storyboard from the course page — no video provider is connected, so scenes are described rather than filmed."}
              </p>
            )}

            <fieldset className="story-fields" disabled={inFlight}>
              <label className="field-label" htmlFor="story-title">Title</label>
              <input id="story-title" className="auth-input" value={draft.title} onChange={(e) => edit((s) => ({ ...s, title: e.target.value }))} />
              <label className="field-label" htmlFor="story-hook">Opening line</label>
              <input id="story-hook" className="auth-input" value={draft.hook} onChange={(e) => edit((s) => ({ ...s, hook: e.target.value }))} />

              {draft.scenes.map((scene, i) => (
                <div className="story-scene" key={i}>
                  <div className="story-scene-head">
                    <span className="field-label">Scene {i + 1}</span>
                    {draft.scenes.length > 1 && (
                      <button
                        type="button"
                        className="btn"
                        onClick={() => edit((s) => ({ ...s, scenes: s.scenes.filter((_, si) => si !== i) }))}
                        aria-label={`Remove scene ${i + 1}`}
                      >
                        <IconClose />
                      </button>
                    )}
                  </div>
                  <label className="field-label" htmlFor={`scene-${i}-narration`}>What the avatar says</label>
                  <textarea id={`scene-${i}-narration`} className="auth-input" rows={2} value={scene.narration} onChange={(e) => editScene(i, { narration: e.target.value })} />
                  <div className="story-scene-row">
                    <div>
                      <label className="field-label" htmlFor={`scene-${i}-caption`}>Caption</label>
                      <input id={`scene-${i}-caption`} className="auth-input" value={scene.on_screen_text} maxLength={80} onChange={(e) => editScene(i, { on_screen_text: e.target.value })} />
                    </div>
                    <div className="story-seconds">
                      <label className="field-label" htmlFor={`scene-${i}-seconds`}>Seconds</label>
                      <input id={`scene-${i}-seconds`} className="auth-input" type="number" min={3} max={30} value={scene.seconds} onChange={(e) => editScene(i, { seconds: Number(e.target.value) || 8 })} />
                    </div>
                  </div>
                  <label className="field-label" htmlFor={`scene-${i}-visual`}>What it looks like</label>
                  <input id={`scene-${i}-visual`} className="auth-input" value={scene.visual} onChange={(e) => editScene(i, { visual: e.target.value })} />
                </div>
              ))}
              {draft.scenes.length < MAX_SCENES && (
                <button type="button" className="btn" onClick={() => edit((s) => ({ ...s, scenes: [...s.scenes, blankScene()] }))}>
                  <IconPlus /> Add a scene
                </button>
              )}

              <label className="field-label" htmlFor="story-takeaway">Closing takeaway</label>
              <input id="story-takeaway" className="auth-input" value={draft.takeaway} onChange={(e) => edit((s) => ({ ...s, takeaway: e.target.value }))} />
            </fieldset>

            <div className="story-actions">
              <button type="button" className="btn" disabled={locked || inFlight} onClick={write}>
                {busy === "write" ? "Writing…" : "Rewrite with AI"}
              </button>
              <button type="button" className="btn" disabled={locked || !dirty} onClick={() => act("save", () => saveStoryScript(moduleId, draft))}>
                {busy === "save" ? "Saving…" : "Save edits"}
              </button>
              <button type="button" className="btn" onClick={() => setPreviewing(true)}>Preview</button>
              {story.status === "draft" && (
                <button type="button" className="btn btn-primary" disabled={locked || dirty} onClick={() => act("approve", () => approveStory(moduleId))}>
                  Approve script
                </button>
              )}
              {(story.status === "approved" || story.status === "failed" || story.status === "ready") && (
                <button type="button" className="btn btn-primary" disabled={locked || dirty} onClick={() => act("render", () => renderStory(moduleId))}>
                  {busy === "render" ? "Queuing…" : story.status === "ready" ? "Render again" : "Render"}
                </button>
              )}
              <button
                type="button"
                className="btn"
                disabled={locked}
                onClick={() => {
                  if (window.confirm("Delete this story? Students will no longer see it.")) void act("delete", async () => (await deleteStory(moduleId), null));
                }}
              >
                Delete
              </button>
            </div>
          </>
        )}
      </div>

      {previewing && draft && (
        <StoryPlayer title={draft.title} script={draft} narratorName={null} kind="storyboard" onClose={() => setPreviewing(false)} />
      )}
    </div>
  );
}
