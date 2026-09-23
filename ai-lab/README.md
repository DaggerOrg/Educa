# ai-lab

A practice sandbox for AI engineering fundamentals: retrieval-augmented
generation (RAG), vector search, and knowledge graphs. Separate from the
rest of this repo (Educa's curriculum-builder app) - nothing here depends
on `backend/` or `frontend/`.

## Stack

- **Claude** (`anthropic` SDK) for generation - called directly, not through
  a framework wrapper, so the LLM call itself always matches the official SDK.
- **LlamaIndex** for chunking, embedding, and retrieval orchestration.
- **Chroma** as the local vector store (runs on disk, no external service).
- **NetworkX** for an in-memory knowledge graph.
- Embeddings run locally via `sentence-transformers` (no API key needed for
  the vector-search or knowledge-graph examples).

## Setup

```bash
cd ai-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .          # makes the `ai_lab` package importable
cp .env.example .env      # then fill in ANTHROPIC_API_KEY
```

If you use `ant auth login` instead, you can skip the `.env` file - the
Anthropic SDK picks up the active profile automatically.

## Examples

Each script is runnable standalone and builds on the last:

| Script | What it shows | Needs an API key? |
|---|---|---|
| [`examples/01_vector_search.py`](examples/01_vector_search.py) | Embed text into Chroma, run similarity search, filter by metadata | No |
| [`examples/02_basic_rag.py`](examples/02_basic_rag.py) | Full RAG: ingest `data/sample_docs/`, retrieve, ask Claude | Yes |
| [`examples/03_knowledge_graph.py`](examples/03_knowledge_graph.py) | Build a concept graph with NetworkX, query neighbors/paths/centrality | No |
| [`examples/04_graph_rag.py`](examples/04_graph_rag.py) | GraphRAG: merge graph context + vector context into one Claude prompt | Yes |

```bash
python examples/01_vector_search.py
python examples/02_basic_rag.py
python examples/03_knowledge_graph.py
python examples/04_graph_rag.py
```

## Layout

```
ai-lab/
  data/sample_docs/     # small text files the RAG examples ingest
  src/ai_lab/            # reusable pieces: claude.py, rag.py, vector_store.py, graph_store.py
  examples/               # runnable, numbered walkthroughs
  chroma_db/              # created on first run - local Chroma persistence (gitignored)
```

`src/ai_lab/rag.py` and `src/ai_lab/vector_store.py` both use Chroma, but
show two different levels of abstraction: `vector_store.py` talks to Chroma
directly (good for seeing what a vector DB actually does), while `rag.py`
goes through LlamaIndex for chunking + indexing (good for seeing how a real
RAG pipeline is put together).
