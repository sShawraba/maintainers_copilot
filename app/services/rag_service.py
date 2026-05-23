# app/services/rag_service.py
import os
import json
import hashlib
from functools import lru_cache
from typing import List, Dict, Optional, Any, Tuple
import numpy as np

from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session

from app.db.models import RAGChunk
from app.repositories.rag_repository import RAGChunkRepository

from groq import Groq 
from dotenv import load_dotenv

load_dotenv()

class RAGService:
    """RAG retrieval service with caching and dependency injection."""

    def __init__(self, db: Session, dense_model, reranker):
        self.db = db
        self.repo = RAGChunkRepository(db)
        self.dense_model = dense_model   # no longer loads inside
        self.reranker = reranker
        self._bm25 = None
        self._chunks = None
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def _get_bm25(self):
        """Lazy load BM25 index and chunk list."""
        if self._bm25 is None:
            chunks = self.db.query(RAGChunk).all()
            tokenized_chunks = [self._tokenize(chunk.text) for chunk in chunks]
            self._bm25 = BM25Okapi(tokenized_chunks)
            self._chunks = chunks
        return self._bm25, self._chunks

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer; can be enhanced with NLTK."""
        return text.lower().split()

    def _compute_query_hash(self, query: str, top_k: int, use_reranker: bool, use_hybrid: bool, metadata_filter: Optional[Dict]) -> str:
        """Generate cache key from request parameters."""
        key = f"{query}|{top_k}|{use_reranker}|{use_hybrid}|{json.dumps(metadata_filter, sort_keys=True)}"
        return hashlib.md5(key.encode()).hexdigest()

    @lru_cache(maxsize=128)
    def _cached_retrieve(self, query_hash: str, query: str, top_k: int, use_reranker: bool, use_hybrid: bool, metadata_filter_json: str) -> List[Tuple[str, Dict, float]]:
        """Internal cached method. The cache key is query_hash; other args are for context."""
        # Parse metadata filter back to dict
        metadata_filter = json.loads(metadata_filter_json) if metadata_filter_json else None

        # Step 1: Retrieve candidates
        if use_hybrid:
            candidates = self._hybrid_search(query, top_k=top_k*2, metadata_filter=metadata_filter)
        else:
            query_emb = self.dense_model.encode(query)
            candidates = self.repo.similarity_search(query_emb.tolist(), top_k=top_k*2, filter_meta_data=metadata_filter)

        # Step 2: Rerank
        if use_reranker:
            candidates = self._rerank(query, candidates, top_k=top_k)
        else:
            candidates = candidates[:top_k]

        # Step 3: Compute scores (simple placeholder)
        results = []
        for chunk in candidates:
            # Simple score: cosine similarity if dense, else reranker score or 0.5
            score = self._compute_score(query, chunk)
            results.append((chunk.text, chunk.meta_data, score))
        return results

    def retrieve(self, query: str, top_k: int = 5, use_reranker: bool = True,
             use_hybrid: bool = True, use_hyde: bool = False,
             metadata_filter: Optional[Dict] = None) -> List[Tuple[str, Dict, float]]:
        # Transform query if HyDE enabled
        original_query = query
        if use_hyde:
            query = self._generate_hypothetical_answer(query)
            print(f"[HyDE] Transformed query to: {query[:100]}...")  # optional logging

        query_hash = self._compute_query_hash(original_query, top_k, use_reranker, use_hybrid, metadata_filter)
        metadata_json = json.dumps(metadata_filter, sort_keys=True) if metadata_filter else None
        return self._cached_retrieve(query_hash, query, top_k, use_reranker, use_hybrid, metadata_json)

    def _hybrid_search(self, query: str, top_k: int = 10, alpha: float = 0.5, metadata_filter: Optional[Dict] = None) -> List[RAGChunk]:
        """Hybrid dense + sparse retrieval."""
        import numpy as np

        def cosine_sim(a, b):
            """Compute cosine similarity between two vectors."""
            a = np.array(a)
            b = np.array(b)
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)

        # 1. Dense retrieval
        query_emb = self.dense_model.encode(query)
        dense_results = self.repo.similarity_search(query_emb.tolist(), top_k=top_k*2, filter_meta_data=metadata_filter)
        dense_scores = [cosine_sim(chunk.embedding, query_emb) for chunk in dense_results]

        # 2. Sparse BM25
        bm25, chunks = self._get_bm25()
        tokenized_query = self._tokenize(query)
        bm25_scores = bm25.get_scores(tokenized_query)
        sparse_indices = np.argsort(bm25_scores)[-top_k*2:][::-1]
        sparse_chunks = [chunks[i] for i in sparse_indices]
        sparse_scores = [bm25_scores[i] for i in sparse_indices]

        # 3. Merge (weighted sum)
        all_chunks = list(set(dense_results + sparse_chunks))
        combined = {}
        max_sparse = max(bm25_scores) if len(bm25_scores) > 0 and max(bm25_scores) > 0 else 1.0

        for chunk in all_chunks:
            dense_score = 0.0
            if chunk in dense_results:
                idx = dense_results.index(chunk)
                dense_score = dense_scores[idx]

            sparse_score = 0.0
            if chunk in sparse_chunks:
                idx = sparse_chunks.index(chunk)
                sparse_score = sparse_scores[idx]

            norm_sparse = sparse_score / max_sparse if max_sparse > 0 else 0.0
            combined[chunk.id] = alpha * dense_score + (1 - alpha) * norm_sparse

        sorted_ids = sorted(combined, key=combined.get, reverse=True)[:top_k]
        return [next(c for c in all_chunks if c.id == i) for i in sorted_ids]

    def _rerank(self, query: str, chunks: List[RAGChunk], top_k: int = 5) -> List[RAGChunk]:
        """Rerank using cross-encoder."""
        pairs = [(query, chunk.text) for chunk in chunks]
        scores = self.reranker.predict(pairs)
        ranked_indices = np.argsort(scores)[::-1][:top_k]
        return [chunks[i] for i in ranked_indices]

    def _compute_score(self, query: str, chunk: RAGChunk) -> float:
        return 0.5  # placeholder

    def _generate_hypothetical_answer(self, query: str) -> str:
        """Generate a hypothetical answer to use as query embedding."""
        prompt = f"""Given the question, write a short, clear hypothetical answer that would appear in documentation or a resolved issue.

Question: {query}
Hypothetical answer:"""
        response = self.groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )
        return response.choices[0].message.content.strip()