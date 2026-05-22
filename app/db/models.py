# app/db/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import enum

Base = declarative_base()

class RoleEnum(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"

class MemoryTypeEnum(str, enum.Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"

class RAGChunk(Base):
    __tablename__ = "rag_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Text, nullable=False)
    meta_data = Column(JSON, nullable=False, default=dict)  # renamed from 'metadata'
    embedding = Column(Vector(384))
    created_at = Column(DateTime, server_default=func.now())

class LongTermMemory(Base):
    __tablename__ = "long_term_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    memory_type = Column(SQLEnum(MemoryTypeEnum), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    target = Column(String, nullable=True)
    meta_data = Column(JSON, nullable=True)  # renamed
    timestamp = Column(DateTime, server_default=func.now())

class WidgetConfig(Base):
    __tablename__ = "widget_configs"

    widget_id = Column(String, primary_key=True)
    allowed_origins = Column(JSON, nullable=False, default=list)
    theme = Column(JSON, nullable=False, default=dict)
    greeting = Column(String, nullable=True)
    enabled_tools = Column(JSON, nullable=False, default=list)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())