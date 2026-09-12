import { useMemo, useState } from "react";
import type { CefrLevel, KnowledgeNode, KnowledgeNodeType, KnowledgeRelationship, KnowledgeStatus } from "../types/knowledgeGraph.ts";

const ALL_NODE_TYPES: KnowledgeNodeType[] = ["concept", "skill", "learning_objective", "exercise", "resource", "level"];
const ALL_CEFR: CefrLevel[] = ["A1", "A2", "B1", "B2", "C1", "C2"];
const ALL_STATUSES: KnowledgeStatus[] = ["teacher_approved", "teacher_reviewed", "needs_review", "ai_generated"];
const ALL_SKILLS = ["Reading", "Writing", "Listening", "Speaking"];

export function useGraphFilters(nodes: KnowledgeNode[], relationships: KnowledgeRelationship[]) {
  const [nodeTypes, setNodeTypes] = useState<Set<KnowledgeNodeType>>(new Set(ALL_NODE_TYPES));
  const [cefr, setCefr] = useState<Set<CefrLevel>>(new Set(ALL_CEFR));
  const [skills, setSkills] = useState<Set<string>>(new Set(ALL_SKILLS));
  const [statuses, setStatuses] = useState<Set<KnowledgeStatus>>(new Set(ALL_STATUSES));
  const [searchQuery, setSearchQuery] = useState("");

  function toggle<T>(set: Set<T>, setSet: (s: Set<T>) => void, value: T) {
    const next = new Set(set);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    setSet(next);
  }

  const visibleNodeIds = useMemo(() => {
    const ids = new Set<string>();
    for (const n of nodes) {
      if (!nodeTypes.has(n.type)) continue;
      if (n.cefrLevel && !cefr.has(n.cefrLevel)) continue;
      // Level nodes (A1..C2) carry the level as their *name*, not a
      // cefrLevel field pointing at themselves -- without this they'd
      // never respond to the CEFR checkboxes at all.
      if (n.type === "level" && !cefr.has(n.name as CefrLevel)) continue;
      if (!statuses.has(n.status)) continue;
      if (n.type === "skill" && !skills.has(n.name)) continue;
      ids.add(n.id);
    }
    return ids;
  }, [nodes, nodeTypes, cefr, statuses, skills]);

  const visibleRelationshipIds = useMemo(() => {
    const ids = new Set<string>();
    for (const r of relationships) {
      if (visibleNodeIds.has(r.sourceId) && visibleNodeIds.has(r.targetId)) ids.add(r.id);
    }
    return ids;
  }, [relationships, visibleNodeIds]);

  const searchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return [];
    return nodes.filter((n) => n.name.toLowerCase().includes(q) || n.aliases?.some((a) => a.toLowerCase().includes(q))).slice(0, 8);
  }, [nodes, searchQuery]);

  return {
    nodeTypes,
    cefr,
    skills,
    statuses,
    searchQuery,
    setSearchQuery,
    toggleNodeType: (t: KnowledgeNodeType) => toggle(nodeTypes, setNodeTypes, t),
    toggleCefr: (l: CefrLevel) => toggle(cefr, setCefr, l),
    toggleSkill: (s: string) => toggle(skills, setSkills, s),
    toggleStatus: (s: KnowledgeStatus) => toggle(statuses, setStatuses, s),
    visibleNodeIds,
    visibleRelationshipIds,
    searchResults,
  };
}

export { ALL_CEFR, ALL_NODE_TYPES, ALL_SKILLS, ALL_STATUSES };
