# app/repositories/widget_repository.py
from sqlalchemy.orm import Session
from app.db.models import WidgetConfig

class WidgetRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, widget_id: str) -> WidgetConfig:
        return self.db.query(WidgetConfig).filter(WidgetConfig.widget_id == widget_id).first()

    def create(self, widget_id: str, allowed_origins: list, theme: dict, greeting: str, enabled_tools: list, created_by: str):
        config = WidgetConfig(
            widget_id=widget_id,
            allowed_origins=allowed_origins,
            theme=theme,
            greeting=greeting,
            enabled_tools=enabled_tools,
            created_by=created_by
        )
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def update(self, widget_id: str, **kwargs):
        config = self.get_by_id(widget_id)
        if not config:
            return None
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        self.db.commit()
        self.db.refresh(config)
        return config

    def delete(self, widget_id: str) -> bool:
        config = self.get_by_id(widget_id)
        if config:
            self.db.delete(config)
            self.db.commit()
            return True
        return False