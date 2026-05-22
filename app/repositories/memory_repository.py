# app/repositories/memory_repository.py
from sqlalchemy.orm import Session
from app.db.models import LongTermMemory, MemoryTypeEnum

class MemoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_memory(self, user_id: str, memory_type: MemoryTypeEnum, content: str, embedding: list = None):
        memory = LongTermMemory(
            user_id=user_id,
            memory_type=memory_type,
            content=content,
            embedding=embedding
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def get_memories_by_user(self, user_id: str, memory_type: MemoryTypeEnum = None):
        query = self.db.query(LongTermMemory).filter(LongTermMemory.user_id == user_id)
        if memory_type:
            query = query.filter(LongTermMemory.memory_type == memory_type)
        return query.order_by(LongTermMemory.created_at.desc()).all()

    def delete_memory(self, memory_id: int, user_id: str) -> bool:
        memory = self.db.query(LongTermMemory).filter(
            LongTermMemory.id == memory_id,
            LongTermMemory.user_id == user_id
        ).first()
        if memory:
            self.db.delete(memory)
            self.db.commit()
            return True
        return False