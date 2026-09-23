// Focus mode: the selected node, what leads into it (left) and what it leads
// to (right). A view-only layout -- never written back to the graph.
export interface GraphLink {
  id: string;
  source: string;
  target: string;
}

export interface Neighborhood {
  centerId: string;
  before: string[];
  after: string[];
  nodeIds: Set<string>;
  edgeIds: Set<string>;
  positions: Record<string, { x: number; y: number }>;
}

const COLUMN_GAP = 300;
const ROW_GAP = 100;

export function neighborhoodOf(centerId: string, links: GraphLink[]): Neighborhood {
  const before = new Set<string>();
  const after = new Set<string>();
  const edgeIds = new Set<string>();
  for (const l of links) {
    if (l.source === l.target) continue;
    if (l.target === centerId) {
      before.add(l.source);
      edgeIds.add(l.id);
    } else if (l.source === centerId) {
      after.add(l.target);
      edgeIds.add(l.id);
    }
  }
  // A node linked both ways sits on the "before" side only.
  for (const id of before) after.delete(id);

  const positions: Record<string, { x: number; y: number }> = { [centerId]: { x: 0, y: 0 } };
  const stack = (ids: string[], x: number) =>
    ids.forEach((id, i) => {
      positions[id] = { x, y: (i - (ids.length - 1) / 2) * ROW_GAP };
    });
  const beforeIds = [...before];
  const afterIds = [...after];
  stack(beforeIds, -COLUMN_GAP);
  stack(afterIds, COLUMN_GAP);

  return {
    centerId,
    before: beforeIds,
    after: afterIds,
    nodeIds: new Set([centerId, ...beforeIds, ...afterIds]),
    edgeIds,
    positions,
  };
}
