from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.activity import ActivityEvent


class ActivityRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        project_id: str,
        event_type: str,
        message: str,
        actor_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ActivityEvent:
        event = ActivityEvent(
            project_id=project_id,
            actor_id=actor_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            message=message,
            metadata_json=metadata or {},
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_paginated(
        self, project_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[ActivityEvent], int]:
        query = self.db.query(ActivityEvent).filter(ActivityEvent.project_id == project_id)
        total = query.with_entities(func.count(ActivityEvent.id)).scalar() or 0
        offset = (page - 1) * page_size
        items = query.order_by(ActivityEvent.created_at.desc()).offset(offset).limit(page_size).all()
        return items, total
