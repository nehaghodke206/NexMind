from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ProjectSummaryResponse(BaseModel):
    project_id: str
    dependency_count: int
    open_incident_count: int
    pending_review_count: int
    validation_pass_count: int
    validation_fail_count: int
    last_scan_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
