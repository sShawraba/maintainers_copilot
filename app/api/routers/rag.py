from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.rag_service import RAGService
from typing import Optional, Dict

router = APIRouter(prefix="/rag", tags=["RAG"])

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    use_reranker: bool = True
    metadata_filter: Optional[Dict] = None

class QueryResponse(BaseModel):
    chunks: list[str]
    count: int

@router.post("/retrieve", response_model=QueryResponse)
def retrieve_chunks(req: QueryRequest, db: Session = Depends(get_db)):
    rag = RAGService(db)
    chunks = rag.retrieve(req.question, top_k=req.top_k, use_reranker=req.use_reranker, metadata_filter=req.metadata_filter)
    return QueryResponse(chunks=chunks, count=len(chunks))