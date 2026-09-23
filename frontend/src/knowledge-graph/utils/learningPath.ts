import type { CefrLevel, KnowledgeNode, KnowledgeNodeType, KnowledgeRelationship } from "../types/knowledgeGraph.ts";
import { flowRoles, prerequisiteDepths, type LayoutLink } from "./graphLayout.ts";

// The Path view: the graph read as a list, from the basics to the advanced.
//
// What gets a place on the path is what a learner learns -- concepts and
// learning objectives. Skills, exercises and resources hang off the topics
// they belong to instead of taking a place of their own, and level nodes
// (A1..C2) are not shown at all because a topic's own level says the same.
//
// The steps are levels (A1..C2) when the graph has them; a topic without one
// takes the level of what it builds on, or failing that, of what builds on it.
// A graph with no levels at all is ordered by its "learn this first" arrows
// instead: step 1 is everything with nothing before it.

export type PathRole = "start" | "end";

export interface PathItem {
  node: KnowledgeNode;
  // What to learn first (its prerequisites), by name.
  after: KnowledgeNode[];
  // Skills, exercises and resources connected to this topic.
  support: KnowledgeNode[];
  role?: PathRole;
}

export interface PathSection {
  // "stage" sections form the basics-to-advanced sequence; the other two sit beyond its advanced end.
  kind: "stage" | "unleveled" | "other";
  key: string;
  // Short text for the marker on the path: "A1", "1", "?".
  badge: string;
  label: string;
  caption: string;
  items: PathItem[];
}

export interface LearningPath {
  grouping: "level" | "step";
  sections: PathSection[];
}

const CEFR: CefrLevel[] = ["A1", "A2", "B1", "B2", "C1", "C2"];
const CEFR_CAPTION: Record<CefrLevel, string> = {
  A1: "Beginner",
  A2: "Elementary",
  B1: "Intermediate",
  B2: "Upper intermediate",
  C1: "Advanced",
  C2: "Proficient",
};

const PATH_TYPES: ReadonlySet<KnowledgeNodeType> = new Set(["concept", "learning_objective"]);
const SUPPORT_ORDER: KnowledgeNodeType[] = ["skill", "exercise", "resource"];

const byName = (a: KnowledgeNode, b: KnowledgeNode) => a.name.localeCompare(b.name);
const bySupportOrder = (a: KnowledgeNode, b: KnowledgeNode) =>
  SUPPORT_ORDER.indexOf(a.type) - SUPPORT_ORDER.indexOf(b.type) || byName(a, b);

