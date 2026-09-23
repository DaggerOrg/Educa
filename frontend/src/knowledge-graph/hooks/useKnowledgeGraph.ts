import { useCallback, useEffect, useState } from "react";
import { computeLaneLayout, placeInLane, type LayoutLink } from "../utils/graphLayout.ts";
import { DEMO_GRAPH_ID, knowledgeGraphService } from "../services/knowledgeGraphService.ts";
import type { KnowledgeNode, KnowledgeRelationship } from "../types/knowledgeGraph.ts";

const toLinks = (rels: KnowledgeRelationship[]): LayoutLink[] =>
  rels.map((r) => ({ source: r.sourceId, target: r.targetId, type: r.type }));

export function useKnowledgeGraph() {
  const [nodes, setNodes] = useState<KnowledgeNode[]>([]);
  const [relationships, setRelationships] = useState<KnowledgeRelationship[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    knowledgeGraphService
      .getGraph(DEMO_GRAPH_ID)
      .then((data) => {
        if (cancelled) return;
        const positions = computeLaneLayout(data.nodes, toLinks(data.relationships));
        setNodes(data.nodes.map((n) => ({ ...n, position: n.position ?? positions[n.id] })));
        setRelationships(data.relationships);
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const addNode = useCallback(async (input: Omit<KnowledgeNode, "id">) => {
    const created = await knowledgeGraphService.createNode(DEMO_GRAPH_ID, input);
    setNodes((prev) => {
      const position = created.position ?? placeInLane(created, prev);
      return [...prev, { ...created, position }];
    });
    return created;
  }, []);

  const editNode = useCallback(async (nodeId: string, patch: Partial<KnowledgeNode>) => {
    const updated = await knowledgeGraphService.updateNode(DEMO_GRAPH_ID, nodeId, patch);
    setNodes((prev) => prev.map((n) => (n.id === nodeId ? { ...n, ...updated, position: n.position } : n)));
    return updated;
  }, []);

  const moveNode = useCallback((nodeId: string, position: { x: number; y: number }) => {
    // Pure local state -- dragging is a view concern, not something that
    // needs to round-trip through the (async) mock service.
    setNodes((prev) => prev.map((n) => (n.id === nodeId ? { ...n, position } : n)));
  }, []);

  const removeNode = useCallback(async (nodeId: string) => {
    await knowledgeGraphService.deleteNode(DEMO_GRAPH_ID, nodeId);
    setNodes((prev) => prev.filter((n) => n.id !== nodeId));
    setRelationships((prev) => prev.filter((r) => r.sourceId !== nodeId && r.targetId !== nodeId));
  }, []);

  const addRelationship = useCallback(async (input: Omit<KnowledgeRelationship, "id">) => {
    const created = await knowledgeGraphService.createRelationship(DEMO_GRAPH_ID, input);
    setRelationships((prev) => [...prev, created]);
    return created;
  }, []);

  const editRelationship = useCallback(async (relationshipId: string, patch: Partial<KnowledgeRelationship>) => {
    const updated = await knowledgeGraphService.updateRelationship(DEMO_GRAPH_ID, relationshipId, patch);
    setRelationships((prev) => prev.map((r) => (r.id === relationshipId ? updated : r)));
    return updated;
  }, []);

  const removeRelationship = useCallback(async (relationshipId: string) => {
    await knowledgeGraphService.deleteRelationship(DEMO_GRAPH_ID, relationshipId);
    setRelationships((prev) => prev.filter((r) => r.id !== relationshipId));
  }, []);

  const resetLayout = useCallback(() => {
    setNodes((prev) => {
      const positions = computeLaneLayout(prev, toLinks(relationships));
      return prev.map((n) => ({ ...n, position: positions[n.id] }));
    });
  }, [relationships]);

  return {
    nodes,
    relationships,
    loading,
    error,
    addNode,
    editNode,
    moveNode,
    removeNode,
    addRelationship,
    editRelationship,
    removeRelationship,
    resetLayout,
  };
}
