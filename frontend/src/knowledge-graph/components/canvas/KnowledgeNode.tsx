import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { createContext, useContext, type ComponentType, type SVGProps } from "react";
import FlagBadge, { type FlowRole } from "./FlagBadge.tsx";
import {
  IconConcept, IconDocument, IconEdit, IconLevel, IconObjective, IconSkill,
} from "../../../components/icons.tsx";
import type { KnowledgeNode, KnowledgeNodeType, KnowledgeStatus } from "../../types/knowledgeGraph.ts";
import { NODE_TYPE_LABELS, STATUS_LABELS } from "../../types/knowledgeGraph.ts";

export const TYPE_ICONS: Record<KnowledgeNodeType, ComponentType<SVGProps<SVGSVGElement>>> = {
  concept: IconConcept,
  skill: IconSkill,
  learning_objective: IconObjective,
  exercise: IconEdit,
  resource: IconDocument,
  level: IconLevel,
};

export const STATUS_CLASS: Record<KnowledgeStatus, string> = {
  teacher_approved: "kg-status-approved",
  needs_review: "kg-status-review",
  ai_generated: "kg-status-ai",
  teacher_reviewed: "kg-status-reviewed",
};

// Which nodes are the start / end of a chain of "learn this first" arrows, provided by the canvas.
export const NodeRoleContext = createContext<ReadonlyMap<string, FlowRole> | null>(null);

export type KnowledgeFlowNodeData = { node: KnowledgeNode };
export type KnowledgeFlowNode = Node<KnowledgeFlowNodeData, "knowledge">;

// Name first, type + level second, review status as a dot (same colors as
// the legend in the filters panel). Anything more belongs in the inspector.
export default function KnowledgeNodeCard({ data, selected }: NodeProps<KnowledgeFlowNode>) {
  const { node } = data;
  const Icon = TYPE_ICONS[node.type];
  const role = useContext(NodeRoleContext)?.get(node.id);

  return (
    <div className={`kg-node${selected ? " is-selected" : ""}`}>
      {role && <FlagBadge role={role} />}
      <Handle type="target" position={Position.Left} />
      <span className="kg-node-icon">
        <Icon />
      </span>
      <div className="kg-node-body">
        <div className="kg-node-name" title={node.name}>{node.name}</div>
        <div className="kg-node-meta">
          {NODE_TYPE_LABELS[node.type]}
          {node.cefrLevel ? ` · ${node.cefrLevel}` : ""}
        </div>
      </div>
      <span
        className={`kg-node-dot ${STATUS_CLASS[node.status]}`}
        role="img"
        aria-label={STATUS_LABELS[node.status]}
        title={STATUS_LABELS[node.status]}
      />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
