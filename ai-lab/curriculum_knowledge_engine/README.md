# Curriculum Knowledge Engine (CKE)

An enterprise-shaped curriculum knowledge engine: hybrid RAG + GraphRAG over
ingested curricula, plus graph-driven prerequisite chains and learning
paths. Built as a deeper, production-structured sibling to the quick
scripts in [`../examples/`](../examples/) - same underlying ideas (RAG,
vector search, knowledge graphs), but as a layered, tested, swappable-
backend service instead of standalone scripts.

The sample content is itself an AI-engineering curriculum - 18 concepts
(Python -> neural networks -> transformers -> RAG -> knowledge graphs ->
GraphRAG -> agents -> evaluation) with real prerequisite relationships. See
[`data/sample_curriculum.yaml`](data/sample_curriculum.yaml).

## Architecture

```
src/cke/
  domain/          Pydantic models + enums + exceptions - no framework or storage code
  config.py        Settings (env-driven), one place every other module reads config from
  llm/             ClaudeClient - the only module that calls the Anthropic SDK
  repositories/    Interfaces (ports) + backend implementations (adapters)
    interfaces.py    VectorRepository, GraphRepository, CourseRepository (ABCs)
    vector/          ChromaVectorRepository (local) / PgVectorRepository (production)
    graph/           NetworkXGraphRepository (local) / Neo4jGraphRepository (production)
    course/          JsonCourseRepository
  ingestion/       CurriculumSpec (authoring schema) -> chunking -> embedding -> graph building
    graph_extractor.py   LLM-based graph enrichment (Claude proposes edges; human-authored edges stay authoritative)
  retrieval/       VectorRetriever, GraphRetriever, HybridRetriever (GraphRAG context assembly)
  services/        QAService, LearningPathService, GapAnalysisService, CurriculumService
  container.py     Composition root - wires Settings -> repositories -> services once
  api/             FastAPI app: routers, request/response schemas, error handlers
  cli/             Typer CLI - same Container the API uses
```

This is a ports-and-adapters (hexagonal) design: every service depends on
`cke.repositories.interfaces`, never on a concrete backend. Swapping
`CKE_VECTOR_BACKEND=chroma` -> `pgvector` or `CKE_GRAPH_BACKEND=networkx` ->
`neo4j` is a config change, not a code change - see `cke/repositories/factory.py`.

**A layered trust model for the concept graph.** The curriculum author
declares the backbone prerequisite graph by hand
(`CurriculumSpec.concepts[].requires`) - that's ground truth. Optionally
(`--llm-extract` / `enable_llm_extraction=true`), Claude also reads each
lesson's prose and proposes additional relationships it implies but the
author didn't declare, tagged `source=llm_extracted` with a confidence
score and rationale, and rejected outright if it would introduce a
prerequisite cycle. The same split shows up in `LearningPathService`: the
*order* of a study plan is always the deterministic output of a graph
topological sort, never something the LLM decides - Claude only writes the
pedagogical narrative and time estimates layered on top of that order.

## Setup

```bash
cd curriculum_knowledge_engine
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then fill in CKE_ANTHROPIC_API_KEY, or use `ant auth login`
```

## Usage

### CLI

```bash
cke ingest                                   # ingest the bundled sample curriculum
cke ingest --file path/to/other.yaml --llm-extract
cke courses
cke concepts --top-central 5                 # most foundational concepts
cke ask "How does GraphRAG combine structure and retrieval?"
cke path self-attention --known python-programming,linear-algebra-basics
cke gap neural-networks --known python-programming
cke serve --reload                           # run the API on :8000
```

### API

```bash
uvicorn cke.api.app:app --reload
```

| Method | Path | Description |
|---|---|---|
| POST | `/courses/ingest` | Ingest a curriculum (defaults to the bundled sample) |
| GET | `/courses` | List ingested courses |
| GET | `/courses/{course_id}` | Course detail (modules + lessons) |
| GET | `/concepts` | List every concept in the graph |
| GET | `/concepts/central?top_n=10` | Most foundational concepts, by transitive dependents |
| GET | `/concepts/{id}` / `/prerequisites` / `/dependents` | One concept and its direct graph neighbors |
| POST | `/qa/ask` | Grounded, cited answer (hybrid RAG + GraphRAG) |
| POST | `/learning-paths` | Graph-ordered study plan from known concepts to a goal |
| POST | `/learning-paths/gap-analysis` | Readiness % and missing prerequisites for a target concept |

Interactive docs at `/docs` once the server is running.

## Swapping in production backends

Local dev needs nothing beyond this repo (Chroma + NetworkX, both
file-backed under `./var`). To use Postgres/pgvector and Neo4j instead:

```bash
pip install -e ".[postgres,neo4j]"
docker compose up -d
```

then in `.env`:

```bash
CKE_VECTOR_BACKEND=pgvector
CKE_POSTGRES_DSN=postgresql://cke:cke@localhost:5432/cke
CKE_GRAPH_BACKEND=neo4j
CKE_NEO4J_URI=bolt://localhost:7687
CKE_NEO4J_PASSWORD=change-me-please
```

No service code changes - `cke/repositories/factory.py` is the only thing
that reads these settings.

## Testing

```bash
pytest
```

- `tests/unit/` - pure logic: chunking, the NetworkX graph algorithms
  (cycle detection, topological ordering, centrality), the curriculum
  schema's referential-integrity validation, and the QA/learning-path
  services with a fake Claude client (no network calls).
- `tests/integration/` - the full ingestion pipeline against real Chroma +
  NetworkX + the JSON course store (real local embeddings, no mocking
  below the ingestion service), and the FastAPI app end to end via
  `TestClient`, with `ClaudeClient.complete` / `.extract` monkeypatched at
  the class level so these run without an Anthropic API key while still
  exercising the real retrieval and graph-traversal code paths.

`Neo4jGraphRepository` and `PgVectorRepository` are not exercised by this
suite - there's no Neo4j/Postgres instance in this environment. They
satisfy the same interfaces as the tested local backends, so nothing about
how they're *used* differs; run them against `docker-compose.yml` to
validate the backends themselves.
