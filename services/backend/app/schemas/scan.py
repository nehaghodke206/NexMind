from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ScanCreate(BaseModel):
    dependency_id: Optional[str] = None
    initiated_by: Optional[str] = None
    scan_type: str = Field(default="full", pattern="^(full|targeted|codebase|contract_drift|live_probe)$")
    detection_mode: Optional[str] = Field(default="algorithmic", pattern="^(algorithmic|hybrid|ai)$")
    trigger_type: Optional[str] = "manual"


class ScanCompleteRequest(BaseModel):
    status: str = Field(..., pattern="^(succeeded|partial|failed|canceled|completed)$")
    summary: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    summary_counts: Optional[Dict[str, Any]] = None


class ScanIngestRequest(BaseModel):
    """
    Ingest a locally executed scan from VS Code or CI, storing real detector results
    and triggering idempotent incident synchronization.
    """
    client_run_id: Optional[str] = None
    scan_type: str = "full"
    detection_mode: str = Field(default="algorithmic", pattern="^(algorithmic|hybrid|ai)$")
    capabilities_executed: List[str] = Field(default_factory=list)
    duration_seconds: Optional[float] = None
    summary_counts: Dict[str, Any] = Field(default_factory=dict)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    inventory: Optional[Dict[str, Any]] = None
    status: str = Field(default="succeeded", pattern="^(succeeded|partial|failed|canceled)$")
    error_message: Optional[str] = None
    scanner_version: Optional[str] = "0.2.0"
    repository_revision: Optional[str] = None
    initiated_by: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ScanRunResponse(BaseModel):
    id: str
    project_id: str
    dependency_id: Optional[str] = None
    initiated_by: Optional[str] = None
    scan_type: str = "full"
    detection_mode: Optional[str] = "algorithmic"
    capabilities_executed: List[str] = Field(default_factory=list)
    status: str
    duration_seconds: Optional[float] = None
    summary_counts: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    error_message: Optional[str] = None
    is_local: bool = False
    sync_status: str = "synchronized"
    client_run_id: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ScanListResponse(BaseModel):
    items: List[ScanRunResponse]
    total: int
