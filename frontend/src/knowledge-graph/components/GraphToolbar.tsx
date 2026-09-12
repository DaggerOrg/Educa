import { useReactFlow } from "@xyflow/react";
import { IconFitView, IconLayout, IconZoomIn, IconZoomOut } from "../../components/icons.tsx";

interface GraphToolbarProps {
  onResetLayout: () => void;
  showLabels: boolean;
  onToggleLabels: () => void;
}

export default function GraphToolbar({ onResetLayout, showLabels, onToggleLabels }: GraphToolbarProps) {
  const { fitView, zoomIn, zoomOut } = useReactFlow();

  return (
    <div className="kg-toolbar">
      <button type="button" className="btn kg-toolbar-btn" title="Fit view" onClick={() => fitView({ duration: 200 })}>
        <IconFitView />
      </button>
      <button type="button" className="btn kg-toolbar-btn" title="Zoom in" onClick={() => zoomIn({ duration: 150 })}>
        <IconZoomIn />
      </button>
      <button type="button" className="btn kg-toolbar-btn" title="Zoom out" onClick={() => zoomOut({ duration: 150 })}>
        <IconZoomOut />
      </button>
      <div className="kg-toolbar-divider" />
      <button type="button" className="btn kg-toolbar-btn" title="Reset / auto layout" onClick={onResetLayout}>
        <IconLayout />
      </button>
      <button
        type="button"
        className={`btn kg-toolbar-btn${showLabels ? " is-active" : ""}`}
        title={showLabels ? "Hide relationship labels" : "Show relationship labels"}
        onClick={onToggleLabels}
      >
        {showLabels ? "Labels: On" : "Labels: Off"}
      </button>
    </div>
  );
}
