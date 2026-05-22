from sqlalchemy.orm import Session
from app.db.models import RAGChunk

class RAGChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, text: str, meta_data: dict, embedding: list) -> RAGChunk:
        chunk = RAGChunk(
            text=text,
            meta_data=meta_data,
            embedding=embedding
        )
        self.db.add(chunk)
        self.db.commit()
        self.db.refresh(chunk)
        return chunk

    def create_batch(self, chunks: list) -> list:
        """chunks: list of (text, meta_data, embedding) tuples"""
        db_chunks = [RAGChunk(text=t, meta_data=m, embedding=e) for t, m, e in chunks]
        self.db.add_all(db_chunks)
        self.db.commit()
        return db_chunks

    def get_by_id(self, chunk_id: int) -> RAGChunk:
        return self.db.query(RAGChunk).filter(RAGChunk.id == chunk_id).first()

    def similarity_search(self, query_embedding: list, top_k: int = 5, filter_meta_data: dict = None):
        query = self.db.query(RAGChunk).order_by(RAGChunk.embedding.cosine_distance(query_embedding))
        if filter_meta_data:
            for key, value in filter_meta_data.items():
                query = query.filter(RAGChunk.meta_data[key].astext == str(value))
        return query.limit(top_k).all()

    def delete_all(self):
        self.db.query(RAGChunk).delete()
        self.db.commit()