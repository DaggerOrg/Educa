import { ReactFlowProvider, useReactFlow } from "@xyflow/react";
import { useEffect, useState } from "react";
import "./styles/knowledge-graph.css";
import { IconPlus } from "../components/icons.tsx";
import GraphFilters from "./components/GraphFilters.tsx";
import GraphLegend from "./components/GraphLegend.tsx";
import GraphSearch from "./components/GraphSearch.tsx";
import GraphToolbar from "./components/GraphToolbar.tsx";
import KnowledgeGraphCanvas from "./components/KnowledgeGraphCanvas.tsx";
import NodeInspector from "./components/NodeInspector.tsx";
import EdgeInspector from "./components/EdgeInspector.tsx";
import NodeForm from "./components/NodeForm.tsx";
import RelationshipForm from "./components/RelationshipForm.tsx";
import DeleteConfirmationDialog from "./components/DeleteConfirmationDialog.tsx";
import { useGraphFilters } from "./hooks/useGraphFilters.ts";
import { useGraphSelection } from "./hooks/useGraphSelection.ts";
import { useKnowledgeGraph } from "./hooks/useKnowledgeGraph.ts";
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

  const [addMenuOpen, setAddMenuOpen] = useState(false);
  const [nodeFormState, setNodeFormState] = useState<NodeFormState>(null);
  const [relationshipFormState, setRelationshipFormState] = useState<RelationshipFormState>(null);
  const [deleteState, setDeleteState] = useState<DeleteState>(null);
  const [showLabels, setShowLabels] = useState(true);
  const [focusNodeId, setFocusNodeId] = useState<string | null>(null);

  const selectedNode = selection?.kind === "node" ? nodes.find((n) => n.id === selection.id) ?? null : null;
  const selectedRelationship = selection?.kind === "relationship" ? relationships.find((r) => r.id === selection.id) ?? null : null;

  const needsReviewCount = nodes.filter((n) => n.status === "needs_review").length;
  const conceptCount = nodes.filter((n) => n.type === "concept").length;
  const skillCount = nodes.filter((n) => n.type === "skill").length;

  function handleSearchSelect(nodeId: string) {
    selectNode(nodeId);
    setFocusNodeId(nodeId);
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

          <div className={`kg-canvas-wrap${showLabels ? "" : " kg-labels-hidden"}`}>
            {loading ? (
              <div className="empty-panel">Loading graph…</div>
            ) : (
              <>
                <KnowledgeGraphCanvas
                  nodes={nodes}
                  relationships={relationships}
                  visibleNodeIds={filters.visibleNodeIds}
                  visibleRelationshipIds={filters.visibleRelationshipIds}
                  selection={selection}
                  onSelectNode={selectNode}
                  onSelectRelationship={selectRelationship}
                  onClearSelection={clearSelection}
                  onMoveNode={moveNode}
                  onRequestConnect={(sourceId, targetId) => setRelationshipFormState({ mode: "create", sourceId, targetId })}
                />
                <div className="kg-canvas-toolbar-slot">
                  <GraphToolbar onResetLayout={resetLayout} showLabels={showLabels} onToggleLabels={() => setShowLabels((v) => !v)} />
                </div>
                <GraphFocusEffect nodeId={focusNodeId} onDone={() => setFocusNodeId(null)} />
              </>
            )}
          </div>

          <aside className="kg-right">
            {selectedNode && (
              <NodeInspector
                node={selectedNode}
                allNodes={nodes}
                relationships={relationships}
                onSelectNode={selectNode}
                onEdit={() => setNodeFormState({ mode: "edit", nodeId: selectedNode.id })}
                onDelete={() => setDeleteState({ kind: "node", id: selectedNode.id, label: selectedNode.name })}
              />
            )}
            {selectedRelationship && (
              <EdgeInspector
                relationship={selectedRelationship}
                allNodes={nodes}
                onSelectNode={selectNode}
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
