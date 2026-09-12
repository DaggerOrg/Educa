import type { KnowledgeGraphData, KnowledgeNode, KnowledgeRelationship, KnowledgeSource } from "../types/knowledgeGraph.ts";

// Demo domain: English language teaching, B1 curriculum -- see
// KnowledgeGraphPage's breadcrumb. 30 nodes / 41 relationships, enough to
// feel like a real subject graph rather than a 3-node toy demo. Clustered
// by category (grammar / vocabulary / skills / activities / assessment /
// resources / levels) so graphLayout.ts has real structure to lay out.

const grammarBook: KnowledgeSource = {
  id: "source-grammar-book-u7",
  documentName: "English Grammar Book",
  documentType: "textbook",
  unit: "Unit 7",
  page: 84,
  excerpt: "The present perfect is formed using have/has and the past participle. It connects a past action to the present moment.",
  evidenceType: "explicit",
};

const teacherGuide: KnowledgeSource = {
  id: "source-teacher-guide-u7",
  documentName: "Teacher Guide",
  documentType: "teacher_guide",
  unit: "Unit 7",
  page: 32,
  excerpt: "Introduce present perfect through a 'have you ever...' speaking warm-up before presenting the form explicitly.",
  evidenceType: "explicit",
};

const workbook7a: KnowledgeSource = {
  id: "source-workbook-7a",
  documentName: "Workbook",
  documentType: "worksheet",
  unit: "Exercise 7A",
  excerpt: "Complete the sentences using the present perfect: 'I ___ (visit) three countries this year.'",
  evidenceType: "explicit",
};

function node(partial: Partial<KnowledgeNode> & Pick<KnowledgeNode, "id" | "type" | "name" | "status">): KnowledgeNode {
  return {
    createdBy: partial.status === "ai_generated" || partial.status === "needs_review" ? "ai" : "teacher",
    createdAt: "2026-06-02T09:00:00Z",
    updatedAt: "2026-08-14T15:30:00Z",
    ...partial,
  };
}

