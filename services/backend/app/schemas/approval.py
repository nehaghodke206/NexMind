from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RepairApprovalCreate(BaseModel):
    reviewer_id: str
    decision: str = Field(default="approved", pattern="^(approved)$")
    comment: Optional[str] = None
    patch_hash: Optional[str] = None


class RepairRejectionCreate(BaseModel):
    reviewer_id: str
    reason: str = Field(..., min_length=1)


class RepairApprovalResponse(BaseModel):
    id: str
    repair_id: str
    reviewer_id: str
    decision: str
    comment: Optional[str] = None
    decided_at: datetime

    model_config = ConfigDict(from_attributes=True)
