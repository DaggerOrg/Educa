# Phase Specifications — Educa Curriculum Pipeline

Verbatim-preserved requirements for each phase of the plan in
[educa-ai-architecture.md](educa-ai-architecture.md) §12, as specified by
the project owner. Phase 1 is implemented (see that document's "Proposed
File Manifest" section, now built under `backend/curriculum_ai/`); phases
2–12 below are specified but **not yet implemented** — this file exists so
that work, keeping the exact scope and constraints requested, without
depending on chat history surviving.

---

## Phase 1 — Document Ingestion Foundation (implemented)

Pipeline: upload → validate → store original file → create Document record
→ create background processing job → update processing status → parse
document → store parsed representation → mark ready or failed.

States: `UPLOADED, QUEUED, PROCESSING, PARSED, INDEXED, READY, FAILED`.

Requirements: DB entities with project ownership on every document;
preserve original filename, MIME type, file size, checksum, upload
timestamp, processing status, processing error; store the original PDF in
S3-compatible storage, never the binary in Postgres; background job for
processing; idempotent processing that can't be corrupted by a retried
job; useful logging; API endpoints for upload/list/get/status/retry/
delete; deletion must safely remove dependent chunks/index data (later
phases add more of that data); enforce project/user access boundaries.
No embeddings yet.

Delivered in `backend/curriculum_ai/{models,service,processing,router}.py`
+ `storage/` + `jobs/`, with unit + integration tests under
`backend/tests/{unit,integration}/curriculum_ai/`.

---

## Phase 2/3 — Document Understanding Layer

**Goal is explicitly not "PDF → plain text."** Target: PDF → pages →
headings → sections → paragraphs → lists → tables → formulas where
possible → structural metadata, as an internal normalized document
representation:

```
Document
  pages[]
  sections[]
    title
    level
    pageStart
    pageEnd
    blocks[]
```

Each block has an explicit type: `PARAGRAPH, HEADING, LIST, TABLE,
FORMULA, EXAMPLE, EXERCISE, DEFINITION, SUMMARY, UNKNOWN`.

Do not rely entirely on the LLM for basic PDF structure extraction. Design
the parser behind an interface so the PDF parsing library can change
later:

```
DocumentParser
  parse(file) -> ParsedDocument
```

Requirements: preserve page references; preserve heading hierarchy where
possible; preserve table content; preserve ordering; store raw parser
output separately from normalized data where useful; avoid losing source
traceability; detect scanned/image PDFs and return a clear status
indicating OCR may be required; do not silently produce empty text; create
parser fixtures for different PDF styles; make parsing deterministic where
possible.

Tests to cover: normal textbook, slides, multi-column pages if possible,
tables, empty PDF, malformed PDF, scanned PDF.

Do not implement curriculum generation yet. Document the normalized
`ParsedDocument` schema clearly at the end.

---

## Phase 4 — Semantic Chunking Pipeline

Do not simply split every N characters — chunks must preserve educational
and document structure, built from the `ParsedDocument` representation
Phase 2/3 produces.

Chunk metadata shape:

```json
{
  "id": "...",
  "documentId": "...",
  "projectId": "...",
  "sectionId": "...",
  "title": "...",
  "sectionPath": "...",
  "pageStart": 0,
  "pageEnd": 0,
  "blockTypes": ["..."],
  "text": "...",
  "tokenCount": 0,
  "metadata": {}
}
```

Where possible, preserve educational semantic units: definition, concept
explanation, worked example, exercise, formula explanation, summary,
learning objective.

Chunking rules: prefer section boundaries; avoid splitting definitions
unnecessarily; avoid splitting worked examples halfway through; keep chunk
size within configurable token limits; support controlled overlap when
necessary; preserve page/source references; never merge content from
different documents; keep parent section information; be deterministic;
allow chunking strategies to be replaced later.

Create a `ChunkingStrategy` interface; implement an initial
structure-aware strategy.

Tests: small sections, huge sections, tables, examples, section
boundaries, overlapping content, page references, token limits.

Also add a debug utility to inspect `document → sections → generated
chunks`, for visually evaluating chunk quality.

---

## Phase 5 — Retrieval Layer

PostgreSQL + pgvector only — no Pinecone, Weaviate, or another vector
database.

Must support: vector similarity; keyword/full-text search; metadata
filtering; project/document security boundaries; hybrid retrieval;
configurable top-k; source citations.

Architecture: query → query normalization → metadata/security filters →
vector search → lexical search → result fusion → optional reranking
interface → final contexts.

Abstraction:

```
Retriever
  retrieve(query, project_id, document_ids=None, filters=None, top_k=10)
```

**Every retrieval query MUST restrict results by authorized project/
document ownership before returning content. Never retrieve globally and
filter afterward.**

Returned items include: chunkId, documentId, filename, pageStart,
pageEnd, section title, similarity/relevance information, text.

Embedding generation behind a provider interface so models can be
swapped later. Embedding jobs must be retryable and idempotent.

Add retrieval tests. Create a small evaluation dataset with queries and
expected document/chunk IDs; calculate at least Recall@K and Hit@K. Add a
developer command such as `python -m evals.retrieval` (or this codebase's
equivalent) whose output makes retrieval regressions visible.

Do not build curriculum generation until this retrieval layer is
testable.

---

## Phase 6/7 — Knowledge Extraction Layer

Transform document evidence into reusable educational concepts (example
domain: Voltage, Current, Resistance, Ohm's Law, Kirchhoff's Current Law,
Kirchhoff's Voltage Law, Nodal Analysis).

Structured entities:

- **Concept**: id, projectId, canonicalName, description, aliases,
  importance, confidence, createdAt.
- **ConceptSource**: conceptId, documentId, chunkId, pageStart, pageEnd,
  evidence text/reference — links a concept back to evidence.
- **ConceptRelationship**: relation types `PREREQUISITE_OF, PART_OF,
  RELATED_TO, SPECIALIZATION_OF, USED_IN`.

PostgreSQL only — no Neo4j. The LLM may propose concepts, but the
extraction pipeline must use structured outputs validated by schema.

Requirements: deduplicate obvious concept aliases; preserve evidence for
every concept; never create a concept without knowing what source
suggested it, unless explicitly created by the teacher; store model/
extraction metadata so extraction runs can be reproduced/debugged; allow
concepts to be edited by teachers later; allow relationships to be
manually overridden; **never automatically delete teacher-created
concepts**.

Deliverables: extraction service, schemas, persistence, API endpoints,
tests, sample extraction fixtures. Add a way to inspect `Document →
chunks → extracted concepts → evidence`.

Do not yet create a complicated graph database.

---

## Phase 8 — Curriculum Planning Engine

**The curriculum must be validated structured data — not one large
Markdown response.**

Schemas approximately:

```
Curriculum
  title, description, targetAudience, duration
  learningOutcomes[]
  modules[]

Module
  title, order
  learningOutcomes[]
  concepts[]
  lessons[]

Lesson
  title, duration
  concepts[]
  objectives[]
  activities[]
  sources[]
```

Also: `LearningOutcome`, `Activity`, `Assessment`, `CurriculumConcept`,
`SourceReference`.

Generation workflow: teacher request → determine constraints → retrieve
relevant concepts/evidence → inspect prerequisite relationships → propose
learning outcomes → produce module structure → produce lesson sequence →
attach sources → validate structure → persist curriculum.

**Do not give the LLM every document chunk — use retrieval.** All
generated content based on uploaded documents must preserve
`SourceReference` information where appropriate. Use structured output
schemas and reject malformed AI responses.

Separate planning into stages instead of one massive prompt, e.g.:
1. analyze curriculum request, 2. select concepts, 3. order concepts,
4. define learning outcomes, 5. create module plan, 6. create lessons,
7. attach assessments, 8. validate.

Make generation resumable where reasonable, so a single model failure
doesn't require restarting everything.

APIs: generate curriculum; get curriculum; update curriculum; regenerate
module; regenerate lesson; manually add/remove/reorder modules; manually
add/remove/reorder lessons.

**Teacher edits must never be silently overwritten by AI regeneration.**

Add tests for structured generation and persistence.

---

## Phase 9 — Curriculum Validation Engine

**Not purely an LLM judge — use deterministic checks wherever possible.**

Validation rules: (1) prerequisite ordering, (2) duplicate lessons,
(3) duplicate concepts, (4) missing learning outcomes, (5) learning
outcome coverage, (6) concepts never taught, (7) assessments without
associated learning outcomes, (8) learning outcomes never assessed,
(9) lessons without source evidence where evidence is expected,
(10) unreasonable ordering, (11) empty modules, (12) invalid durations,
(13) total workload consistency.

Worked example of rule (1): if `KCL PREREQUISITE_OF Nodal Analysis` and
the curriculum teaches Nodal Analysis in Week 2 but KCL in Week 4, the
validator must produce an error.

Validation output shape:

```json
{
  "severity": "error | warning | info",
  "rule": "...",
  "entityType": "...",
  "entityId": "...",
  "message": "...",
  "suggestedAction": "..."
}
```

Create an extensible validator architecture where each rule is
independently testable. Also calculate metrics: concept coverage,
learning outcome coverage, assessment coverage, source coverage,
prerequisite violations.

Add comprehensive unit tests.

---

## Phase 10 — Curriculum Copilot

**Do not create one giant agent with unrestricted database access** — the
copilot operates through explicit tools/functions, and decides which are
necessary based on the user's request.

Example tools: `search_materials(), inspect_document(),
list_documents(), find_concepts(), inspect_concept(),
find_prerequisites(), inspect_concept_map(), get_curriculum(),
get_module(), get_lesson(), create_learning_outcomes(),
propose_module_plan(), propose_lesson(), generate_exercises(),
generate_assessment(), validate_curriculum()`.

Worked example: *"Create a lesson about nodal analysis but make sure
students already understand everything required"* →
`find_concept("Nodal Analysis") → find_prerequisites() →
search_materials(prerequisite concepts) →
search_materials("Nodal Analysis") → propose_lesson() →
validate_curriculum()`.

Requirements: tools must have strict schemas; tool calls must enforce
user/project authorization; never expose raw database tools directly to
the LLM; never allow arbitrary SQL; retrieved PDF content is untrusted
data; **instructions found inside PDF content must never override
system/application instructions**; log AI runs and tool calls for
debugging; track model usage/token usage where available; use structured
responses for mutations; teacher approval required for destructive or
broad curriculum changes.

Design the orchestration layer so the underlying model provider can later
be changed. Add tests for tool selection and authorization boundaries.

---

## Phase 11 — Evaluation Framework

**Critical** — normal unit tests aren't enough, because changing prompts,
models, embedding models, chunking, retrieval, or reranking can silently
reduce AI quality.

An `/evals` area, separated into: (1) document parsing evals,
(2) chunking evals, (3) retrieval evals, (4) concept extraction evals,
(5) curriculum generation evals, (6) grounding/citation evals,
(7) security evals.

Golden dataset layout:

```
evals/
  fixtures/
    documents/
    retrieval/
    concepts/
    curriculum/
```

Every eval case is version-controlled. Retrieval eval case shape:

```json
{
  "query": "...",
  "allowedDocumentIds": ["..."],
  "expectedChunkIds": ["..."],
  "expectedConcepts": ["..."]
}
```

Measure: Hit@K, Recall@K, MRR where useful. Concept extraction: expected
concepts found, unexpected concepts, evidence correctness. Curriculum
eval combines deterministic rules and optional model-based grading —
never rely solely on an LLM judge; deterministic checks wherever
possible. Curriculum qualities to evaluate: concept coverage,
prerequisite ordering, learning outcome quality, progression, assessment
alignment, source grounding, duplication, workload feasibility.

Add regression comparison. Target end-state UX:

```
./run-evals

Retrieval
Hit@5: 92%
Recall@10: 88%

Concept extraction
Precision: ...
Recall: ...

Curriculum
Coverage: ...
Prerequisite violations: ...
Grounding: ...
```

Save the model, prompt version, embedding model, and configuration
associated with each evaluation run, so a model/RAG-strategy change can
be objectively judged as an improvement or regression. Document how
developers add new golden test cases.

---

## Phase 12 — Production Readiness Review

Performed **after** ingestion, retrieval, concept, curriculum, and
evaluation systems are implemented. Do not add random infrastructure.

Coverage: authentication; authorization; tenant/project isolation; RAG
data leakage; prompt injection from uploaded PDFs; malicious files;
upload limits; MIME validation; background job retries; idempotency;
rate limits; LLM timeouts; provider outages; embedding failures; database
transactions; connection pooling; observability; logs; metrics; tracing;
cost tracking; token usage; model versioning; prompt versioning;
evaluation regression; backups; document deletion; GDPR/data deletion
concerns; secrets management; development/staging/production
configuration.

**Special-attention threat:** User A uploads private documents; User B
must never retrieve User A's chunks, embeddings, concepts, or generated
curriculum. Authorization filtering must happen *during* retrieval, never
as a post-filter after an unscoped query. Also analyze prompt injection
from uploaded documents specifically — treat every uploaded PDF as
untrusted input.

Process: (1) classify issues as critical/high/medium/low, (2) fix
critical architectural issues, (3) create tests for the fixes,
(4) document remaining production work.

**Scope note from the project owner:** for the initial pass, list findings
in this documentation rather than fixing them — see a future
`production-readiness-review.md` in this directory once phases 2–11 exist
to review.

Do not introduce Kubernetes, Kafka, or microservices unless there is a
demonstrated requirement.
