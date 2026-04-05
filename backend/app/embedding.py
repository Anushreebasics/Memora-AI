from sentence_transformers import SentenceTransformer, CrossEncoder

from .config import settings


class Embedder:
    def __init__(self) -> None:
        self._model = SentenceTransformer(settings.embedding_model)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


class Reranker:
    def __init__(self) -> None:
        # Load a lightweight cross-encoder model
        self._model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        couples = [[query, doc] for doc in documents]
        scores = self._model.predict(couples)
        return scores.tolist()
