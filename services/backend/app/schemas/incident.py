from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class IncidentCreate(BaseModel):
    dependency_id: str
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    change_type: str = Field(
        default="unknown",
        pattern="^(field_rename|field_removed|type_change|pagination_change|status_change|semantic_change|tool_schema_change|unknown)$",
    )
    severity: str = Field(
        default="medium",
        pattern="^(low|medium|high|critical)$",
    )
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    fingerprint: Optional[str] = None
    observation_ids: Optional[List[str]] = Field(default_factory=list)
    affected_workflows: Optional[List[str]] = Field(default_factory=list)
    affected_files: Optional[List[str]] = Field(default_factory=list)
    evidence: Optional[Dict[str, Any]] = None


class IncidentUpdate(BaseModel):
    status: Optional[str] = Field(
        default=None,
        pattern="^(open|triaged|in_progress|awaiting_review|resolved|dismissed)$",
    )
    assignee_id: Optional[str] = None
    review_notes: Optional[str] = None
    severity: Optional[str] = Field(
        default=None,
        pattern="^(low|medium|high|critical)$",
    )


class IncidentResponse(BaseModel):
    id: str
    project_id: str
    dependency_id: str
    title: str
    description: Optional[str] = None
    change_type: str
    severity: str
    status: str
    confidence: Optional[float] = None
    assignee_id: Optional[str] = None
    review_notes: Optional[str] = None
    affected_workflows: List[str] = Field(default_factory=list)
    affected_files: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentListResponse(BaseModel):
    items: List[IncidentResponse]
    page: int
    page_size: int
    total: int
