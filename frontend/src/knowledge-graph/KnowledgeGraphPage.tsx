import { ReactFlowProvider, useReactFlow } from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";
import "./styles/knowledge-graph.css";
import { IconPlus } from "../components/icons.tsx";
import FocusFit from "./components/canvas/FocusFit.tsx";
import GraphFilters from "./components/panels/GraphFilters.tsx";
import GraphLegend from "./components/panels/GraphLegend.tsx";
import GraphSearch from "./components/panels/GraphSearch.tsx";
import GraphToolbar from "./components/panels/GraphToolbar.tsx";
import ViewSwitch from "./components/panels/ViewSwitch.tsx";
import LearningPathView from "./components/path/LearningPathView.tsx";
import KnowledgeGraphCanvas from "./components/canvas/KnowledgeGraphCanvas.tsx";
import { FocusNote } from "./components/canvas/StageChrome.tsx";
import NodeInspector from "./components/inspector/NodeInspector.tsx";
import EdgeInspector from "./components/inspector/EdgeInspector.tsx";
import NodeForm from "./components/dialogs/NodeForm.tsx";
import RelationshipForm from "./components/dialogs/RelationshipForm.tsx";
import DeleteConfirmationDialog from "./components/dialogs/DeleteConfirmationDialog.tsx";
import { useGraphFilters } from "./hooks/useGraphFilters.ts";
import { useGraphSelection } from "./hooks/useGraphSelection.ts";
import { useFocusView } from "./hooks/useFocusView.ts";
import { useGraphView } from "./hooks/useGraphView.ts";
import { useKnowledgeGraph } from "./hooks/useKnowledgeGraph.ts";
import type { LinkDetail } from "./utils/linkVisibility.ts";
import { NODE_TYPE_LABELS, type KnowledgeNode, type KnowledgeNodeType, type KnowledgeRelationship } from "./types/knowledgeGraph.ts";

const ADD_MENU_TYPES: KnowledgeNodeType[] = ["concept", "exercise", "learning_objective", "resource"];

type NodeFormState = { mode: "add"; initialType: KnowledgeNodeType } | { mode: "edit"; nodeId: string } | null;
type RelationshipFormState =
  | { mode: "create"; sourceId: string; targetId: string }
  | { mode: "edit"; relationshipId: string }
  | null;
type DeleteState = { kind: "node" | "relationship"; id: string; label: string } | null;

