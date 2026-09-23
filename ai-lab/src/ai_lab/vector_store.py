"""Raw Chroma walkthrough, no LlamaIndex - useful for seeing what a vector
database actually does under the hood: add texts, embed them, and run a
similarity search, optionally filtered by metadata.
"""

import chromadb

from ai_lab.config import CHROMA_DIR

COLLECTION_NAME = "ai_lab_raw_vectors"


def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    # No embedding_function passed in -> Chroma uses its bundled default
    # (a local ONNX MiniLM model), so this needs no API key.
    return client.get_or_create_collection(COLLECTION_NAME)


def add_texts(texts: list[str], metadatas: list[dict] | None = None):
    collection = get_collection()
    ids = [f"doc-{i}" for i in range(len(texts))]
    collection.add(documents=texts, ids=ids, metadatas=metadatas)
    return collection


def similarity_search(query: str, top_k: int = 3, where: dict | None = None):
    collection = get_collection()
    return collection.query(query_texts=[query], n_results=top_k, where=where)
