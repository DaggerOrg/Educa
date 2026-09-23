import { MiniMap } from "@xyflow/react";

// Overview of the whole graph with the current view outlined; drag or click
// it to jump somewhere else. Theming is in knowledge-graph.css (.kg-minimap).
export default function GraphMiniMap() {
  return <MiniMap className="kg-minimap" style={{ width: 160, height: 110 }} pannable zoomable ariaLabel="Graph overview" />;
}
