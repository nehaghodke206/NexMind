from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ScanCreate(BaseModel):
    dependency_id: Optional[str] = None
    initiated_by: Optional[str] = None
    scan_type: str = Field(default="full", pattern="^(full|targeted)$")


class ScanCompleteRequest(BaseModel):
    status: str = Field(..., pattern="^(completed|failed)$")
    summary: Optional[str] = None
    error_message: Optional[str] = None


class ScanRunResponse(BaseModel):
    id: str
    project_id: str
    dependency_id: Optional[str] = None
    initiated_by: Optional[str] = None
    status: str
    summary: Optional[str] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
