import {
  Background, Controls, MarkerType, ReactFlow, type Connection, type EdgeTypes, type NodeChange, type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useMemo, useState } from "react";
import type { GraphSelection } from "../../hooks/useGraphSelection.ts";
import type { KnowledgeNode, KnowledgeRelationship } from "../../types/knowledgeGraph.ts";
import GraphMiniMap from "./GraphMiniMap.tsx";
import InitialView from "./InitialView.tsx";
import KnowledgeEdgeLine, { EdgeFocusContext, type KnowledgeFlowEdge } from "./KnowledgeEdge.tsx";
import KnowledgeNodeCard, { NodeRoleContext, type KnowledgeFlowNode } from "./KnowledgeNode.tsx";
import LaneBands from "./LaneBands.tsx";
import { flowRoles } from "../../utils/graphLayout.ts";
import { isLinkShown, type LinkDetail } from "../../utils/linkVisibility.ts";

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
  // View-only positions (Focus mode); while set, nodes can't be dragged so nothing is saved from them.
  positionOverrides?: Record<string, { x: number; y: number }> | null;
  // "flow": only the learn-this-first arrows (plus AI-suggested edges awaiting review and the selected node's links). "all": everything.
  linkDetail?: LinkDetail;
}

export default function KnowledgeGraphCanvas({
  nodes, relationships, visibleNodeIds, visibleRelationshipIds, selection,
  onSelectNode, onSelectRelationship, onClearSelection, onMoveNode, onRequestConnect, positionOverrides, linkDetail = "all",
}: KnowledgeGraphCanvasProps) {
  // Node sizes come back from xyflow as `dimensions` changes and have to be fed back in as `measured`
  // -- otherwise the minimap (and anything else that needs sizes) sees zero-size nodes and draws nothing.
  const [measured, setMeasured] = useState<Record<string, { width: number; height: number }>>({});

  const flowNodes: KnowledgeFlowNode[] = useMemo(
    () =>
      nodes
        .filter((n) => visibleNodeIds.has(n.id))
        .map((n) => ({
          id: n.id,
          type: "knowledge",
          position: positionOverrides?.[n.id] ?? n.position ?? { x: 0, y: 0 },
          data: { node: n },
          measured: measured[n.id],
          selected: selection?.kind === "node" && selection.id === n.id,
        })),
    [nodes, visibleNodeIds, selection, positionOverrides, measured],
  );

  // Start/End come from the whole graph, not just what's currently shown.
  const roles = useMemo(
    () => flowRoles(relationships.map((r) => ({ source: r.sourceId, target: r.targetId, type: r.type }))),
    [relationships],
  );
  const bandItems = useMemo(
    () => flowNodes.map((n) => ({ type: n.data.node.type, x: n.position.x, y: n.position.y })),
    [flowNodes],
  );

  const focusIds = useMemo(() => (selection?.kind === "node" ? new Set([selection.id]) : null), [selection]);

  const flowEdges: KnowledgeFlowEdge[] = useMemo(
    () =>
      relationships
        .filter((r) => visibleRelationshipIds.has(r.id))
        .filter((r) =>
          isLinkShown(
            { type: r.type, source: r.sourceId, target: r.targetId, pendingReview: r.evidenceType === "llm_inferred" && !r.teacherApproved },
            linkDetail,
            { nodeIds: selection?.kind === "node" ? new Set([selection.id]) : new Set(), linkSelected: selection?.kind === "relationship" && selection.id === r.id },
          ),
        )
        .map((r) => ({
          id: r.id,
          type: "knowledge",
          source: r.sourceId,
          target: r.targetId,
          data: { relationship: r },
          selected: selection?.kind === "relationship" && selection.id === r.id,
          markerEnd: { type: MarkerType.ArrowClosed },
        })),
    [relationships, visibleRelationshipIds, selection, linkDetail],
  );

  const handleNodesChange = useCallback(
    (changes: NodeChange<KnowledgeFlowNode>[]) => {
      const sizes: Record<string, { width: number; height: number }> = {};
      for (const change of changes) {
        if (change.type === "dimensions" && change.dimensions) sizes[change.id] = change.dimensions;
        else if (change.type === "position" && change.position && !positionOverrides) onMoveNode(change.id, change.position);
      }
      const changed = Object.entries(sizes).filter(([id, d]) => measured[id]?.width !== d.width || measured[id]?.height !== d.height);
      if (changed.length > 0) setMeasured((prev) => ({ ...prev, ...Object.fromEntries(changed) }));
    },
    [onMoveNode, positionOverrides, measured],
  );

  const handleConnect = useCallback(
    (connection: Connection) => {
      if (connection.source && connection.target) onRequestConnect(connection.source, connection.target);
    },
    [onRequestConnect],
  );

  return (
    <div className="kg-canvas">
      <EdgeFocusContext.Provider value={focusIds}>
      <NodeRoleContext.Provider value={roles}>
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={handleNodesChange}
        nodesDraggable={!positionOverrides}
        onConnect={handleConnect}
        onNodeClick={(_, node) => onSelectNode(node.id)}
        onEdgeClick={(_, edge) => onSelectRelationship(edge.id)}
        onPaneClick={onClearSelection}
        proOptions={{ hideAttribution: true }}
        minZoom={0.2}
        maxZoom={1.6}
      >
        <InitialView top={80} />
        <Background gap={24} size={1} />
        {!positionOverrides && <LaneBands items={bandItems} />}
        <Controls showInteractive={false} />
        <GraphMiniMap />
      </ReactFlow>
      </NodeRoleContext.Provider>
      </EdgeFocusContext.Provider>
    </div>
  );
}
