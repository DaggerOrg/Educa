// Small overlay on the graph canvas: which graph this is (official vs draft)
// and a one-line reminder of the editing gestures. pointer-events: none, so
// it never blocks the canvas underneath.
export type GraphVariant = "official" | "draft";

interface StageChromeProps {
  variant: GraphVariant;
  hint?: string;
}

export default function StageChrome({ variant, hint }: StageChromeProps) {
  return (
    <>
      <span className={`status-pill kg-stage-pill kg-stage-pill-${variant}`}>
        {variant === "draft" ? "Draft graph" : "Official graph"}
      </span>
      {hint && <div className="kg-stage-hint">{hint}</div>}
    </>
  );
}

// Shown while Focus is on but nothing is selected, so the toggle never looks broken.
export function FocusNote() {
  return <div className="kg-focus-note">Focus is on — select a node to see only what leads to it and what it leads to.</div>;
}
