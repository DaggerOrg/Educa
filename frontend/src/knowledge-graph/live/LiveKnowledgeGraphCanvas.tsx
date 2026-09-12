// The collaborative counterpart to KnowledgeGraphPage.tsx -- same visual
// canvas (same node/edge renderers, same legend), but the graph state is
// synced live across every connected teacher via Liveblocks Storage
// (@liveblocks/react-flow's `useLiveblocksFlow`) instead of the mock REST
// service. One Liveblocks room per board, named `kg-board:{board.id}` (see
// backend/app/liveblocks_auth.py's `KG_BOARD_ROOM_PATTERN`).
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Connection,
  type EdgeTypes,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  ClientSideSuspense,
  LiveblocksProvider,
  RoomProvider,
  useHistory,
  useOthers,
} from "@liveblocks/react/suspense";
import { Cursors, useLiveblocksFlow } from "@liveblocks/react-flow";
import "@liveblocks/react-ui/styles.css";
import "@liveblocks/react-flow/styles.css";
import "../../liveblocks.config.ts";
import { useState } from "react";
import { API_BASE } from "../../api.ts";
import type { Session } from "../../auth.ts";
import type { KgBoard } from "../../types.ts";
import { IconPlus } from "../../components/icons.tsx";
import KnowledgeEdgeLine, { type KnowledgeFlowEdge } from "../components/KnowledgeEdge.tsx";
import KnowledgeNodeCard, { type KnowledgeFlowNode } from "../components/KnowledgeNode.tsx";
import GraphLegend from "../components/GraphLegend.tsx";
import {
  NODE_TYPE_LABELS,
  RELATIONSHIP_LABELS,
  type KnowledgeNode,
  type KnowledgeNodeType,
  type KnowledgeRelationship,
  type KnowledgeRelationshipType,
} from "../types/knowledgeGraph.ts";

const nodeTypes: NodeTypes = { knowledge: KnowledgeNodeCard };
const edgeTypes: EdgeTypes = { knowledge: KnowledgeEdgeLine };

const ADD_MENU_TYPES: KnowledgeNodeType[] = [
  "concept", "skill", "learning_objective", "exercise", "resource", "level",
];

const RELATIONSHIP_MENU_TYPES: KnowledgeRelationshipType[] = [
  "prerequisite_of", "part_of", "teaches", "practices", "assesses", "reinforces",
];

interface LiveKnowledgeGraphCanvasProps {
  session: Session;
  board: KgBoard;
}

