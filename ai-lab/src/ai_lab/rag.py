"""Minimal RAG pipeline: LlamaIndex + Chroma for retrieval, Claude for the answer.

LlamaIndex handles chunking, embedding, and similarity search; we skip its
LLM abstraction and call the Anthropic SDK directly for generation, so the
one thing actually talking to Claude is documented, official SDK code.
"""

import chromadb
from llama_index.core import Settings, SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from ai_lab.claude import ask_claude
from ai_lab.config import CHROMA_DIR, EMBED_MODEL_NAME, SAMPLE_DOCS_DIR

Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)
Settings.llm = None  # generation goes through ai_lab.claude, not a LlamaIndex LLM wrapper

COLLECTION_NAME = "ai_lab_docs"

RAG_SYSTEM_PROMPT = (
    "Answer the user's question using ONLY the numbered context chunks "
    "below. Cite the chunk number(s) you used, like [1] or [1][3]. If the "
    "context doesn't contain the answer, say so instead of guessing."
)


def _vector_store() -> ChromaVectorStore:
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(COLLECTION_NAME)
    return ChromaVectorStore(chroma_collection=collection)


def build_index(docs_dir=SAMPLE_DOCS_DIR) -> VectorStoreIndex:
    """Chunk + embed every file in docs_dir and (re)populate the Chroma collection."""
    documents = SimpleDirectoryReader(str(docs_dir)).load_data()
    storage_context = StorageContext.from_defaults(vector_store=_vector_store())
    return VectorStoreIndex.from_documents(documents, storage_context=storage_context)


def load_index() -> VectorStoreIndex:
    """Load an index from an already-populated Chroma collection (no re-embedding)."""
    return VectorStoreIndex.from_vector_store(_vector_store())


def retrieve(question: str, index: VectorStoreIndex, top_k: int = 3):
    retriever = index.as_retriever(similarity_top_k=top_k)
    return retriever.retrieve(question)


def answer(question: str, index: VectorStoreIndex, top_k: int = 3) -> str:
    nodes = retrieve(question, index, top_k=top_k)
    context = "\n\n".join(f"[{i + 1}] {node.get_content()}" for i, node in enumerate(nodes))
    prompt = f"Context:\n{context}\n\nQuestion: {question}"
    return ask_claude(prompt, system=RAG_SYSTEM_PROMPT, max_tokens=1024)
