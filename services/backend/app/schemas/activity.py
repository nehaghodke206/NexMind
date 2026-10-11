from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ActivityEventResponse(BaseModel):
    id: str
    project_id: str
    actor_id: Optional[str] = None
    event_type: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="wrap")
    @classmethod
    def handle_orm_metadata(cls, v: Any, handler: Any) -> Any:
        if hasattr(v, "metadata_json"):
            return cls(
                id=v.id,
                project_id=v.project_id,
                actor_id=v.actor_id,
                event_type=v.event_type,
                resource_type=v.resource_type,
                resource_id=v.resource_id,
                message=v.message,
                metadata=v.metadata_json or {},
                created_at=v.created_at,
            )
        return handler(v)


class ActivityEventListResponse(BaseModel):
    items: List[ActivityEventResponse]
    page: int
    page_size: int
    total: int
