# app/domain/rag.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class RetrievalRequest(BaseModel):
    """Request model for RAG retrieval endpoint."""
    question: str = Field(..., description="User's question", min_length=1)
    top_k: int = Field(5, description="Number of final chunks to return", ge=1, le=20)
    use_reranker: bool = Field(True, description="Apply cross-encoder reranking")
    use_hybrid: bool = Field(True, description="Use hybrid search (dense+sparse)")
    metadata_filter: Optional[Dict[str, str]] = Field(
        None,
        description="Filter by chunk metadata, e.g. {'type': 'issue', 'class': 'bug'}"
    )
    use_hyde: bool = Field(False, description="Apply HyDE query transformation")

class ChunkResult(BaseModel):
    """Single retrieved chunk with metadata and relevance score."""
    text: str
    metadata: Dict[str, Any]
    score: Optional[float] = Field(None, description="Relevance score (higher = more relevant)")

class RetrievalResponse(BaseModel):
    """Response model for RAG retrieval."""
    chunks: List[ChunkResult]
    total: int