import { NODE_TYPE_LABELS, type KnowledgeNodeType } from "../types/knowledgeGraph.ts";

// Lane layout -- deterministic, no auto-layout dependency (dagre/elkjs).
//   rows    = lanes, one per node type (Concepts, Skills, Exercises, ...)
//   columns = how far along the "learn this first" chain a node is, so the
//             graph reads left to right from where a learner starts to
//             where they finish. Nodes that aren't part of that chain
//             (skills, exercises, resources, levels) sit under the leftmost
//             concept they're connected to.
// "Auto Layout"/"Reset Layout" in GraphToolbar and the live board's Tidy
// button both just re-run this.

export interface LayoutNode {
  id: string;
  type: KnowledgeNodeType;
  // Level nodes (A1..C2) are laid out in CEFR order rather than by their links.
  name?: string;
}

export interface LayoutLink {
  source: string;
  target: string;
  type: string;
}

const PREREQUISITE = "prerequisite_of";

// Card footprint (a card is 200px wide; height varies, so a typical two-line card is assumed).
export const NODE_W = 200;
const NODE_H = 64;

const COL_W = 260;
const ROW_H = 84;
const HEADER = 36; // room above a lane's first row for its label
const LANE_GAP = 24;
const CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"];
// A column taller than this spills into the next column to its right, so one busy column can't make a lane tower.
const MAX_STACK = 3;

const LANE_ORDER: KnowledgeNodeType[] = ["concept", "skill", "learning_objective", "exercise", "resource", "level"];

// How many "learn this first" steps come before each node: the longest path back to a node with no prerequisites
// (0 = nothing has to come first). Only nodes on a prerequisite chain get an entry. A cycle can't be drawn as a
// sequence, so its back edge is ignored. The caller passes links between nodes that exist.
export function prerequisiteDepths(links: LayoutLink[]): Map<string, number> {
  const preds = new Map<string, string[]>();
  const inChain = new Set<string>();
  for (const l of links) {
    if (l.type !== PREREQUISITE) continue;
    preds.set(l.target, [...(preds.get(l.target) ?? []), l.source]);
    inChain.add(l.source);
    inChain.add(l.target);
  }

  const depth = new Map<string, number>();
  const visiting = new Set<string>();
  const depthOf = (id: string): number => {
    const known = depth.get(id);
    if (known !== undefined) return known;
    if (visiting.has(id)) return 0;
    visiting.add(id);
    let d = 0;
    for (const p of preds.get(id) ?? []) d = Math.max(d, depthOf(p) + 1);
    visiting.delete(id);
    depth.set(id, d);
    return d;
  };

  const result = new Map<string, number>();
  for (const id of inChain) result.set(id, depthOf(id));
  return result;
}

function computeColumns(nodes: LayoutNode[], links: LayoutLink[]): Map<string, number> {
  const ids = new Set(nodes.map((n) => n.id));
  const valid = links.filter((l) => ids.has(l.source) && ids.has(l.target) && l.source !== l.target);

  const col = prerequisiteDepths(valid);

  const neighbors = new Map<string, string[]>();
  for (const l of valid) {
    neighbors.set(l.source, [...(neighbors.get(l.source) ?? []), l.target]);
    neighbors.set(l.target, [...(neighbors.get(l.target) ?? []), l.source]);
  }
  let progressed = true;
  while (progressed) {
    progressed = false;
    for (const n of nodes) {
      if (col.has(n.id)) continue;
      const placed = (neighbors.get(n.id) ?? []).filter((id) => col.has(id)).map((id) => col.get(id)!);
      if (placed.length > 0) {
        col.set(n.id, Math.min(...placed));
        progressed = true;
      }
    }
  }
  for (const n of nodes) if (!col.has(n.id)) col.set(n.id, 0);
  return col;
}

