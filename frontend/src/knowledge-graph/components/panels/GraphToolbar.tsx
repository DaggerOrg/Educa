import { useReactFlow } from "@xyflow/react";
import { IconFitView, IconLayout, IconZoomIn, IconZoomOut } from "../../../components/icons.tsx";

interface GraphToolbarProps {
  onResetLayout: () => void;
  showLabels: boolean;
  onToggleLabels: () => void;
  focusMode: boolean;
  onToggleFocus: () => void;
  linkDetail: "flow" | "all";
  onToggleLinks: () => void;
  // Undefined when there is nowhere to go back to.
  onBack?: () => void;
}

export default function GraphToolbar({
  onResetLayout, showLabels, onToggleLabels, focusMode, onToggleFocus, linkDetail, onToggleLinks, onBack,
}: GraphToolbarProps) {
  const { fitView, zoomIn, zoomOut } = useReactFlow();

  return (
    <div className="kg-toolbar">
      {onBack && (
        <>
          <button type="button" className="btn kg-toolbar-btn" title="Back to the previous node" onClick={onBack}>
            ← Back
          </button>
          <div className="kg-toolbar-divider" />
        </>
      )}
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
      <button type="button" className="btn kg-toolbar-btn" title="Tidy into lanes" onClick={onResetLayout}>
        <IconLayout />
      </button>
      <button
        type="button"
        className={`btn kg-toolbar-btn${linkDetail === "all" ? " is-active" : ""}`}
        title={linkDetail === "flow" ? "Showing the learn-this-first path (and the links of the selected node). Click to show every link." : "Showing every link. Click to show only the learn-this-first path."}
        onClick={onToggleLinks}
      >
        {linkDetail === "flow" ? "Links: Flow" : "Links: All"}
      </button>
      <button
        type="button"
        className={`btn kg-toolbar-btn${focusMode ? " is-active" : ""}`}
        title={focusMode ? "Show the whole graph" : "Show only the selected node and its connections"}
        onClick={onToggleFocus}
      >
        {focusMode ? "Focus: On" : "Focus: Off"}
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
