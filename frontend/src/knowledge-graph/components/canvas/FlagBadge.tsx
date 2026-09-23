export type FlowRole = "start" | "end";

const LABELS: Record<FlowRole, { text: string; hint: string }> = {
  start: { text: "Start", hint: "Start — nothing has to come before this" },
  end: { text: "End", hint: "End — nothing else builds on this" },
};

// The Start / End marker shown on a card and in the legend.
export default function FlagBadge({ role }: { role: FlowRole }) {
  return (
    <span className={`kg-node-flag kg-node-flag-${role}`} title={LABELS[role].hint}>
      <svg viewBox="0 0 10 10" aria-hidden="true">
        {role === "start" ? (
          <path d="M2.5 1.5v7l6-3.5z" fill="currentColor" />
        ) : (
          <path d="M2.5 9V1.5M2.5 1.5h5.5l-1.5 2 1.5 2H2.5" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
        )}
      </svg>
      {LABELS[role].text}
    </span>
  );
}