export default function KnowledgeGraphPage() {
  const {
    nodes, relationships, loading, error,
    addNode, editNode, moveNode, removeNode,
    addRelationship, editRelationship, removeRelationship, resetLayout,
  } = useKnowledgeGraph();

  const { selection, selectNode, selectRelationship, clearSelection } = useGraphSelection();
  const filters = useGraphFilters(nodes, relationships);
  const [view, setView] = useGraphView();

  const [addMenuOpen, setAddMenuOpen] = useState(false);
  const [nodeFormState, setNodeFormState] = useState<NodeFormState>(null);
  const [relationshipFormState, setRelationshipFormState] = useState<RelationshipFormState>(null);
  const [deleteState, setDeleteState] = useState<DeleteState>(null);
  const [showLabels, setShowLabels] = useState(false);
  const [focusNodeId, setFocusNodeId] = useState<string | null>(null);
  const [focusMode, setFocusMode] = useState(false);
  const [linkDetail, setLinkDetail] = useState<LinkDetail>("flow");
  // Bumped by Tidy so the canvas re-frames onto the new layout.
  const [layoutVersion, setLayoutVersion] = useState(0);
  // Nodes visited before the current one, newest last -- what "Back" walks.
  const [trail, setTrail] = useState<string[]>([]);

  const selectedNode = selection?.kind === "node" ? nodes.find((n) => n.id === selection.id) ?? null : null;
  const selectedRelationship = selection?.kind === "relationship" ? relationships.find((r) => r.id === selection.id) ?? null : null;

  const needsReviewCount = nodes.filter((n) => n.status === "needs_review").length;
  const conceptCount = nodes.filter((n) => n.type === "concept").length;
  const skillCount = nodes.filter((n) => n.type === "skill").length;

  // Focus mode: only the selected node, what leads into it and what it leads to.
  const links = useMemo(
    () => relationships.map((r) => ({ id: r.id, source: r.sourceId, target: r.targetId })),
    [relationships],
  );
  const focusView = useFocusView(focusMode && selectedNode ? selectedNode.id : null, links);
  const visibleNodeIds = useMemo(
    () => (focusView ? new Set([...filters.visibleNodeIds].filter((id) => focusView.nodeIds.has(id))) : filters.visibleNodeIds),
    [focusView, filters.visibleNodeIds],
  );
  const visibleRelationshipIds = useMemo(
    () => (focusView ? new Set([...filters.visibleRelationshipIds].filter((id) => focusView.edgeIds.has(id))) : filters.visibleRelationshipIds),
    [focusView, filters.visibleRelationshipIds],
  );
  const pathNodes = useMemo(() => nodes.filter((n) => filters.visibleNodeIds.has(n.id)), [nodes, filters.visibleNodeIds]);
  const framePositions = useMemo(
    () =>
      focusView
        ? Object.values(focusView.positions)
        : nodes.filter((n) => filters.visibleNodeIds.has(n.id)).map((n) => n.position ?? { x: 0, y: 0 }),
    [focusView, nodes, filters.visibleNodeIds],
  );

  // Every way of moving to another node (canvas click, related-node chips,
  // search) goes through here so Back always has somewhere to return to.
  function navigateTo(nodeId: string) {
    if (selection?.kind === "node" && selection.id === nodeId) return;
    if (selection?.kind === "node") setTrail((t) => [...t.slice(-49), selection.id]);
    selectNode(nodeId);
    if (!focusMode) setFocusNodeId(nodeId);
  }

  function goBack() {
    const previous = trail[trail.length - 1];
    if (!previous) return;
    setTrail((t) => t.slice(0, -1));
    selectNode(previous);
    if (!focusMode) setFocusNodeId(previous);
  }

  function handleSearchSelect(nodeId: string) {
    navigateTo(nodeId);
    filters.setSearchQuery("");
  }

  async function handleApprove() {
    if (!selectedRelationship) return;
    await editRelationship(selectedRelationship.id, { teacherApproved: true });
  }

  return (
    <ReactFlowProvider>
      <div className="kg-page">
        <div className="kg-header">
          <div className="kg-breadcrumb">
            Knowledge Graph <span>/</span> English Language <span>/</span> B1 Curriculum
          </div>
          <GraphSearch
            query={filters.searchQuery}
            onQueryChange={filters.setSearchQuery}
            results={filters.searchResults}
            onSelectResult={handleSearchSelect}
          />
          <ViewSwitch view={view} onChange={setView} />
          <div className="kg-add-menu">
            <button type="button" className="btn btn-primary" onClick={() => setAddMenuOpen((v) => !v)}>
              <IconPlus /> Add
            </button>
            {addMenuOpen && (
              <div className="kg-add-menu-list">
                {ADD_MENU_TYPES.map((t) => (
                  <button
                    type="button"
                    key={t}
                    className="kg-add-menu-item"
                    onClick={() => {
                      setNodeFormState({ mode: "add", initialType: t });
                      setAddMenuOpen(false);
                    }}
                  >
                    Add {NODE_TYPE_LABELS[t]}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {error && <div className="error-banner kg-page-error">{error}</div>}

        <div className="kg-body">
          <aside className="kg-left">
            <GraphFilters
              nodeTypes={filters.nodeTypes}
              cefr={filters.cefr}
              skills={filters.skills}
              statuses={filters.statuses}
              onToggleNodeType={filters.toggleNodeType}
              onToggleCefr={filters.toggleCefr}
              onToggleSkill={filters.toggleSkill}
              onToggleStatus={filters.toggleStatus}
            />
            <GraphLegend />
          </aside>

          {view === "path" ? (
            loading ? (
              <div className="empty-panel">Loading graph…</div>
            ) : (
              <LearningPathView
                nodes={pathNodes}
                relationships={relationships}
                selectedId={selectedNode?.id ?? null}
                onSelectNode={navigateTo}
              />
            )
          ) : (
            <div className={`kg-canvas-wrap kg-stage${showLabels ? "" : " kg-labels-hidden"}${focusView ? " kg-focus-on" : ""}`}>
              {loading ? (
                <div className="empty-panel">Loading graph…</div>
              ) : (
                <>
                  <KnowledgeGraphCanvas
                    nodes={nodes}
                    relationships={relationships}
                    visibleNodeIds={visibleNodeIds}
                    visibleRelationshipIds={visibleRelationshipIds}
                    selection={selection}
                    positionOverrides={focusView?.positions ?? null}
                    linkDetail={linkDetail}
                    onSelectNode={navigateTo}
                    onSelectRelationship={selectRelationship}
                    onClearSelection={clearSelection}
                    onMoveNode={moveNode}
                    onRequestConnect={(sourceId, targetId) => setRelationshipFormState({ mode: "create", sourceId, targetId })}
                  />
                  <div className="kg-canvas-toolbar-slot">
                    <GraphToolbar
                      onResetLayout={() => {
                        resetLayout();
                        setLayoutVersion((v) => v + 1);
                      }}
                      showLabels={showLabels}
                      onToggleLabels={() => setShowLabels((v) => !v)}
                      linkDetail={linkDetail}
                      onToggleLinks={() => setLinkDetail((d) => (d === "flow" ? "all" : "flow"))}
                      focusMode={focusMode}
                      onToggleFocus={() => setFocusMode((v) => !v)}
                      onBack={trail.length > 0 ? goBack : undefined}
                    />
                  </div>
                  {focusMode && !selectedNode && <FocusNote />}
                  <FocusFit
                    frameKey={focusView ? `focus:${focusView.centerId}` : `all:${layoutVersion}`}
                    positions={framePositions}
                    top={80}
                    minZoom={focusView ? 0.4 : 0.75}
                  />
                  <GraphFocusEffect nodeId={focusNodeId} onDone={() => setFocusNodeId(null)} />
                </>
              )}
            </div>
          )}

          <aside className="kg-right">
            {selectedNode && (
              <NodeInspector
                node={selectedNode}
                allNodes={nodes}
                relationships={relationships}
                onSelectNode={navigateTo}
                onEdit={() => setNodeFormState({ mode: "edit", nodeId: selectedNode.id })}
                onDelete={() => setDeleteState({ kind: "node", id: selectedNode.id, label: selectedNode.name })}
              />
            )}
            {selectedRelationship && (
              <EdgeInspector
                relationship={selectedRelationship}
                allNodes={nodes}
                onSelectNode={navigateTo}
                onEdit={() => setRelationshipFormState({ mode: "edit", relationshipId: selectedRelationship.id })}
                onDelete={() => setDeleteState({ kind: "relationship", id: selectedRelationship.id, label: "this relationship" })}
                onApprove={handleApprove}
              />
            )}
            {!selectedNode && !selectedRelationship && (
              <div className="kg-inspector-empty empty-panel">
                <p>Select a node to inspect its educational role, prerequisites, resources, and relationships.</p>
                <div className="kg-summary">
                  <div>{nodes.length} Nodes</div>
                  <div>{relationships.length} Relationships</div>
                  <div>{needsReviewCount} Need Review</div>
                </div>
              </div>
            )}
          </aside>
        </div>

        <div className="kg-status-bar">
          <span>{conceptCount} Concepts</span>
          <span>{relationships.length} Relationships</span>
          <span>{skillCount} Skills</span>
          <span>{needsReviewCount} Needs Review</span>
        </div>
      </div>

      {nodeFormState && (
        <NodeForm
          mode={nodeFormState.mode}
          initialType={nodeFormState.mode === "add" ? nodeFormState.initialType : undefined}
          initial={nodeFormState.mode === "edit" ? nodes.find((n) => n.id === nodeFormState.nodeId) : undefined}
          onClose={() => setNodeFormState(null)}
          onSave={async (data) => {
            if (nodeFormState.mode === "add") {
              const created = await addNode(data as Omit<KnowledgeNode, "id">);
              selectNode(created.id);
            } else {
              await editNode(nodeFormState.nodeId, data);
            }
          }}
        />
      )}

      {relationshipFormState && (() => {
        const sourceId = relationshipFormState.mode === "create"
          ? relationshipFormState.sourceId
          : relationships.find((r) => r.id === relationshipFormState.relationshipId)?.sourceId;
        const targetId = relationshipFormState.mode === "create"
          ? relationshipFormState.targetId
          : relationships.find((r) => r.id === relationshipFormState.relationshipId)?.targetId;
        const sourceNode = nodes.find((n) => n.id === sourceId);
        const targetNode = nodes.find((n) => n.id === targetId);
        if (!sourceNode || !targetNode) return null;
        return (
          <RelationshipForm
            mode={relationshipFormState.mode}
            sourceNode={sourceNode}
            targetNode={targetNode}
            initial={relationshipFormState.mode === "edit" ? relationships.find((r) => r.id === relationshipFormState.relationshipId) : undefined}
            onClose={() => setRelationshipFormState(null)}
            onSave={async (data) => {
              if (relationshipFormState.mode === "create") {
                const created = await addRelationship(data as Omit<KnowledgeRelationship, "id">);
                selectRelationship(created.id);
              } else {
                await editRelationship(relationshipFormState.relationshipId, data);
              }
            }}
          />
        );
      })()}

      {deleteState && (
        <DeleteConfirmationDialog
          title={deleteState.kind === "node" ? "Delete node" : "Delete relationship"}
          description={
            deleteState.kind === "node"
              ? `Delete "${deleteState.label}"? Its relationships will be removed too. This can't be undone.`
              : "Delete this relationship? This can't be undone."
          }
          onCancel={() => setDeleteState(null)}
          onConfirm={async () => {
            if (deleteState.kind === "node") await removeNode(deleteState.id);
            else await removeRelationship(deleteState.id);
            clearSelection();
            setDeleteState(null);
          }}
        />
      )}
    </ReactFlowProvider>
  );
}

function GraphFocusEffect({ nodeId, onDone }: { nodeId: string | null; onDone: () => void }) {
  const { setCenter, getNode } = useReactFlow();

  useEffect(() => {
    if (!nodeId) return;
    const flowNode = getNode(nodeId);
    if (flowNode) {
      const x = flowNode.position.x + (flowNode.measured?.width ?? 200) / 2;
      const y = flowNode.position.y + (flowNode.measured?.height ?? 92) / 2;
      setCenter(x, y, { zoom: 1, duration: 400 });
    }
    onDone();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeId]);

  return null;
}
