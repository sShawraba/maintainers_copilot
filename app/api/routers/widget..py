from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.repositories.widget_repository import WidgetRepository
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/widget", tags=["widget"])

class WidgetConfigResponse(BaseModel):
    widget_id: str
    allowed_origins: List[str]
    theme: dict
    greeting: Optional[str]
    enabled_tools: List[str]

@router.get("/config/{widget_id}", response_model=WidgetConfigResponse)
def get_widget_config(widget_id: str, db: Session = Depends(get_db)):
    repo = WidgetRepository(db)
    config = repo.get_by_id(widget_id)
    if not config:
        raise HTTPException(status_code=404, detail="Widget not found")
    return WidgetConfigResponse(
        widget_id=config.widget_id,
        allowed_origins=config.allowed_origins,
        theme=config.theme,
        greeting=config.greeting,
        enabled_tools=config.enabled_tools
    )