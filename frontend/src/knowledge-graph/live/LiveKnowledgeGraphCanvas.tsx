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
  useStore,
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
import { useMemo, useState } from "react";
import { API_BASE } from "../../api.ts";
import type { Session } from "../../auth.ts";
import type { KgBoard } from "../../types.ts";
import { IconPlus } from "../../components/icons.tsx";
import TextPromptDialog from "../components/dialogs/TextPromptDialog.tsx";
import KnowledgeEdgeLine, { EdgeFocusContext, type KnowledgeFlowEdge } from "../components/canvas/KnowledgeEdge.tsx";
import KnowledgeNodeCard, { NodeRoleContext, type KnowledgeFlowNode } from "../components/canvas/KnowledgeNode.tsx";
import LaneBands from "../components/canvas/LaneBands.tsx";
import FocusFit from "../components/canvas/FocusFit.tsx";
import GraphMiniMap from "../components/canvas/GraphMiniMap.tsx";
import InitialView from "../components/canvas/InitialView.tsx";
import GraphLegend from "../components/panels/GraphLegend.tsx";
import ViewSwitch from "../components/panels/ViewSwitch.tsx";
import LearningPathView from "../components/path/LearningPathView.tsx";
import StageChrome, { FocusNote, type GraphVariant } from "../components/canvas/StageChrome.tsx";
import {
  NODE_TYPE_LABELS,
  RELATIONSHIP_LABELS,
  type KnowledgeNode,
  type KnowledgeNodeType,
  type KnowledgeRelationship,
  type KnowledgeRelationshipType,
} from "../types/knowledgeGraph.ts";
import { useFocusView } from "../hooks/useFocusView.ts";
import { useGraphView } from "../hooks/useGraphView.ts";
import { computeLaneLayout, flowRoles, placeInLane, type LayoutLink } from "../utils/graphLayout.ts";
import { isLinkShown, type LinkDetail } from "../utils/linkVisibility.ts";
import { viewportFor } from "../utils/viewport.ts";

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
  // Boards don't carry an official/draft status yet, so callers omit this
  // and every board renders as the official look.
  variant?: GraphVariant;
}

export default function LiveKnowledgeGraphCanvas({ session, board, variant = "official" }: LiveKnowledgeGraphCanvasProps) {
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
            <LiveGraphInner title={board.title} variant={variant} />
          </ReactFlowProvider>
        </ClientSideSuspense>
      </RoomProvider>
    </LiveblocksProvider>
  );
}

type NameDialog = { mode: "add"; type: KnowledgeNodeType } | { mode: "rename"; node: KnowledgeFlowNode } | null;

type PendingConnection = { connection: Connection; screenX: number; screenY: number };

