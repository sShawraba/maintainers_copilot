from fastapi import APIRouter, Depends, HTTPException
from app.domain.rag import RetrievalRequest, RetrievalResponse, ChunkResult
from app.services.rag_service import RAGService
from app.db.session import get_sync_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/rag", tags=["RAG"])

def get_rag_service(db: Session = Depends(get_sync_db)):
    from app.model_loader import dense_model, reranker
    return RAGService(db, dense_model, reranker)

@router.post("/retrieve", response_model=RetrievalResponse)
def retrieve(request: RetrievalRequest, rag_service: RAGService = Depends(get_rag_service)):
    try:
        results = rag_service.retrieve(
            query=request.question,
            top_k=request.top_k,
            use_reranker=request.use_reranker,
            use_hybrid=request.use_hybrid,
            metadata_filter=request.metadata_filter
        )
        chunks = [ChunkResult(text=t, metadata=m, score=s) for t, m, s in results]
        return RetrievalResponse(chunks=chunks, total=len(chunks))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")