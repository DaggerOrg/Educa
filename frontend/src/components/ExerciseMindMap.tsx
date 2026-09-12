import type { Exercise } from "../types.ts";

// Deliberately not the knowledge-graph/ React Flow setup -- that page is
// an unrelated, hardcoded demo with no backend. This is a small, live
// visualization of one lesson's own generated exercises: plain positioned
// nodes around a center, re-rendering whenever `exercises` changes (which
// the existing 2s course poll in App.tsx already delivers).
const KIND_LABEL: Record<Exercise["kind"], string> = {
  multiple_choice: "MC",
  true_false: "T/F",
  flashcard: "Card",
};

function excerpt(text: string, max = 42): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

interface ExerciseMindMapProps {
  lessonTitle: string | null;
  exercises: Exercise[];
}

export default function ExerciseMindMap({ lessonTitle, exercises }: ExerciseMindMapProps) {
  const radius = 42;
  const center = 50;

  return (
    <div className="mind-map">
      <h3 className="mind-map-title">Mind map</h3>
      {exercises.length === 0 ? (
        <p className="hint">Exercises you generate for this lesson will appear here as they're added.</p>
      ) : (
        <svg className="mind-map-canvas" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
          {exercises.map((ex, i) => {
            const angle = (2 * Math.PI * i) / exercises.length - Math.PI / 2;
            const x = center + radius * Math.cos(angle);
            const y = center + radius * Math.sin(angle);
            return (
              <line
                key={`edge-${ex.id}`}
                x1={center}
                y1={center}
                x2={x}
                y2={y}
                className="mind-map-edge"
              />
            );
          })}
          <circle cx={center} cy={center} r={9} className="mind-map-center" />
          <text x={center} y={center} className="mind-map-center-label" textAnchor="middle" dominantBaseline="middle">
            {lessonTitle ? excerpt(lessonTitle, 12) : "Lesson"}
          </text>
          {exercises.map((ex, i) => {
            const angle = (2 * Math.PI * i) / exercises.length - Math.PI / 2;
            const x = center + radius * Math.cos(angle);
            const y = center + radius * Math.sin(angle);
            return (
              <g key={ex.id} className={`mind-map-node mind-map-node-${ex.kind}`}>
                <circle cx={x} cy={y} r={6} />
                <text x={x} y={y} textAnchor="middle" dominantBaseline="middle">
                  {KIND_LABEL[ex.kind]}
                </text>
                <title>{excerpt(ex.prompt, 80)}</title>
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
}
