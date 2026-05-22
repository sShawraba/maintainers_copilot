# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.db.models import Base
import os

# Get database URL from environment or Vault later
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/maintainers_copilot")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """Dependency for FastAPI to get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create tables (useful for initial setup, but Alembic is preferred)."""
    Base.metadata.create_all(bind=engine)