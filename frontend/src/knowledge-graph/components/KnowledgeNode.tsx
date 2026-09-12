import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import type { ComponentType, SVGProps } from "react";
import {
  IconConcept, IconDocument, IconEdit, IconLevel, IconObjective, IconSkill,
} from "../../components/icons.tsx";
import type { KnowledgeNode, KnowledgeNodeType, KnowledgeStatus } from "../types/knowledgeGraph.ts";
import { NODE_TYPE_LABELS, STATUS_LABELS } from "../types/knowledgeGraph.ts";

const TYPE_ICONS: Record<KnowledgeNodeType, ComponentType<SVGProps<SVGSVGElement>>> = {
  concept: IconConcept,
  skill: IconSkill,
  learning_objective: IconObjective,
  exercise: IconEdit,
  resource: IconDocument,
  level: IconLevel,
};

const STATUS_CLASS: Record<KnowledgeStatus, string> = {
  teacher_approved: "kg-status-approved",
  needs_review: "kg-status-review",
  ai_generated: "kg-status-ai",
  teacher_reviewed: "kg-status-reviewed",
};

export type KnowledgeFlowNodeData = { node: KnowledgeNode };
export type KnowledgeFlowNode = Node<KnowledgeFlowNodeData, "knowledge">;

export default function KnowledgeNodeCard({ data, selected }: NodeProps<KnowledgeFlowNode>) {
  const { node } = data;
  const Icon = TYPE_ICONS[node.type];

  return (
    <div className={`kg-node${selected ? " is-selected" : ""}`}>
      <Handle type="target" position={Position.Top} />
      <div className="kg-node-type">
        <Icon className="kg-node-type-icon" />
        {NODE_TYPE_LABELS[node.type]}
      </div>
      <div className="kg-node-name">{node.name}</div>
      <div className="kg-node-meta">
        {node.cefrLevel && <span className="kg-node-cefr">{node.cefrLevel}</span>}
        {node.cefrLevel && <span className="kg-node-dot">•</span>}
        <span className={`kg-node-status ${STATUS_CLASS[node.status]}`}>{STATUS_LABELS[node.status]}</span>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