export function computeLaneLayout(nodes: LayoutNode[], links: LayoutLink[]): Record<string, { x: number; y: number }> {
  const col = computeColumns(nodes, links);
  const positions: Record<string, { x: number; y: number }> = {};
  const types = [...LANE_ORDER, ...nodes.map((n) => n.type).filter((t) => !LANE_ORDER.includes(t))];

  let top = 0;
  for (const type of new Set(types)) {
    const members = nodes.filter((n) => n.type === type).sort((a, b) => col.get(a.id)! - col.get(b.id)!);
    if (members.length === 0) continue;
    if (type === "level" && members.every((n) => CEFR_ORDER.includes(n.name ?? ""))) {
      for (const n of members) positions[n.id] = { x: CEFR_ORDER.indexOf(n.name!) * COL_W, y: top + HEADER };
      top += HEADER + ROW_H + LANE_GAP;
      continue;
    }
    const stack = new Map<number, number>();
    let rows = 1;
    for (const n of members) {
      let slot = col.get(n.id)!;
      while ((stack.get(slot) ?? 0) >= MAX_STACK) slot++;
      const row = stack.get(slot) ?? 0;
      stack.set(slot, row + 1);
      rows = Math.max(rows, row + 1);
      positions[n.id] = { x: slot * COL_W, y: top + HEADER + row * ROW_H };
    }
    top += HEADER + rows * ROW_H + LANE_GAP;
  }
  return positions;
}

// Where a newly added node goes without disturbing the rest: at the end of its
// own type's lane (or below everything if that type has no lane yet).
export function placeInLane(
  created: LayoutNode,
  existing: (LayoutNode & { position?: { x: number; y: number } })[],
): { x: number; y: number } {
  const placed = existing.filter((n) => n.position);
  const same = placed.filter((n) => n.type === created.type);
  if (same.length > 0) {
    return {
      x: Math.max(...same.map((n) => n.position!.x)) + COL_W,
      y: Math.min(...same.map((n) => n.position!.y)),
    };
  }
  const bottom = placed.length > 0 ? Math.max(...placed.map((n) => n.position!.y)) + ROW_H : 0;
  return { x: 0, y: bottom + LANE_GAP + HEADER };
}

// Start = something learners can begin with (it leads on to other things, and
// nothing has to come before it). End = something nothing else builds on.
// Only the "learn this first" arrows count, and only for nodes that have one.
export function flowRoles(links: LayoutLink[]): Map<string, "start" | "end"> {
  const hasIn = new Set<string>();
  const hasOut = new Set<string>();
  for (const l of links) {
    if (l.type !== PREREQUISITE || l.source === l.target) continue;
    hasOut.add(l.source);
    hasIn.add(l.target);
  }
  const roles = new Map<string, "start" | "end">();
  for (const id of hasOut) if (!hasIn.has(id)) roles.set(id, "start");
  for (const id of hasIn) if (!hasOut.has(id)) roles.set(id, "end");
  return roles;
}

export interface LaneBand {
  type: KnowledgeNodeType;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

// Draws a band per type from where the nodes actually are, so it stays true
// after dragging. If the bands would overlap (a free-form layout, or Focus
// mode's columns) there are no lanes to show, so none are drawn.
export function lanesFromPositions(items: { type: KnowledgeNodeType; x: number; y: number }[]): LaneBand[] {
  if (items.length === 0) return [];
  const minX = Math.min(...items.map((i) => i.x)) - 20;
  const maxX = Math.max(...items.map((i) => i.x)) + NODE_W + 20;

  const byType = new Map<KnowledgeNodeType, { minY: number; maxY: number }>();
  for (const i of items) {
    const b = byType.get(i.type);
    byType.set(i.type, { minY: Math.min(b?.minY ?? i.y, i.y), maxY: Math.max(b?.maxY ?? i.y, i.y) });
  }

  const bands: LaneBand[] = [...byType.entries()]
    .map(([type, { minY, maxY }]) => ({
      type,
      label: NODE_TYPE_LABELS[type],
      x: minX,
      y: minY - HEADER,
      width: maxX - minX,
      height: maxY - minY + HEADER + NODE_H + 12,
    }))
    .sort((a, b) => a.y - b.y);

  if (bands.length < 2) return [];
  for (let i = 0; i < bands.length - 1; i++) {
    if (bands[i].y + bands[i].height > bands[i + 1].y) return [];
  }
  return bands;
}
