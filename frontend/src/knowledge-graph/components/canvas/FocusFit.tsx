import { useReactFlow, useStore } from "@xyflow/react";
import { useEffect, useRef } from "react";
import { viewportFor } from "../../utils/viewport.ts";

// Re-frames the canvas whenever `frameKey` changes (a different node focused,
// or focus switched on/off). The first key is remembered without moving --
// InitialView owns the opening view.
export default function FocusFit({
  frameKey, positions, top, minZoom = 0.4,
}: { frameKey: string; positions: { x: number; y: number }[]; top: number; minZoom?: number }) {
  const { setViewport } = useReactFlow();
  const width = useStore((s) => s.width);
  const height = useStore((s) => s.height);
  const lastKey = useRef<string | null>(null);

  useEffect(() => {
    if (width === 0 || height === 0) return;
    if (lastKey.current === null) {
      lastKey.current = frameKey;
      return;
    }
    if (lastKey.current === frameKey || positions.length === 0) return;
    lastKey.current = frameKey;
    void setViewport(viewportFor(positions, { width, height }, { top, minZoom }), { duration: 300 });
    // positions is derived from frameKey's state; re-framing on every position change would fight dragging.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frameKey, width, height]);

  return null;
}
