"""Audit logger recording lifecycle events in SQLite."""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from .db import Database


class AuditLogger:
    def __init__(self, db: Database):
        self.db = db

    def log(self, actor_action: str, target_type: str, target_id: str, details: Dict[str, Any]):
        event = {
            "id": f"aud_{uuid.uuid4().hex[:8]}",
            "actor_action": actor_action,
            "target_type": target_type,
            "target_id": target_id,
            "details": details,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.db.save_audit_event(event)
