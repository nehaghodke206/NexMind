from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RepairApplicationCreate(BaseModel):
    agent_id: Optional[str] = None
    status: str = Field(..., pattern="^(applied|failed|cancelled)$")
    workspace_reference: Optional[str] = None
    message: Optional[str] = None


class RepairApplicationResponse(BaseModel):
    id: str
    repair_id: str
    agent_id: Optional[str] = None
    status: str
    workspace_reference: Optional[str] = None
    message: Optional[str] = None
    reported_at: datetime

    model_config = ConfigDict(from_attributes=True)
