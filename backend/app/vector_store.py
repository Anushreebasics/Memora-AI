import chromadb
from chromadb.api.models.Collection import Collection

from .config import settings


class VectorStore:
    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(path=settings.chroma_dir)
        self._collection: Collection = self._client.get_or_create_collection(
            name="knowledge_chunks",
            metadata={"hnsw:space": "cosine"},
        )

    def remove_source_chunks(self, source_id: int) -> None:
        self._collection.delete(where={"source_id": source_id})

    def add_chunks(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        if not ids:
            return
        self._collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)

    def query(self, query_embedding: list[float], top_k: int):
        return self._collection.query(query_embeddings=[query_embedding], n_results=top_k)
