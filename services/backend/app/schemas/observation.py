from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ObservationCreate(BaseModel):
    dependency_id: str
    observation_type: str = Field(..., pattern="^(response_shape|status_code|latency|pagination|tool_schema|semantic_change|other)$")
    endpoint: Optional[str] = None
    method: Optional[str] = None
    observed_at: Optional[datetime] = None
    payload: Dict[str, Any]
    fingerprint: Optional[str] = None


class ObservationBatchCreate(BaseModel):
    observations: List[ObservationCreate]


class ObservationBatchResponse(BaseModel):
    accepted_count: int
    observation_ids: List[str]


class ObservationResponse(BaseModel):
    id: str
    scan_id: str
    dependency_id: str
    observation_type: str
    endpoint: Optional[str] = None
    method: Optional[str] = None
    observed_at: datetime
    payload: Dict[str, Any]
    fingerprint: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
