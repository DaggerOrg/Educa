import { BaseEdge, EdgeLabelRenderer, getBezierPath, type Edge, type EdgeProps } from "@xyflow/react";
import { RELATIONSHIP_LABELS } from "../types/knowledgeGraph.ts";
import type { KnowledgeRelationship } from "../types/knowledgeGraph.ts";

export type KnowledgeFlowEdgeData = { relationship: KnowledgeRelationship };
export type KnowledgeFlowEdge = Edge<KnowledgeFlowEdgeData, "knowledge">;

export default function KnowledgeEdgeLine({
  id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data, markerEnd, selected,
}: EdgeProps<KnowledgeFlowEdge>) {
  const [edgePath, labelX, labelY] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition });
  const relationship = data?.relationship;
  const isPendingAi = relationship?.evidenceType === "llm_inferred" && !relationship.teacherApproved;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        className={`kg-edge${isPendingAi ? " kg-edge-pending" : ""}${selected ? " is-selected" : ""}`}
      />
      {relationship && (
        <EdgeLabelRenderer>
          <div
            className={`kg-edge-label${isPendingAi ? " kg-edge-label-pending" : ""}${selected ? " is-selected" : ""}`}
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          >
            {RELATIONSHIP_LABELS[relationship.type]}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
