// Which links a canvas draws. "flow" keeps the picture readable: only the
// learn-this-first path, plus anything that needs attention or belongs to what
// the user has selected. "all" draws everything.
export type LinkDetail = "flow" | "all";

export interface LinkFacts {
  type: string;
  source: string;
  target: string;
  // An AI-suggested link still waiting for a teacher's approval.
  pendingReview: boolean;
}

export function isLinkShown(
  link: LinkFacts,
  detail: LinkDetail,
  selection: { nodeIds: ReadonlySet<string>; linkSelected: boolean },
): boolean {
  return (
    detail === "all" ||
    link.type === "prerequisite_of" ||
    link.pendingReview ||
    selection.linkSelected ||
    selection.nodeIds.has(link.source) ||
    selection.nodeIds.has(link.target)
  );
}
