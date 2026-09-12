// Data/service boundary for the Knowledge Graph editor. Components call
// only the functions re-exported here -- never a mock/API implementation
// directly -- so swapping `mockKnowledgeGraphService` for a real
// `fetch`-based `apiKnowledgeGraphService` against a future
// `GET/POST /api/knowledge-graphs/:id` backend is a one-line change below,
// with no call-site updates anywhere in the app.
import { mockKnowledgeGraphService } from "./mockKnowledgeGraphService.ts";
import type { KnowledgeGraphData, KnowledgeNode, KnowledgeRelationship } from "../types/knowledgeGraph.ts";

export interface KnowledgeGraphService {
  getGraph(graphId: string): Promise<KnowledgeGraphData>;
  createNode(graphId: string, node: Omit<KnowledgeNode, "id">): Promise<KnowledgeNode>;
  updateNode(graphId: string, nodeId: string, patch: Partial<KnowledgeNode>): Promise<KnowledgeNode>;
  deleteNode(graphId: string, nodeId: string): Promise<void>;
  createRelationship(graphId: string, relationship: Omit<KnowledgeRelationship, "id">): Promise<KnowledgeRelationship>;
  updateRelationship(graphId: string, relationshipId: string, patch: Partial<KnowledgeRelationship>): Promise<KnowledgeRelationship>;
  deleteRelationship(graphId: string, relationshipId: string): Promise<void>;
}

// The swap point: point this at apiKnowledgeGraphService once the
// ingestion pipeline + Neo4j + backend endpoints exist.
export const knowledgeGraphService: KnowledgeGraphService = mockKnowledgeGraphService;

export const DEMO_GRAPH_ID = "english-b1-curriculum";
