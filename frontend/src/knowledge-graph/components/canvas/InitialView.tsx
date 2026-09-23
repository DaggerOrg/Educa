import { useReactFlow, useStore } from "@xyflow/react";
import { useEffect, useRef } from "react";
import { viewportFor } from "../../utils/viewport.ts";

// Opens the graph at a zoom where node text is readable (see viewportFor).
// Runs once, from node positions and the canvas size -- not from measured
// node dimensions, which the read-only canvases never write back into state.
// The "fit view" control still shows everything.
export default function InitialView({ top }: { top: number }) {
  const { getNodes, setViewport } = useReactFlow();
  const width = useStore((s) => s.width);
  const height = useStore((s) => s.height);
  const done = useRef(false);

  useEffect(() => {
    if (done.current || width === 0 || height === 0) return;
    done.current = true;
    const nodes = getNodes();
    if (nodes.length === 0) return;
    void setViewport(viewportFor(nodes.map((n) => n.position), { width, height }, { top, minZoom: 0.75 }));
  }, [width, height, top, getNodes, setViewport]);

  return null;
}
