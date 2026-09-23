import type { Editor, JSONContent } from "@tiptap/react";
import { EditorContent, useEditor } from "@tiptap/react";
import { Placeholder } from "@tiptap/extensions";
import StarterKit from "@tiptap/starter-kit";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { IconCheck, IconClose, IconSparkle } from "../components/icons.tsx";
import type { NoteSuggestion } from "../studentAiApi.ts";
import { useAmbientSuggestions } from "./useAmbientSuggestions.ts";

interface NoteEditorProps {
  initialDoc: JSONContent | null;
  aiEnabled: boolean;
  onChange: (doc: JSONContent) => void;
  onEditor: (editor: Editor | null) => void;
  fetchSuggestion: (heading: string, surrounding: string, signal: AbortSignal) => Promise<NoteSuggestion>;
}

const PLACEHOLDER = "Take notes here. Type a heading like “What is present tense” and pause — I can write the notes for you.";

export default function NoteEditor({ initialDoc, aiEnabled, onChange, onEditor, fetchSuggestion }: NoteEditorProps) {
  const editor = useEditor({
    extensions: [StarterKit, Placeholder.configure({ placeholder: PLACEHOLDER })],
    content: initialDoc ?? undefined,
    shouldRerenderOnTransaction: true,
    editorProps: { attributes: { class: "notes-prose", "aria-label": "Lesson notes", spellcheck: "true" } },
    onUpdate: ({ editor: e }) => onChange(e.getJSON()),
  });

  useEffect(() => {
    onEditor(editor);
    return () => onEditor(null);
  }, [editor, onEditor]);

  const { state, accept, reject } = useAmbientSuggestions({ editor, enabled: aiEnabled, fetchSuggestion });

  // Keyboard: Tab takes the suggestion, Escape declines it -- like an inline completion.
  useEffect(() => {
    if (!editor || state.status !== "ready") return;
    const dom = editor.view.dom;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Tab" && !e.shiftKey) {
        e.preventDefault();
        accept();
      } else if (e.key === "Escape") {
        e.preventDefault();
        reject();
      }
    };
    dom.addEventListener("keydown", onKey);
    return () => dom.removeEventListener("keydown", onKey);
  }, [editor, state.status, accept, reject]);

  // Anchor the suggestion card under the title it belongs to. The wrapper
  // scrolls with the text, so the card scrolls with it.
  const wrapRef = useRef<HTMLDivElement>(null);
  const [top, setTop] = useState(0);
  const anchored = state.status === "loading" || state.status === "ready" ? state.candidate.insertAt : null;
  useLayoutEffect(() => {
    if (!editor || anchored == null || !wrapRef.current) return;
    try {
      const coords = editor.view.coordsAtPos(Math.max(1, anchored - 1));
      setTop(coords.bottom - wrapRef.current.getBoundingClientRect().top + 8);
    } catch {
      setTop(0);
    }
  }, [editor, anchored, state.status]);

  return (
    <div className="notes-editor-wrap" ref={wrapRef}>
      <Toolbar editor={editor} />
      <EditorContent editor={editor} className="notes-editor" />

      {state.status === "loading" && (
        <div className="notes-suggest notes-suggest--loading" style={{ top }} role="status">
          <IconSparkle /> Writing notes on “{state.candidate.text}”…
        </div>
      )}
      {state.status === "ready" && (
        <SuggestionCard
          top={top}
          heading={state.candidate.text}
          suggestion={state.suggestion}
          onAccept={accept}
          onReject={reject}
        />
      )}
      {state.status === "limit" && (
        <p className="notes-ai-note" role="status">You've used today's AI note suggestions. You can still write your own notes.</p>
      )}
      {state.status === "error" && (
        <p className="notes-ai-note" role="status">The note helper isn't available right now.</p>
      )}
    </div>
  );
}

function SuggestionCard({
  top,
  heading,
  suggestion,
  onAccept,
  onReject,
}: {
  top: number;
  heading: string;
  suggestion: NoteSuggestion;
  onAccept: () => void;
  onReject: () => void;
}) {
  // Keep the caret in the editor when a button is pressed.
  const keepFocus = (e: React.MouseEvent) => e.preventDefault();
  return (
    <div className="notes-suggest" style={{ top }} role="dialog" aria-label={`Suggested notes for ${heading}`}>
      <div className="notes-suggest-head">
        <span className="notes-suggest-title"><IconSparkle /> Want me to write notes on “{heading}”?</span>
        <span className={`status-pill ${suggestion.source === "lesson" ? "status-approved" : "status-draft"}`}>
          {suggestion.source === "lesson" ? "From your lesson" : "General knowledge"}
        </span>
      </div>
      {suggestion.summary && <p className="notes-suggest-summary">{suggestion.summary}</p>}
      <ul className="notes-suggest-points">
        {suggestion.key_points.map((p, i) => <li key={i}>{p}</li>)}
      </ul>
      {suggestion.example && <p className="notes-suggest-example"><strong>Example:</strong> {suggestion.example}</p>}
      <div className="notes-suggest-actions">
        <button type="button" className="btn btn-primary" onMouseDown={keepFocus} onClick={onAccept}>
          <IconCheck /> Accept
        </button>
        <button type="button" className="btn" onMouseDown={keepFocus} onClick={onReject}>
          <IconClose /> Reject
        </button>
        <span className="notes-suggest-keys">Tab to accept · Esc to dismiss</span>
      </div>
    </div>
  );
}

function Toolbar({ editor }: { editor: Editor | null }) {
  if (!editor) return null;
  const item = (label: string, active: boolean, run: () => void, text: string) => (
    <button
      type="button"
      className={`notes-tool${active ? " is-active" : ""}`}
      aria-label={label}
      aria-pressed={active}
      title={label}
      onMouseDown={(e) => e.preventDefault()}
      onClick={run}
    >
      {text}
    </button>
  );
  return (
    <div className="notes-toolbar" role="toolbar" aria-label="Formatting">
      {item("Heading", editor.isActive("heading", { level: 2 }), () => editor.chain().focus().toggleHeading({ level: 2 }).run(), "H")}
      {item("Bold", editor.isActive("bold"), () => editor.chain().focus().toggleBold().run(), "B")}
      {item("Italic", editor.isActive("italic"), () => editor.chain().focus().toggleItalic().run(), "I")}
      {item("Bullet list", editor.isActive("bulletList"), () => editor.chain().focus().toggleBulletList().run(), "•")}
    </div>
  );
}
