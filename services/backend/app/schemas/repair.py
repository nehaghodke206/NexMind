from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class RepairProposalCreate(BaseModel):
    rationale: str = Field(..., min_length=1)
    strategy: str = Field(
        default="compatibility_adapter",
        pattern="^(compatibility_adapter|callsite_update|pagination_adapter|manual_review|other)$",
    )
    diff_preview: Optional[str] = None
    proposed_changes: Optional[Dict[str, Any]] = Field(default_factory=dict)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    created_by: Optional[str] = None
    patch: Optional[Dict[str, Any]] = None  # to support {"format": "unified_diff", "content": "..."}


class RepairProposalResponse(BaseModel):
    id: str
    incident_id: str
    status: str
    rationale: str
    strategy: str
    diff_preview: Optional[str] = None
    proposed_changes: Dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = None
    created_by: Optional[str] = None
    patch_hash: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