export const englishKnowledgeGraph: KnowledgeGraphData = {
  nodes: [
    // ---- Grammar concepts ----
    node({
      id: "concept-present-simple", type: "concept", name: "Present Simple",
      description: "Used for habits, routines, facts, and general truths.",
      category: "grammar", cefrLevel: "A1", status: "teacher_approved", confidence: 0.98,
      aliases: ["Simple Present"], tags: ["tense", "verb-form"],
    }),
    node({
      id: "concept-have-has", type: "concept", name: "Have / Has",
      description: "Auxiliary verb used to form the present perfect (have/has + past participle).",
      category: "grammar", cefrLevel: "A1", status: "teacher_approved", confidence: 0.97,
      tags: ["auxiliary-verb"],
    }),
    node({
      id: "concept-past-simple", type: "concept", name: "Past Simple",
      description: "Used for completed actions at a specific time in the past.",
      category: "grammar", cefrLevel: "A2", status: "teacher_approved", confidence: 0.97,
      aliases: ["Simple Past"], tags: ["tense", "verb-form"],
    }),
    node({
      id: "concept-past-time", type: "concept", name: "Past-time concepts",
      description: "Time expressions and reference points (yesterday, last year, in 2020) that anchor an action in the past.",
      category: "grammar", cefrLevel: "A2", status: "teacher_reviewed", confidence: 0.85,
      tags: ["time-expressions"],
    }),
    node({
      id: "concept-past-participle", type: "concept", name: "Past Participle",
      description: "The verb form used with have/has to form the present perfect (e.g. gone, seen, visited).",
      category: "grammar", cefrLevel: "B1", status: "teacher_approved", confidence: 0.96,
      tags: ["verb-form"],
      sources: [grammarBook],
    }),
    node({
      id: "concept-present-perfect", type: "concept", name: "Present Perfect",
      description: "Used to describe experiences or events connected to the present.",
      category: "grammar", cefrLevel: "B1", status: "teacher_approved", confidence: 0.92,
      aliases: ["Present Perfect Tense"], tags: ["tense", "verb-form"],
      sources: [grammarBook, teacherGuide],
    }),
    node({
      id: "concept-present-perfect-continuous", type: "concept", name: "Present Perfect Continuous",
      description: "Used to emphasize the duration of an action that started in the past and continues now.",
      category: "grammar", cefrLevel: "B2", status: "needs_review", confidence: 0.71,
      tags: ["tense", "verb-form"],
    }),
    node({
      id: "concept-conditionals", type: "concept", name: "Conditionals",
      description: "Sentence structures describing hypothetical or real cause-and-effect situations.",
      category: "grammar", cefrLevel: "B2", status: "ai_generated", confidence: 0.68,
      tags: ["sentence-structure"],
    }),

    // ---- Vocabulary concepts ----
    node({
      id: "concept-travel-vocabulary", type: "concept", name: "Travel Vocabulary",
      description: "Core words and phrases for describing trips, transport, and destinations.",
      category: "vocabulary", cefrLevel: "A2", status: "teacher_approved", confidence: 0.94,
      tags: ["vocabulary", "travel"],
    }),
    node({
      id: "concept-life-experiences-vocabulary", type: "concept", name: "Life Experiences Vocabulary",
      description: "Vocabulary for talking about things you have done, been, or achieved.",
      category: "vocabulary", cefrLevel: "B1", status: "teacher_reviewed", confidence: 0.88,
      tags: ["vocabulary", "experiences"],
    }),

    // ---- Reading/writing sub-skills ----
    node({
      id: "concept-reading-inference", type: "concept", name: "Reading Inference",
      description: "Drawing conclusions from a text that aren't directly stated.",
      category: "reading-skills", cefrLevel: "B1", status: "teacher_reviewed", confidence: 0.83,
      tags: ["comprehension"],
    }),
    node({
      id: "concept-paragraph-structure", type: "concept", name: "Paragraph Structure",
      description: "Organizing a paragraph around a topic sentence, supporting detail, and conclusion.",
      category: "writing-skills", cefrLevel: "B1", status: "ai_generated", confidence: 0.74,
      tags: ["writing"],
    }),

    // ---- Skills ----
    node({ id: "skill-reading", type: "skill", name: "Reading", status: "teacher_approved", confidence: 1 }),
    node({ id: "skill-writing", type: "skill", name: "Writing", status: "teacher_approved", confidence: 1 }),
    node({ id: "skill-listening", type: "skill", name: "Listening", status: "teacher_approved", confidence: 1 }),
    node({ id: "skill-speaking", type: "skill", name: "Speaking", status: "teacher_approved", confidence: 1 }),

    // ---- CEFR levels ----
    node({ id: "level-a1", type: "level", name: "A1", status: "teacher_approved", confidence: 1 }),
    node({ id: "level-a2", type: "level", name: "A2", status: "teacher_approved", confidence: 1 }),
    node({ id: "level-b1", type: "level", name: "B1", status: "teacher_approved", confidence: 1 }),
    node({ id: "level-b2", type: "level", name: "B2", status: "teacher_approved", confidence: 1 }),
    node({ id: "level-c1", type: "level", name: "C1", status: "teacher_approved", confidence: 1 }),
    node({ id: "level-c2", type: "level", name: "C2", status: "teacher_approved", confidence: 1 }),

    // ---- Activities / exercises ----
    node({
      id: "exercise-reading-travel", type: "exercise", name: "Reading: Travel Experiences",
      description: "A short article about a backpacking trip, followed by comprehension questions.",
      category: "activity", cefrLevel: "B1", status: "teacher_approved", confidence: 0.9,
    }),
    node({
      id: "exercise-listening-trip-abroad", type: "exercise", name: "Listening: A Trip Abroad",
      description: "An audio recording of a traveler describing a memorable trip.",
      category: "activity", cefrLevel: "B1", status: "teacher_reviewed", confidence: 0.86,
    }),
    node({
      id: "exercise-speaking-have-you-ever", type: "exercise", name: "Speaking: Have You Ever…?",
      description: "Pair-work speaking task practicing present perfect questions about life experiences.",
      category: "activity", cefrLevel: "B1", status: "teacher_approved", confidence: 0.91,
      sources: [teacherGuide],
    }),
    node({
      id: "exercise-writing-memorable-experience", type: "exercise", name: "Writing: My Memorable Experience",
      description: "A guided paragraph-writing task describing a memorable personal experience.",
      category: "activity", cefrLevel: "B1", status: "needs_review", confidence: 0.65,
    }),
    node({
      id: "exercise-present-perfect-quiz", type: "exercise", name: "Present Perfect Quiz",
      description: "A 10-question quiz assessing present perfect form and usage.",
      category: "assessment", cefrLevel: "B1", status: "teacher_approved", confidence: 0.95,
      sources: [workbook7a],
    }),

    // ---- Learning objective ----
    node({
      id: "objective-describe-past-experiences", type: "learning_objective",
      name: "Students can describe past life experiences.",
      category: "objective", cefrLevel: "B1", status: "teacher_approved", confidence: 0.9,
    }),

    // ---- Resources ----
    node({
      id: "resource-grammar-book-u7", type: "resource", name: "English Grammar Book — Unit 7",
      description: "Core grammar reference, unit 7 covers the present perfect.",
      category: "textbook", status: "teacher_approved", confidence: 1,
      sources: [grammarBook],
    }),
    node({
      id: "resource-teacher-guide-u7", type: "resource", name: "Teacher Guide — Unit 7",
      description: "Lesson plans and warm-up activities for teaching unit 7.",
      category: "teacher_guide", status: "teacher_approved", confidence: 1,
      sources: [teacherGuide],
    }),
  ],

  relationships: [
    // ---- Prerequisite chain ----
    rel("rel-1", "concept-present-simple", "concept-past-simple", "prerequisite_of", "source_explicit", true, 0.95),
    rel("rel-2", "concept-past-simple", "concept-past-participle", "prerequisite_of", "source_explicit", true, 0.93),
    rel("rel-3", "concept-past-participle", "concept-present-perfect", "prerequisite_of", "source_explicit", true, 0.96, [grammarBook]),
    rel("rel-4", "concept-have-has", "concept-present-perfect", "prerequisite_of", "source_explicit", true, 0.95),
    rel("rel-5", "concept-past-time", "concept-present-perfect", "prerequisite_of", "llm_inferred", false, 0.72),
    rel("rel-6", "concept-present-perfect", "concept-present-perfect-continuous", "prerequisite_of", "llm_inferred", false, 0.79),
    rel("rel-7", "concept-past-simple", "concept-conditionals", "prerequisite_of", "llm_inferred", false, 0.66),
    rel("rel-8", "concept-present-perfect", "objective-describe-past-experiences", "prerequisite_of", "teacher_created", true, undefined),

    // ---- Level membership ----
    rel("rel-9", "concept-present-simple", "level-a1", "belongs_to_level", "source_explicit", true, undefined),
    rel("rel-10", "concept-have-has", "level-a1", "belongs_to_level", "source_explicit", true, undefined),
    rel("rel-11", "concept-past-simple", "level-a2", "belongs_to_level", "source_explicit", true, undefined),
    rel("rel-12", "concept-travel-vocabulary", "level-a2", "belongs_to_level", "source_explicit", true, undefined),
    rel("rel-13", "concept-past-time", "level-a2", "belongs_to_level", "llm_inferred", true, 0.8),
    rel("rel-14", "concept-past-participle", "level-b1", "belongs_to_level", "source_explicit", true, undefined),
    rel("rel-15", "concept-present-perfect", "level-b1", "belongs_to_level", "source_explicit", true, undefined),
    rel("rel-16", "concept-life-experiences-vocabulary", "level-b1", "belongs_to_level", "source_explicit", true, undefined),
    rel("rel-17", "concept-reading-inference", "level-b1", "belongs_to_level", "llm_inferred", true, 0.82),
    rel("rel-18", "concept-paragraph-structure", "level-b1", "belongs_to_level", "llm_inferred", false, 0.7),
    rel("rel-19", "concept-present-perfect-continuous", "level-b2", "belongs_to_level", "llm_inferred", false, 0.77),
    rel("rel-20", "concept-conditionals", "level-b2", "belongs_to_level", "llm_inferred", false, 0.69),

    // ---- Concept practices skill ----
    rel("rel-21", "concept-present-perfect", "skill-speaking", "practices", "source_explicit", true, undefined, [teacherGuide]),
    rel("rel-22", "concept-present-perfect", "skill-writing", "practices", "source_explicit", true, undefined),
    rel("rel-23", "concept-present-perfect", "skill-reading", "practices", "llm_inferred", true, 0.84),
    rel("rel-24", "concept-travel-vocabulary", "skill-speaking", "practices", "teacher_created", true, undefined),
    rel("rel-25", "concept-life-experiences-vocabulary", "skill-speaking", "practices", "llm_inferred", true, 0.81),
    rel("rel-26", "concept-reading-inference", "skill-reading", "practices", "source_explicit", true, undefined),

    // ---- Activity part_of skill ----
    rel("rel-27", "exercise-reading-travel", "skill-reading", "part_of", "source_explicit", true, undefined),
    rel("rel-28", "exercise-listening-trip-abroad", "skill-listening", "part_of", "source_explicit", true, undefined),
    rel("rel-29", "exercise-speaking-have-you-ever", "skill-speaking", "part_of", "source_explicit", true, undefined),
    rel("rel-30", "exercise-writing-memorable-experience", "skill-writing", "part_of", "source_explicit", true, undefined),

    // ---- Exercise uses concept ----
    rel("rel-31", "exercise-reading-travel", "concept-travel-vocabulary", "uses", "source_explicit", true, undefined),
    rel("rel-32", "exercise-listening-trip-abroad", "concept-travel-vocabulary", "uses", "source_explicit", true, undefined),
    rel("rel-33", "exercise-speaking-have-you-ever", "concept-present-perfect", "uses", "source_explicit", true, undefined, [teacherGuide]),
    rel("rel-34", "exercise-speaking-have-you-ever", "concept-life-experiences-vocabulary", "uses", "llm_inferred", true, 0.87),
    rel("rel-35", "exercise-writing-memorable-experience", "concept-present-perfect", "uses", "llm_inferred", false, 0.73),

    // ---- Assessment ----
    rel("rel-36", "exercise-present-perfect-quiz", "concept-present-perfect", "assesses", "source_explicit", true, undefined, [workbook7a]),

    // ---- Resources ----
    rel("rel-37", "concept-present-perfect", "resource-grammar-book-u7", "explained_by", "source_explicit", true, undefined, [grammarBook]),
    rel("rel-38", "resource-teacher-guide-u7", "concept-present-perfect", "teaches", "source_explicit", true, undefined, [teacherGuide]),
    rel("rel-39", "exercise-speaking-have-you-ever", "resource-teacher-guide-u7", "supported_by", "teacher_created", true, undefined),

    // ---- Reinforces ----
    rel("rel-40", "concept-present-perfect-continuous", "concept-present-perfect", "reinforces", "llm_inferred", false, 0.75),
    rel("rel-41", "concept-life-experiences-vocabulary", "concept-present-perfect", "reinforces", "teacher_created", true, undefined),
  ],
};

function rel(
  id: string,
  sourceId: string,
  targetId: string,
  type: KnowledgeRelationship["type"],
  evidenceType: KnowledgeRelationship["evidenceType"],
  teacherApproved: boolean,
  confidence: number | undefined,
  sources?: KnowledgeSource[],
): KnowledgeRelationship {
  return { id, sourceId, targetId, type, evidenceType, teacherApproved, confidence, sources };
}
