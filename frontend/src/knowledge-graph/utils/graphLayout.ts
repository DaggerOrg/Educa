import type { KnowledgeNode } from "../types/knowledgeGraph.ts";

// Deterministic cluster layout -- no auto-layout dependency (dagre/elkjs).
// Groups nodes into named regions (grammar/vocabulary/skills/activities/
// assessment/objectives/resources/levels) and lays each region out as a
// simple wrapping grid, with regions placed at fixed offsets so related
// nodes stay visually together instead of being scattered. "Auto Layout"
// and "Reset Layout" in GraphToolbar both just re-run this.

const NODE_WIDTH = 200;
const NODE_HEIGHT = 92;
const COL_GAP = 40;
const ROW_GAP = 32;

interface Region {
  key: string;
  columns: number;
  origin: { x: number; y: number };
  matches: (node: KnowledgeNode) => boolean;
}

const REGIONS: Region[] = [
  { key: "grammar", columns: 2, origin: { x: 0, y: 0 }, matches: (n) => n.type === "concept" && n.category === "grammar" },
  { key: "vocabulary", columns: 2, origin: { x: 0, y: 520 }, matches: (n) => n.type === "concept" && n.category === "vocabulary" },
  { key: "reading-writing-skills", columns: 2, origin: { x: 0, y: 720 }, matches: (n) => n.type === "concept" && (n.category === "reading-skills" || n.category === "writing-skills") },
  { key: "skills", columns: 1, origin: { x: 560, y: 0 }, matches: (n) => n.type === "skill" },
  { key: "activities", columns: 2, origin: { x: 800, y: 0 }, matches: (n) => n.type === "exercise" && n.category === "activity" },
  { key: "assessment", columns: 1, origin: { x: 800, y: 460 }, matches: (n) => n.type === "exercise" && n.category === "assessment" },
  { key: "objectives", columns: 1, origin: { x: 560, y: 460 }, matches: (n) => n.type === "learning_objective" },
  { key: "resources", columns: 1, origin: { x: 560, y: 620 }, matches: (n) => n.type === "resource" },
  { key: "levels", columns: 6, origin: { x: 0, y: 940 }, matches: (n) => n.type === "level" },
];

export function computeClusteredLayout(nodes: KnowledgeNode[]): Record<string, { x: number; y: number }> {
  const positions: Record<string, { x: number; y: number }> = {};
  const assigned = new Set<string>();

  for (const region of REGIONS) {
    const members = nodes.filter((n) => !assigned.has(n.id) && region.matches(n));
    members.forEach((n, i) => {
      const col = i % region.columns;
      const row = Math.floor(i / region.columns);
      positions[n.id] = {
        x: region.origin.x + col * (NODE_WIDTH + COL_GAP),
        y: region.origin.y + row * (NODE_HEIGHT + ROW_GAP),
      };
      assigned.add(n.id);
    });
  }

  // Anything that didn't match a region (future node types) -- park in an
  // overflow row below everything else rather than dropping it.
  const leftover = nodes.filter((n) => !assigned.has(n.id));
  leftover.forEach((n, i) => {
    positions[n.id] = { x: i * (NODE_WIDTH + COL_GAP), y: 1160 };
  });

  return positions;
}

export const REGION_LABELS: Record<string, string> = {
  grammar: "Grammar",
  vocabulary: "Vocabulary",
  "reading-writing-skills": "Reading & Writing",
  skills: "Skills",
  activities: "Activities",
  assessment: "Assessment",
  objectives: "Learning Objectives",
  resources: "Resources",
  levels: "CEFR Levels",
};
