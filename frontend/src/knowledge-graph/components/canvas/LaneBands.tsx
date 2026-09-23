import { ViewportPortal } from "@xyflow/react";
import { useMemo } from "react";
import type { KnowledgeNodeType } from "../../types/knowledgeGraph.ts";
import { lanesFromPositions } from "../../utils/graphLayout.ts";

// Labeled horizontal bands behind the cards, one per node type. Drawn in
// flow coordinates so they pan and zoom with the graph; they hold no state
// and never touch the nodes themselves.
export default function LaneBands({ items }: { items: { type: KnowledgeNodeType; x: number; y: number }[] }) {
  const bands = useMemo(() => lanesFromPositions(items), [items]);
  if (bands.length === 0) return null;
  return (
    <ViewportPortal>
      {bands.map((b) => (
        <div
          key={b.type}
          className="kg-lane"
          style={{ transform: `translate(${b.x}px, ${b.y}px)`, width: b.width, height: b.height }}
        >
          <span className="kg-lane-label">{b.label}</span>
        </div>
      ))}
    </ViewportPortal>
  );
}
