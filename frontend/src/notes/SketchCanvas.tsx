import { Excalidraw } from "@excalidraw/excalidraw";
import "@excalidraw/excalidraw/index.css";
import { useRef } from "react";
import type { SketchScene } from "../studentAiApi.ts";
import { useTheme } from "../theme.ts";

interface SketchCanvasProps {
  initial: SketchScene | null;
  onChange: (scene: SketchScene) => void;
}

/** Excalidraw, loaded lazily by NotesPanel (it's a large bundle most lessons never need). */
export default function SketchCanvas({ initial, onChange }: SketchCanvasProps) {
  const theme = useTheme();
  // Excalidraw calls onChange for every pointer move, selection and zoom; only a
  // change to the drawing itself should trigger a save.
  const lastSaved = useRef<string>(initial ? JSON.stringify(initial.elements) : "[]");

  return (
    <div className="notes-sketch">
      <Excalidraw
        theme={theme}
        initialData={
          initial
            ? {
                // The stored elements came from Excalidraw itself.
                elements: initial.elements as never,
                appState: { viewBackgroundColor: initial.appState?.viewBackgroundColor },
                scrollToContent: true,
              }
            : undefined
        }
        // No image tool: images live in a separate files map that isn't stored.
        UIOptions={{ tools: { image: false }, canvasActions: { loadScene: false, saveToActiveFile: false } }}
        onChange={(elements, appState) => {
          const live = elements.filter((el) => !el.isDeleted);
          const serialized = JSON.stringify(live);
          if (serialized === lastSaved.current) return;
          lastSaved.current = serialized;
          onChange({ elements: live as unknown[], appState: { viewBackgroundColor: appState.viewBackgroundColor } });
        }}
      />
    </div>
  );
}
