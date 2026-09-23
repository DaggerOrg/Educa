import { IconGraph, IconPath } from "../../../components/icons.tsx";
import type { GraphView } from "../../hooks/useGraphView.ts";

interface ViewSwitchProps {
  view: GraphView;
  onChange: (view: GraphView) => void;
}

const OPTIONS: { value: GraphView; label: string; hint: string; Icon: typeof IconGraph }[] = [
  { value: "graph", label: "Graph", hint: "The full graph on a canvas", Icon: IconGraph },
  { value: "path", label: "Path", hint: "A simple list, from the basics to the advanced", Icon: IconPath },
];

// Graph / Path: the same knowledge, drawn two ways.
export default function ViewSwitch({ view, onChange }: ViewSwitchProps) {
  return (
    <div className="kg-segmented" role="group" aria-label="How to show the knowledge graph">
      {OPTIONS.map(({ value, label, hint, Icon }) => (
        <button
          key={value}
          type="button"
          className={`kg-segmented-btn${view === value ? " is-active" : ""}`}
          aria-pressed={view === value}
          title={hint}
          onClick={() => onChange(value)}
        >
          <Icon /> {label}
        </button>
      ))}
    </div>
  );
}
