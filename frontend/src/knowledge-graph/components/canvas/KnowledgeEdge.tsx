import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath, type Edge, type EdgeProps } from "@xyflow/react";
import { createContext, useContext } from "react";
import { RELATIONSHIP_LABELS } from "../../types/knowledgeGraph.ts";
import type { KnowledgeRelationship } from "../../types/knowledgeGraph.ts";

// Ids of the currently selected node(s), provided by whichever canvas is rendering the edges.
// When set, edges touching them are highlighted and the rest fade back, so one node's
// connections can be read on a dense graph.
export const EdgeFocusContext = createContext<ReadonlySet<string> | null>(null);

export type KnowledgeFlowEdgeData = { relationship: KnowledgeRelationship };
export type KnowledgeFlowEdge = Edge<KnowledgeFlowEdgeData, "knowledge">;

export default function KnowledgeEdgeLine({
  id, source, target, sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition, data, markerEnd, selected,
}: EdgeProps<KnowledgeFlowEdge>) {
  // Right-angle connectors with softly rounded elbows -- reads cleaner than bezier curves on a dense graph.
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition, borderRadius: 8,
  });
  const relationship = data?.relationship;
  const isPendingAi = relationship?.evidenceType === "llm_inferred" && !relationship.teacherApproved;
  const focus = useContext(EdgeFocusContext);
  const hasFocus = !!focus && focus.size > 0;
  const isRelated = hasFocus && (focus.has(source) || focus.has(target));
  const isDimmed = hasFocus && !isRelated && !selected;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        className={`kg-edge${isPendingAi ? " kg-edge-pending" : ""}${isRelated ? " kg-edge-related" : ""}${isDimmed ? " kg-edge-dim" : ""}${selected ? " is-selected" : ""}`}
      />
      {relationship && (
        <EdgeLabelRenderer>
          <div
            className={`kg-edge-label${isPendingAi ? " kg-edge-label-pending" : ""}${isRelated ? " is-related" : ""}${isDimmed ? " kg-edge-label-dim" : ""}${selected ? " is-selected" : ""}`}
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          >
            {RELATIONSHIP_LABELS[relationship.type]}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
