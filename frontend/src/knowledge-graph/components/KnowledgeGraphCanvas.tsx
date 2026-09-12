import {
  Background, Controls, MarkerType, ReactFlow, type Connection, type EdgeTypes, type NodeChange, type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useMemo } from "react";
import type { GraphSelection } from "../hooks/useGraphSelection.ts";
import type { KnowledgeNode, KnowledgeRelationship } from "../types/knowledgeGraph.ts";
import KnowledgeEdgeLine, { type KnowledgeFlowEdge } from "./KnowledgeEdge.tsx";
import KnowledgeNodeCard, { type KnowledgeFlowNode } from "./KnowledgeNode.tsx";

const nodeTypes: NodeTypes = { knowledge: KnowledgeNodeCard };
const edgeTypes: EdgeTypes = { knowledge: KnowledgeEdgeLine };

interface KnowledgeGraphCanvasProps {
  nodes: KnowledgeNode[];
  relationships: KnowledgeRelationship[];
  visibleNodeIds: Set<string>;
  visibleRelationshipIds: Set<string>;
  selection: GraphSelection;
  onSelectNode: (id: string) => void;
  onSelectRelationship: (id: string) => void;
  onClearSelection: () => void;
  onMoveNode: (id: string, position: { x: number; y: number }) => void;
  onRequestConnect: (sourceId: string, targetId: string) => void;
}

export default function KnowledgeGraphCanvas({
  nodes, relationships, visibleNodeIds, visibleRelationshipIds, selection,
  onSelectNode, onSelectRelationship, onClearSelection, onMoveNode, onRequestConnect,
}: KnowledgeGraphCanvasProps) {
  const flowNodes: KnowledgeFlowNode[] = useMemo(
    () =>
      nodes
        .filter((n) => visibleNodeIds.has(n.id))
        .map((n) => ({
          id: n.id,
          type: "knowledge",
          position: n.position ?? { x: 0, y: 0 },
          data: { node: n },
          selected: selection?.kind === "node" && selection.id === n.id,
        })),
    [nodes, visibleNodeIds, selection],
  );

  const flowEdges: KnowledgeFlowEdge[] = useMemo(
    () =>
      relationships
        .filter((r) => visibleRelationshipIds.has(r.id))
        .map((r) => ({
          id: r.id,
          type: "knowledge",
          source: r.sourceId,
          target: r.targetId,
          data: { relationship: r },
          selected: selection?.kind === "relationship" && selection.id === r.id,
          markerEnd: { type: MarkerType.ArrowClosed },
        })),
    [relationships, visibleRelationshipIds, selection],
  );

  const handleNodesChange = useCallback(
    (changes: NodeChange<KnowledgeFlowNode>[]) => {
      for (const change of changes) {
        if (change.type === "position" && change.position) {
          onMoveNode(change.id, change.position);
        }
      }
    },
    [onMoveNode],
  );

  const handleConnect = useCallback(
    (connection: Connection) => {
      if (connection.source && connection.target) onRequestConnect(connection.source, connection.target);
    },
    [onRequestConnect],
  );

  return (
    <div className="kg-canvas">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={handleNodesChange}
        onConnect={handleConnect}
        onNodeClick={(_, node) => onSelectNode(node.id)}
        onEdgeClick={(_, edge) => onSelectRelationship(edge.id)}
        onPaneClick={onClearSelection}
        proOptions={{ hideAttribution: true }}
        minZoom={0.2}
        maxZoom={1.6}
        fitView
      >
        <Background gap={24} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
