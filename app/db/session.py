# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.db.models import Base
import os

SYNC_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/maintainers_copilot"
sync_engine = create_engine(SYNC_DATABASE_URL)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

def get_sync_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create tables (useful for initial setup, but Alembic is preferred)."""
    Base.metadata.create_all(bind=sync_engine)