export function buildLearningPath(nodes: KnowledgeNode[], relationships: KnowledgeRelationship[]): LearningPath {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const rels = relationships.filter((r) => r.sourceId !== r.targetId && byId.has(r.sourceId) && byId.has(r.targetId));

  // A graph with no concepts or objectives still gets a path, made of whatever it has.
  const shown = nodes.filter((n) => n.type !== "level");
  const hasPathTypes = shown.some((n) => PATH_TYPES.has(n.type));
  const main = shown.filter((n) => !hasPathTypes || PATH_TYPES.has(n.type));
  const mainIds = new Set(main.map((n) => n.id));

  const prerequisites: LayoutLink[] = rels
    .filter((r) => r.type === "prerequisite_of" && mainIds.has(r.sourceId) && mainIds.has(r.targetId))
    .map((r) => ({ source: r.sourceId, target: r.targetId, type: r.type }));
  const depth = prerequisiteDepths(prerequisites);
  const depthOf = (id: string) => depth.get(id) ?? 0;

  const roles = flowRoles(rels.map((r) => ({ source: r.sourceId, target: r.targetId, type: r.type })));

  const before = new Map<string, string[]>();
  const beyond = new Map<string, string[]>();
  for (const l of prerequisites) {
    before.set(l.target, [...(before.get(l.target) ?? []), l.source]);
    beyond.set(l.source, [...(beyond.get(l.source) ?? []), l.target]);
  }

  const support = new Map<string, Map<string, KnowledgeNode>>();
  const attached = new Set<string>();
  if (hasPathTypes) {
    for (const r of rels) {
      const pairs: [string, string][] = [[r.sourceId, r.targetId], [r.targetId, r.sourceId]];
      for (const [topicId, otherId] of pairs) {
        const other = byId.get(otherId)!;
        if (!mainIds.has(topicId) || mainIds.has(otherId) || other.type === "level") continue;
        support.set(topicId, (support.get(topicId) ?? new Map()).set(otherId, other));
        attached.add(otherId);
      }
    }
  }

  const itemFor = (node: KnowledgeNode): PathItem => ({
    node,
    after: (before.get(node.id) ?? []).map((id) => byId.get(id)!).sort(byName),
    support: [...(support.get(node.id)?.values() ?? [])].sort(bySupportOrder),
    role: roles.get(node.id),
  });
  const inOrder = (group: KnowledgeNode[]) => [...group].sort((a, b) => depthOf(a.id) - depthOf(b.id) || byName(a, b)).map(itemFor);

  // Stage sections ---------------------------------------------------------
  const levelOf = new Map<string, number>();
  for (const n of main) if (n.cefrLevel && CEFR.includes(n.cefrLevel)) levelOf.set(n.id, CEFR.indexOf(n.cefrLevel));
  const grouping: LearningPath["grouping"] = levelOf.size > 0 ? "level" : "step";

  const sections: PathSection[] = [];
  const unleveled: KnowledgeNode[] = [];

  if (grouping === "level") {
    // Builds-on first (take the highest level among what it builds on), then what builds on it (the lowest).
    const fill = (from: Map<string, string[]>, pick: (levels: number[]) => number) => {
      let filled = false;
      for (const n of main) {
        if (levelOf.has(n.id)) continue;
        const known = (from.get(n.id) ?? []).filter((id) => levelOf.has(id)).map((id) => levelOf.get(id)!);
        if (known.length > 0) {
          levelOf.set(n.id, pick(known));
          filled = true;
        }
      }
      return filled;
    };
    let filled = true;
    while (filled) filled = fill(before, (l) => Math.max(...l)) || fill(beyond, (l) => Math.min(...l));

    for (const [index, level] of CEFR.entries()) {
      const group = main.filter((n) => levelOf.get(n.id) === index);
      if (group.length === 0) continue;
      sections.push({ kind: "stage", key: level, badge: level, label: `Level ${level}`, caption: CEFR_CAPTION[level], items: inOrder(group) });
    }
    unleveled.push(...main.filter((n) => !levelOf.has(n.id)));
  } else {
    const steps = [...new Set(main.map((n) => depthOf(n.id)))].sort((a, b) => a - b);
    for (const [index, step] of steps.entries()) {
      const group = main.filter((n) => depthOf(n.id) === step);
      const number = index + 1;
      sections.push({
        kind: "stage",
        key: `step-${number}`,
        badge: String(number),
        label: `Step ${number}`,
        caption: number === 1 ? "Nothing needed first" : "Builds on the steps before",
        items: inOrder(group),
      });
    }
  }

  if (unleveled.length > 0) {
    sections.push({ kind: "unleveled", key: "unleveled", badge: "?", label: "No level yet", caption: "Set a level to place these on the path", items: inOrder(unleveled) });
  }

  // Supporting items that connect to no topic have nowhere on the path to hang.
  const other = hasPathTypes ? shown.filter((n) => !mainIds.has(n.id) && !attached.has(n.id)).sort(bySupportOrder) : [];
  if (other.length > 0) {
    sections.push({
      kind: "other",
      key: "other",
      badge: "•",
      label: "Not tied to a topic",
      caption: "Skills, exercises and resources with no topic yet",
      items: other.map((node) => ({ node, after: [], support: [], role: undefined })),
    });
  }

  return { grouping, sections };
}
