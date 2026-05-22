import json
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session
from app.repositories.rag_repository import RAGChunkRepository

class RAGService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RAGChunkRepository(db)
        self.dense_model = SentenceTransformer("all-MiniLM-L6-v2")  # same as ingestion
        self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.bm25 = None
        self._load_bm25_index()

    def _load_bm25_index(self):
        """Load all chunks from DB and build BM25 index (sparse retrieval)."""
        chunks = self.db.query(RAGChunk).all()
        tokenized_chunks = [self._tokenize(chunk.text) for chunk in chunks]
        self.bm25 = BM25Okapi(tokenized_chunks)
        self.chunks = chunks  # keep for mapping

    def _tokenize(self, text: str) -> List[str]:
        """Simple whitespace tokenizer; improve with nltk if needed."""
        return text.lower().split()

    def hybrid_search(self, query: str, top_k: int = 10, alpha: float = 0.5, metadata_filter: Optional[Dict] = None):
        """
        alpha: weight for dense (0=only sparse, 1=only dense)
        metadata_filter: e.g., {"type": "issue", "class": "bug"}
        """
        # 1. Dense retrieval: cosine similarity
        query_emb = self.dense_model.encode(query)
        dense_results = self.repo.similarity_search(query_emb.tolist(), top_k=top_k*2, filter_meta_data=metadata_filter)
        dense_scores = [1 - chunk.embedding.cosine_distance(query_emb) for chunk in dense_results]  # convert distance to similarity

        # 2. Sparse retrieval: BM25 scores
        tokenized_query = self._tokenize(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)
        # Get top sparse results
        sparse_indices = np.argsort(bm25_scores)[-top_k*2:][::-1]
        sparse_chunks = [self.chunks[i] for i in sparse_indices]
        sparse_scores = [bm25_scores[i] for i in sparse_indices]

        # 3. Merge (simple reciprocal rank fusion or weighted sum)
        # We'll implement weighted sum for simplicity
        all_chunks = list(set(dense_results + sparse_chunks))
        combined_scores = {}
        for chunk in all_chunks:
            dense_score = next((s for c, s in zip(dense_results, dense_scores) if c.id == chunk.id), 0)
            sparse_score = next((s for c, s in zip(sparse_chunks, sparse_scores) if c.id == chunk.id), 0)
            combined_scores[chunk.id] = alpha * dense_score + (1 - alpha) * (sparse_score / (max(sparse_scores)+1e-6))
        ranked_ids = sorted(combined_scores, key=combined_scores.get, reverse=True)[:top_k]
        return [next(c for c in all_chunks if c.id == i) for i in ranked_ids]

    def rerank(self, query: str, chunks: List[RAGChunk], top_k: int = 5) -> List[RAGChunk]:
        """Re-rank chunks using cross-encoder."""
        pairs = [(query, chunk.text) for chunk in chunks]
        scores = self.reranker.predict(pairs)
        ranked_indices = np.argsort(scores)[::-1][:top_k]
        return [chunks[i] for i in ranked_indices]

    def retrieve(self, query: str, top_k: int = 5, use_reranker: bool = True, metadata_filter: Optional[Dict] = None) -> List[str]:
        """Full pipeline: hybrid search -> optional rerank -> return texts."""
        candidates = self.hybrid_search(query, top_k=10, metadata_filter=metadata_filter)
        if use_reranker:
            candidates = self.rerank(query, candidates, top_k=top_k)
        else:
            candidates = candidates[:top_k]
        return [chunk.text for chunk in candidates]