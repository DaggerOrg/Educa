// Frontend model for the Knowledge Graph editor. Mirrors the shape a future
// `GET /api/knowledge-graphs/:id` would return ({ nodes, relationships })
// so knowledgeGraphService.ts can swap its mock implementation for a real
// one without any component changes.

export type KnowledgeNodeType =
  | "concept"
  | "skill"
  | "learning_objective"
  | "exercise"
  | "resource"
  | "level";

export type KnowledgeStatus =
  | "ai_generated"
  | "teacher_reviewed"
  | "teacher_approved"
  | "needs_review";

export type CefrLevel = "A1" | "A2" | "B1" | "B2" | "C1" | "C2";

export interface KnowledgeSource {
  id: string;
  documentName: string;
  documentType: "textbook" | "teacher_guide" | "worksheet" | "exam" | "lecture_note";
  chapter?: string;
  unit?: string;
  page?: number;
  excerpt?: string;
  evidenceType: "explicit" | "llm_inferred" | "teacher_added";
}

export interface KnowledgeNode {
  id: string;
  type: KnowledgeNodeType;

  name: string;
  description?: string;

  category?: string;
  cefrLevel?: CefrLevel;

  status: KnowledgeStatus;

  // Future AI extraction confidence -- read-only in the UI, never a form field.
  confidence?: number;

  aliases?: string[];
  tags?: string[];
  sources?: KnowledgeSource[];

  createdBy?: "ai" | "teacher";
  createdAt?: string;
  updatedAt?: string;

  position?: { x: number; y: number };
}

export type KnowledgeRelationshipType =
  | "prerequisite_of"
  | "part_of"
  | "practices"
  | "assesses"
  | "teaches"
  | "uses"
  | "explained_by"
  | "supported_by"
  | "belongs_to_level"
  | "reinforces";

export interface KnowledgeRelationship {
  id: string;
  sourceId: string;
  targetId: string;
  type: KnowledgeRelationshipType;

  description?: string;
  confidence?: number;

  evidenceType: "source_explicit" | "llm_inferred" | "teacher_created";
  teacherApproved: boolean;

  sources?: KnowledgeSource[];
}

export interface KnowledgeGraphData {
  nodes: KnowledgeNode[];
  relationships: KnowledgeRelationship[];
}

export const NODE_TYPE_LABELS: Record<KnowledgeNodeType, string> = {
  concept: "Concept",
  skill: "Skill",
  learning_objective: "Learning Objective",
  exercise: "Exercise",
  resource: "Resource",
  level: "Level",
};

export const STATUS_LABELS: Record<KnowledgeStatus, string> = {
  ai_generated: "AI Generated",
  needs_review: "Needs Review",
  teacher_reviewed: "Teacher Reviewed",
  teacher_approved: "Teacher Approved",
};

export const RELATIONSHIP_LABELS: Record<KnowledgeRelationshipType, string> = {
  prerequisite_of: "PREREQUISITE_OF",
  part_of: "PART_OF",
  practices: "PRACTICES",
  assesses: "ASSESSES",
  teaches: "TEACHES",
  uses: "USES",
  explained_by: "EXPLAINED_BY",
  supported_by: "SUPPORTED_BY",
  belongs_to_level: "BELONGS_TO_LEVEL",
  reinforces: "REINFORCES",
};