export default function LiveKnowledgeGraphCanvas({ session, board }: LiveKnowledgeGraphCanvasProps) {
  const roomId = `kg-board:${board.id}`;

  return (
    <LiveblocksProvider
      authEndpoint={async () => {
        const res = await fetch(`${API_BASE}/liveblocks-auth`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` },
          body: JSON.stringify({ room: roomId }),
        });
        if (!res.ok) throw new Error("Couldn't authorize the collaborative graph connection");
        return await res.json();
      }}
    >
      <RoomProvider id={roomId}>
        <ClientSideSuspense fallback={<div className="kg-page"><div className="empty-panel">Connecting…</div></div>}>
          <ReactFlowProvider>
            <LiveGraphInner title={board.title} />
          </ReactFlowProvider>
        </ClientSideSuspense>
      </RoomProvider>
    </LiveblocksProvider>
  );
}

type PendingConnection = { connection: Connection; screenX: number; screenY: number };

function LiveGraphInner({ title }: { title: string }) {
  const reactFlow = useReactFlow<KnowledgeFlowNode, KnowledgeFlowEdge>();
  const others = useOthers();
  const history = useHistory();
  const [addMenuOpen, setAddMenuOpen] = useState(false);
  const [pendingConnection, setPendingConnection] = useState<PendingConnection | null>(null);

  const { nodes, edges, onNodesChange, onEdgesChange, onDelete } = useLiveblocksFlow<
    KnowledgeFlowNode,
    KnowledgeFlowEdge
  >({ suspense: true });

  function addNode(type: KnowledgeNodeType) {
    setAddMenuOpen(false);
    const name = window.prompt(`Name this ${NODE_TYPE_LABELS[type].toLowerCase()}`, "");
    if (!name) return;
    const id = crypto.randomUUID();
    const node: KnowledgeNode = { id, type, name, status: "teacher_approved" };
    const center = reactFlow.screenToFlowPosition({
      x: window.innerWidth / 2,
      y: window.innerHeight / 2 + (Math.random() - 0.5) * 120,
    });
    onNodesChange([
      { type: "add", item: { id, type: "knowledge", position: center, data: { node }, selected: true } },
    ]);
  }

  function renameNode(node: KnowledgeFlowNode) {
    const name = window.prompt("Rename node", node.data.node.name);
    if (!name || name === node.data.node.name) return;
    onNodesChange([
      { type: "replace", id: node.id, item: { ...node, data: { node: { ...node.data.node, name } } } },
    ]);
  }

  function handleConnect(connection: Connection) {
    // Position the relationship-type picker at the target node's on-screen
    // location -- `onConnect` gives us the connection, not the pointer event.
    const targetNode = connection.target ? reactFlow.getNode(connection.target) : undefined;
    const screen = targetNode
      ? reactFlow.flowToScreenPosition(targetNode.position)
      : { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    setPendingConnection({ connection, screenX: screen.x, screenY: screen.y });
  }

  function completeConnection(type: KnowledgeRelationshipType) {
    if (!pendingConnection) return;
    const { source, target } = pendingConnection.connection;
    if (source && target) {
      const relationship: KnowledgeRelationship = {
        id: crypto.randomUUID(),
        sourceId: source,
        targetId: target,
        type,
        evidenceType: "teacher_created",
        teacherApproved: true,
      };
      onEdgesChange([
        {
          type: "add",
          item: {
            id: relationship.id,
            type: "knowledge",
            source,
            target,
            data: { relationship },
            markerEnd: { type: MarkerType.ArrowClosed },
          },
        },
      ]);
    }
    setPendingConnection(null);
  }

  return (
    <div className="kg-page">
      <div className="kg-header">
        <div className="kg-breadcrumb">
          Knowledge Graph <span>/</span> Live <span>/</span> {title}
        </div>
        <div className="kg-live-presence" title={`${others.length + 1} here now`}>
          {others.length + 1} online
        </div>
        <div className="kg-toolbar">
          <button type="button" className="kg-toolbar-btn" onClick={() => history.undo()} title="Undo">
            Undo
          </button>
          <button type="button" className="kg-toolbar-btn" onClick={() => history.redo()} title="Redo">
            Redo
          </button>
        </div>
        <div className="kg-add-menu">
          <button type="button" className="btn btn-primary" onClick={() => setAddMenuOpen((v) => !v)}>
            <IconPlus /> Add
          </button>
          {addMenuOpen && (
            <div className="kg-add-menu-list">
              {ADD_MENU_TYPES.map((t) => (
                <button type="button" key={t} className="kg-add-menu-item" onClick={() => addNode(t)}>
                  Add {NODE_TYPE_LABELS[t]}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="kg-body">
        <aside className="kg-left">
          <GraphLegend />
        </aside>

        <div className="kg-canvas-wrap">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={handleConnect}
            onDelete={onDelete}
            onNodeDoubleClick={(_, node) => renameNode(node)}
            deleteKeyCode={["Backspace", "Delete"]}
            proOptions={{ hideAttribution: true }}
            minZoom={0.2}
            maxZoom={1.6}
            fitView
          >
            <Background gap={24} size={1} />
            <Controls showInteractive={false} />
            <Cursors />
          </ReactFlow>

          {pendingConnection && (
            <div
              className="kg-relationship-picker"
              style={{ left: pendingConnection.screenX, top: pendingConnection.screenY }}
            >
              <div className="kg-relationship-picker-label">Relationship type</div>
              {RELATIONSHIP_MENU_TYPES.map((t) => (
                <button type="button" key={t} className="kg-add-menu-item" onClick={() => completeConnection(t)}>
                  {RELATIONSHIP_LABELS[t]}
                </button>
              ))}
              <button
                type="button"
                className="kg-add-menu-item kg-relationship-picker-cancel"
                onClick={() => setPendingConnection(null)}
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
