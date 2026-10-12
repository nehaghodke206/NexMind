from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class IncidentCreate(BaseModel):
    dependency_id: Optional[str] = None
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    change_type: str = Field(
        default="unknown",
    )
    severity: str = Field(
        default="medium",
        pattern="^(low|medium|high|critical|blocked)$",
    )
    provenance: Optional[str] = "contract_diff"
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    fingerprint: Optional[str] = None
    recommended_action: Optional[str] = None
    observation_ids: Optional[List[str]] = Field(default_factory=list)
    affected_workflows: Optional[List[str]] = Field(default_factory=list)
    affected_files: Optional[List[str]] = Field(default_factory=list)
    evidence: Optional[Dict[str, Any]] = None


class IncidentUpdate(BaseModel):
    status: Optional[str] = Field(
        default=None,
        pattern="^(open|acknowledged|resolved|reopened|triaged|in_progress|awaiting_review|dismissed)$",
    )
    assignee_id: Optional[str] = None
    review_notes: Optional[str] = None
    resolution_notes: Optional[str] = None
    recommended_action: Optional[str] = None
    severity: Optional[str] = Field(
        default=None,
        pattern="^(low|medium|high|critical|blocked)$",
    )


class IncidentTransitionRequest(BaseModel):
    notes: Optional[str] = None
    actor_id: Optional[str] = None


class IncidentEventResponse(BaseModel):
    id: str
    incident_id: str
    event_type: str
    actor_id: Optional[str] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    message: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentResponse(BaseModel):
    id: str
    project_id: str
    dependency_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    change_type: str
    severity: str
    status: str
    provenance: str = "contract_diff"
    confidence: Optional[float] = None
    occurrence_count: int = 1
    fingerprint: Optional[str] = None
    recommended_action: Optional[str] = None
    resolution_notes: Optional[str] = None
    review_notes: Optional[str] = None
    assignee_id: Optional[str] = None
    affected_workflows: List[str] = Field(default_factory=list)
    affected_files: List[str] = Field(default_factory=list)
    evidence_summary: Optional[str] = None
    first_detected_at: datetime
    last_observed_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    reopened_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentListResponse(BaseModel):
    items: List[IncidentResponse]
    page: int
    page_size: int
    total: int
