"""Data models and API schemas for Dependency Guardian."""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class ChangeSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


class RepairStatus(str, Enum):
    DETECTED = "detected"
    PROPOSED = "proposed"
    PREVIEWED = "previewed"
    VALIDATING = "validating"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    BLOCKED_UNCERTAIN = "blocked_uncertain"
    APPLY_FAILED = "apply_failed"
    ROLLED_BACK = "rolled_back"


class ProbeResult(BaseModel):
    probe_id: str
    dependency_id: str
    method: str
    path: str
    status_code: int
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Any
    latency_ms: float
    observed_at: str
    fingerprint: str
    error: Optional[str] = None


class BaselineItem(BaseModel):
    id: str
    dependency_id: str
    probe_id: str
    version: int
    fingerprint: str
    raw_response: Any
    created_at: str
    created_by_action: str = "manual_baseline"


class ChangeItem(BaseModel):
    id: str
    scan_id: str
    dependency_id: str
    probe_id: str
    change_type: str
    severity: ChangeSeverity
    evidence: Dict[str, Any]
    status: str = "detected"
    created_at: str


class ImpactItem(BaseModel):
    workflow_id: str
    workflow_name: str
    source_files: List[str]
    tests: List[str]
    affected_fields: List[str]
    reason: str


class RepairProposal(BaseModel):
    id: str
    change_id: str
    repair_type: str
    target_file: str
    original_code_snippet: str
    proposed_code_snippet: str
    diff: str
    evidence: Dict[str, Any]
    assumptions: List[str]
    confidence: float
    status: RepairStatus
    created_at: str
    error_message: Optional[str] = None


class ValidationResult(BaseModel):
    id: str
    repair_id: str
    command: str
    exit_code: int
    output_summary: str
    duration_ms: float
    status: str
    started_at: str


class ScanResult(BaseModel):
    scan_id: str
    status: str
    services_checked: int
    changes_detected: int
    started_at: str
    duration_ms: float
    changes: List[ChangeItem] = Field(default_factory=list)


class AuditEvent(BaseModel):
    id: str
    actor_action: str
    target_type: str
    target_id: str
    details: Dict[str, Any]
    created_at: str
