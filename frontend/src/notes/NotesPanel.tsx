import type { Editor, JSONContent } from "@tiptap/react";
import { Suspense, lazy, useCallback, useEffect, useState } from "react";
import { ApiError } from "../api.ts";
import { IconClose, IconSparkle } from "../components/icons.tsx";
import {
  getNotes,
  saveNotes,
  suggestNote,
  type AssistResult,
  type NoteDoc,
  type SketchScene,
  type StoredNotes,
} from "../studentAiApi.ts";
import AiHelpers from "./AiHelpers.tsx";
import NoteEditor from "./NoteEditor.tsx";
import { assistToContent } from "./content.ts";
import { combineSaveStates, useDebouncedSave, type SaveState } from "./useDebouncedSave.ts";

// Excalidraw is large; only load it once a student actually opens the sketch tab.
const SketchCanvas = lazy(() => import("./SketchCanvas.tsx"));

type Tab = "notes" | "sketch" | "helpers";

interface NotesPanelProps {
  courseId: string;
  lessonId: string;
  userId: string;
  onClose: () => void;
}

const SAVE_LABEL: Record<SaveState, string> = { idle: "", saving: "Saving…", saved: "Saved", error: "Couldn't save — will retry" };

const aiKey = (userId: string) => `educa_notes_ai_${userId}`;
function loadAiEnabled(userId: string): boolean {
  try {
    return localStorage.getItem(aiKey(userId)) !== "off";
  } catch {
    return true;
  }
}

export default function NotesPanel({ courseId, lessonId, userId, onClose }: NotesPanelProps) {
  const [stored, setStored] = useState<StoredNotes | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("notes");
  const [sketchOpened, setSketchOpened] = useState(false);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [aiEnabled, setAiEnabled] = useState(() => loadAiEnabled(userId));

  useEffect(() => {
    let cancelled = false;
    getNotes(courseId, lessonId)
      .then((n) => !cancelled && setStored(n))
      .catch((e) => !cancelled && setLoadError(e instanceof ApiError ? e.message : "Your notes couldn't be loaded."));
    return () => {
      cancelled = true;
    };
  }, [courseId, lessonId]);

  const docSaver = useDebouncedSave<NoteDoc>((doc) => saveNotes(courseId, lessonId, { doc }));
  const sketchSaver = useDebouncedSave<SketchScene>((sketch) => saveNotes(courseId, lessonId, { sketch }));
  const saveState = combineSaveStates(docSaver.state, sketchSaver.state);

  function toggleAi() {
    const next = !aiEnabled;
    setAiEnabled(next);
    try {
      localStorage.setItem(aiKey(userId), next ? "on" : "off");
    } catch {
      // The preference just won't persist on this device.
    }
  }

  function selectTab(next: Tab) {
    setTab(next);
    if (next === "sketch") setSketchOpened(true);
  }

  const scheduleDoc = docSaver.schedule; // stable across renders, unlike the object it comes from
  const onDocChange = useCallback((doc: JSONContent) => scheduleDoc(doc as NoteDoc), [scheduleDoc]);
  const fetchSuggestion = useCallback(
    (heading: string, surrounding: string, signal: AbortSignal) => suggestNote(courseId, lessonId, heading, surrounding, signal),
    [courseId, lessonId],
  );

  function addToNotes(result: AssistResult) {
    if (!editor) return;
    editor.chain().focus("end").insertContent(assistToContent(result)).run();
    setTab("notes");
  }

  return (
    <aside className="notes-panel" aria-label="My notes">
      <div className="notes-panel-head">
        <span className="notes-panel-title">My notes</span>
        <div className="notes-panel-head-actions">
          <span className="notes-save-state" role="status" aria-live="polite">{SAVE_LABEL[saveState]}</span>
          <button
            type="button"
            role="switch"
            aria-checked={aiEnabled}
            className={`notes-ai-toggle${aiEnabled ? " is-on" : ""}`}
            onClick={toggleAi}
            title="When on, the AI offers to write notes after you type a heading and pause"
          >
            <IconSparkle /> AI suggestions {aiEnabled ? "on" : "off"}
          </button>
          <button type="button" className="chat-drawer-close" onClick={onClose} aria-label="Close notes">
            <IconClose />
          </button>
        </div>
      </div>

      <div className="notes-tabs" role="tablist">
        {(["notes", "sketch", "helpers"] as const).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            className={`notes-tab${tab === t ? " is-active" : ""}`}
            onClick={() => selectTab(t)}
          >
            {t === "notes" ? "Notes" : t === "sketch" ? "Sketch" : "AI helpers"}
          </button>
        ))}
      </div>

      <div className="notes-panel-body">
        {loadError ? (
          <div className="error-banner">{loadError}</div>
        ) : !stored ? (
          <p className="hint">Loading your notes…</p>
        ) : (
          <>
            <div hidden={tab !== "notes"} className="notes-pane">
              <NoteEditor
                initialDoc={stored.doc as JSONContent | null}
                aiEnabled={aiEnabled}
                onChange={onDocChange}
                onEditor={setEditor}
                fetchSuggestion={fetchSuggestion}
              />
            </div>
            <div hidden={tab !== "sketch"} className="notes-pane">
              {sketchOpened && (
                <Suspense fallback={<p className="hint">Loading the canvas…</p>}>
                  <SketchCanvas initial={stored.sketch} onChange={sketchSaver.schedule} />
                </Suspense>
              )}
            </div>
            <div hidden={tab !== "helpers"} className="notes-pane">
              <AiHelpers
                courseId={courseId}
                lessonId={lessonId}
                getNotesText={() => editor?.getText() ?? ""}
                onAddToNotes={addToNotes}
              />
            </div>
          </>
        )}
      </div>
    </aside>
  );
}
