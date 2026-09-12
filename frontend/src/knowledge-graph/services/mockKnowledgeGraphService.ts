// Mock implementation of KnowledgeGraphService -- an in-memory store
// seeded from the demo dataset. Lives for the life of the page load only
// (no localStorage), so a refresh naturally re-seeds from
// englishKnowledgeGraph rather than keeping edits around.
import { englishKnowledgeGraph } from "../data/englishKnowledgeGraph.ts";
import type { KnowledgeGraphData, KnowledgeNode, KnowledgeRelationship } from "../types/knowledgeGraph.ts";
import type { KnowledgeGraphService } from "./knowledgeGraphService.ts";

let idCounter = 1000;
function nextId(prefix: string) {
  idCounter += 1;
  return `${prefix}-${idCounter}`;
}

// A fresh deep copy per seed, so editing the returned graph never mutates
// the module-level mock dataset.
function cloneGraph(): KnowledgeGraphData {
  return {
    nodes: englishKnowledgeGraph.nodes.map((n) => ({ ...n })),
    relationships: englishKnowledgeGraph.relationships.map((r) => ({ ...r })),
  };
}

let store: KnowledgeGraphData | null = null;
function getStore(): KnowledgeGraphData {
  if (!store) store = cloneGraph();
  return store;
}

export const mockKnowledgeGraphService: KnowledgeGraphService = {
  async getGraph() {
    const { nodes, relationships } = getStore();
    return { nodes: nodes.map((n) => ({ ...n })), relationships: relationships.map((r) => ({ ...r })) };
  },

  async createNode(_graphId, node) {
    const created: KnowledgeNode = { ...node, id: nextId(node.type), createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() };
    getStore().nodes.push(created);
    return { ...created };
  },

  async updateNode(_graphId, nodeId, patch) {
    const s = getStore();
    const existing = s.nodes.find((n) => n.id === nodeId);
    if (!existing) throw new Error(`No node with id ${nodeId}`);
    Object.assign(existing, patch, { updatedAt: new Date().toISOString() });
    return { ...existing };
  },

  async deleteNode(_graphId, nodeId) {
    const s = getStore();
    s.nodes = s.nodes.filter((n) => n.id !== nodeId);
    // A node's relationships go with it -- an edge can't dangle off a deleted node.
    s.relationships = s.relationships.filter((r) => r.sourceId !== nodeId && r.targetId !== nodeId);
  },

  async createRelationship(_graphId, relationship) {
    const created: KnowledgeRelationship = { ...relationship, id: nextId("rel") };
    getStore().relationships.push(created);
    return { ...created };
  },

  async updateRelationship(_graphId, relationshipId, patch) {
    const s = getStore();
    const existing = s.relationships.find((r) => r.id === relationshipId);
    if (!existing) throw new Error(`No relationship with id ${relationshipId}`);
    Object.assign(existing, patch);
    return { ...existing };
  },

  async deleteRelationship(_graphId, relationshipId) {
    const s = getStore();
    s.relationships = s.relationships.filter((r) => r.id !== relationshipId);
  },
};
