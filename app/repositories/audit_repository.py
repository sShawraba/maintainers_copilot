from sqlalchemy.orm import Session
from app.db.models import AuditLog

class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(self, actor: str, action: str, target: str = None, meta_data: dict = None):
        log_entry = AuditLog(
            actor=actor,
            action=action,
            target=target,
            meta_data=meta_data or {}
        )
        self.db.add(log_entry)
        self.db.commit()
        return log_entry

    def get_logs(self, limit: int = 100):
        return self.db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()