function LiveGraphInner({ title, variant }: { title: string; variant: GraphVariant }) {
  const reactFlow = useReactFlow<KnowledgeFlowNode, KnowledgeFlowEdge>();
  const others = useOthers();
  const history = useHistory();
  const [addMenuOpen, setAddMenuOpen] = useState(false);
  const [nameDialog, setNameDialog] = useState<NameDialog>(null);
  const [showLabels, setShowLabels] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const [linkDetail, setLinkDetail] = useState<LinkDetail>("flow");
  const [pendingConnection, setPendingConnection] = useState<PendingConnection | null>(null);
  const [view, setView] = useGraphView();
  // The Path view keeps its own highlight: selection on the canvas belongs to the canvas.
  const [pathSelectedId, setPathSelectedId] = useState<string | null>(null);

  const { nodes, edges, onNodesChange, onEdgesChange, onDelete } = useLiveblocksFlow<
    KnowledgeFlowNode,
    KnowledgeFlowEdge
  >({ suspense: true });

  const focusIds = useMemo(() => new Set(nodes.filter((n) => n.selected).map((n) => n.id)), [nodes]);

  // Start/End come from the whole board; lane bands from where the cards actually are.
  const links = useMemo<LayoutLink[]>(
    () => edges.map((e) => ({ source: e.source, target: e.target, type: e.data?.relationship?.type ?? "" })),
    [edges],
  );
  const roles = useMemo(() => flowRoles(links), [links]);
  const bandItems = useMemo(
    () => nodes.map((n) => ({ type: n.data.node.type, x: n.position.x, y: n.position.y })),
    [nodes],
  );
  const pathNodes = useMemo(() => nodes.map((n) => n.data.node), [nodes]);
  const pathRelationships = useMemo(
    () => edges.flatMap((e) => (e.data?.relationship ? [{ ...e.data.relationship, sourceId: e.source, targetId: e.target }] : [])),
    [edges],
  );
  const canvasWidth = useStore((s) => s.width);
  const canvasHeight = useStore((s) => s.height);

  // Re-runs the lane layout and writes the new positions to the shared board (everyone sees it; Undo reverts it).
  function tidy() {
    const positions = computeLaneLayout(nodes.map((n) => ({ id: n.id, type: n.data.node.type, name: n.data.node.name })), links);
    onNodesChange(nodes.map((n) => ({ type: "position" as const, id: n.id, position: positions[n.id] })));
    if (canvasWidth > 0) {
      void reactFlow.setViewport(
        viewportFor(Object.values(positions), { width: canvasWidth, height: canvasHeight }, { top: 56, minZoom: 0.75 }),
        { duration: 300 },
      );
    }
  }

  // Focus mode: with exactly one node selected, show only it, what leads into
  // it and what it leads to. Nodes are hidden and re-placed for display only
  // (never written to the shared board), and dragging is off while it's on.
  const graphLinks = useMemo(() => edges.map((e) => ({ id: e.id, source: e.source, target: e.target })), [edges]);
  const focusView = useFocusView(focusMode && focusIds.size === 1 ? [...focusIds][0] : null, graphLinks);
  const shownNodes = useMemo(
    () =>
      focusView
        ? nodes.map((n) => ({ ...n, hidden: !focusView.nodeIds.has(n.id), position: focusView.positions[n.id] ?? n.position }))
        : nodes,
    [nodes, focusView],
  );
  const shownEdges = useMemo(() => {
    if (focusView) return edges.map((e) => ({ ...e, hidden: !focusView.edgeIds.has(e.id) }));
    if (linkDetail === "all") return edges;
    return edges.map((e) => {
      const r = e.data?.relationship;
      const shown = isLinkShown(
        { type: r?.type ?? "", source: e.source, target: e.target, pendingReview: r?.evidenceType === "llm_inferred" && !r.teacherApproved },
        linkDetail,
        { nodeIds: focusIds, linkSelected: !!e.selected },
      );
      return shown ? e : { ...e, hidden: true };
    });
  }, [edges, focusView, linkDetail, focusIds]);
  const framePositions = useMemo(
    () => (focusView ? Object.values(focusView.positions) : nodes.map((n) => n.position)),
    [focusView, nodes],
  );

  function createNode(type: KnowledgeNodeType, name: string) {
    const id = crypto.randomUUID();
    const node: KnowledgeNode = { id, type, name, status: "teacher_approved" };
    // With no canvas on screen there is no "middle of the view": go where the tidy layout would put it.
    const center = view === "path"
      ? placeInLane({ id, type, name }, nodes.map((n) => ({ id: n.id, type: n.data.node.type, name: n.data.node.name, position: n.position })))
      : reactFlow.screenToFlowPosition({
          x: window.innerWidth / 2,
          y: window.innerHeight / 2 + (Math.random() - 0.5) * 120,
        });
    setPathSelectedId(id);
    onNodesChange([
      { type: "add", item: { id, type: "knowledge", position: center, data: { node }, selected: true } },
    ]);
  }

  function renameNode(node: KnowledgeFlowNode, name: string) {
    if (name === node.data.node.name) return;
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
        <ViewSwitch view={view} onChange={setView} />
        <div className="kg-toolbar">
          <button type="button" className="btn kg-toolbar-btn" onClick={() => history.undo()} title="Undo">
            Undo
          </button>
          <button type="button" className="btn kg-toolbar-btn" onClick={() => history.redo()} title="Redo">
            Redo
          </button>
          {view === "graph" && (
            <>
          <button
            type="button"
            className={`btn kg-toolbar-btn${linkDetail === "all" ? " is-active" : ""}`}
            onClick={() => setLinkDetail((d) => (d === "flow" ? "all" : "flow"))}
            title={linkDetail === "flow" ? "Showing the learn-this-first path (and the links of the selected node). Click to show every link." : "Showing every link. Click to show only the learn-this-first path."}
          >
            Links: {linkDetail === "flow" ? "Flow" : "All"}
          </button>
          <button type="button" className="btn kg-toolbar-btn" onClick={tidy} title="Arrange the cards into lanes by type, left to right">
            Tidy
          </button>
          <button
            type="button"
            className={`btn kg-toolbar-btn${focusMode ? " is-active" : ""}`}
            onClick={() => setFocusMode((v) => !v)}
            title={focusMode ? "Show the whole graph" : "Show only the selected node and its connections"}
          >
            Focus: {focusMode ? "On" : "Off"}
          </button>
          <button
            type="button"
            className={`btn kg-toolbar-btn${showLabels ? " is-active" : ""}`}
            onClick={() => setShowLabels((v) => !v)}
            title={showLabels ? "Hide relationship labels" : "Show relationship labels"}
          >
            Labels: {showLabels ? "On" : "Off"}
          </button>
            </>
          )}
        </div>
        <div className="kg-add-menu">
          <button type="button" className="btn btn-primary" onClick={() => setAddMenuOpen((v) => !v)}>
            <IconPlus /> Add
          </button>
          {addMenuOpen && (
            <div className="kg-add-menu-list">
              {ADD_MENU_TYPES.map((t) => (
                <button type="button" key={t} className="kg-add-menu-item" onClick={() => {
                    setAddMenuOpen(false);
                    setNameDialog({ mode: "add", type: t });
                  }}>
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

        {view === "path" ? (
          <LearningPathView nodes={pathNodes} relationships={pathRelationships} selectedId={pathSelectedId} onSelectNode={setPathSelectedId} />
        ) : (
          <div className={`kg-canvas-wrap kg-stage kg-stage-${variant}${showLabels ? "" : " kg-labels-hidden"}${focusView ? " kg-focus-on" : ""}`}>
            {focusMode && !focusView && <FocusNote />}
            <StageChrome variant={variant} hint="Double-click to rename · Drag handles to connect · Delete to remove" />
            <EdgeFocusContext.Provider value={focusIds}>
            <NodeRoleContext.Provider value={roles}>
            <ReactFlow
              nodes={shownNodes}
              edges={shownEdges}
              nodesDraggable={!focusView}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={handleConnect}
              onDelete={onDelete}
              onNodeDoubleClick={(_, node) => setNameDialog({ mode: "rename", node })}
              deleteKeyCode={["Backspace", "Delete"]}
              proOptions={{ hideAttribution: true }}
              minZoom={0.2}
              maxZoom={1.6}
            >
              <InitialView top={56} />
              <FocusFit frameKey={focusView ? `focus:${focusView.centerId}` : "all"} positions={framePositions} top={56} minZoom={focusView ? 0.4 : 0.75} />
              <Background gap={24} size={1} />
              {!focusView && <LaneBands items={bandItems} />}
              <Controls showInteractive={false} />
              <GraphMiniMap />
              <Cursors />
            </ReactFlow>
            </NodeRoleContext.Provider>
            </EdgeFocusContext.Provider>

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
        )}
      </div>

      {nameDialog && (
        <TextPromptDialog
          title={nameDialog.mode === "add" ? `New ${NODE_TYPE_LABELS[nameDialog.type].toLowerCase()}` : "Rename node"}
          label="Name"
          initialValue={nameDialog.mode === "rename" ? nameDialog.node.data.node.name : ""}
          submitLabel={nameDialog.mode === "add" ? "Add" : "Rename"}
          onCancel={() => setNameDialog(null)}
          onSubmit={(name) => {
            if (nameDialog.mode === "add") createNode(nameDialog.type, name);
            else renameNode(nameDialog.node, name);
            setNameDialog(null);
          }}
        />
      )}
    </div>
  );
}
