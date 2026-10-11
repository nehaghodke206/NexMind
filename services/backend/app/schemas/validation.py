from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class ValidationRunCreate(BaseModel):
    status: Optional[str] = Field(
        default="passed",
        pattern="^(queued|running|passed|failed|blocked|error)$",
    )
    test_command: Optional[str] = None
    output: Optional[str] = None
    details: Optional[Dict[str, Any]] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    # Support contract example payload { "result": "failed", ... }
    result: Optional[str] = None
    summary: Optional[str] = None


class ValidationRunResponse(BaseModel):
    id: str
    repair_id: str
    status: str
    test_command: Optional[str] = None
    output: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
