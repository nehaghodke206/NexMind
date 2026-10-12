"""
Data models and contracts for External API Intelligence and Safe Live Validation.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from ..contracts.findings import (
    CompatibilityClassification,
    DetectionProvenance,
    DetectionSource,
    Finding,
    SeverityLevel,
)


class ProbeStatus(str, Enum):
    """Categorized status for live API validation results."""
    REACHABLE = "reachable"
    AUTH_FAILURE = "auth_failure"
    CLIENT_ERROR = "client_error"
    SERVER_FAILURE = "server_failure"
    UNREACHABLE = "unreachable"
    CONTRACT_MISMATCH = "contract_mismatch"
    SECURITY_BLOCKED = "security_blocked"


class LiveProbeEndpoint(BaseModel):
    """Configuration for a single, safe, read-only endpoint check."""
    id: str
    service_name: str
    base_url: str
    path: str
    method: str = "GET"
    headers: Dict[str, str] = Field(default_factory=dict)
    auth_env_var: Optional[str] = None
    expected_contract: Optional[str] = None
    expected_status_code: int = 200
    expected_fields: List[str] = Field(default_factory=list)
    known_values: Dict[str, Any] = Field(default_factory=dict)
    is_safe_readonly: bool = True

    model_config = ConfigDict(extra="ignore")


class LiveValidationOptions(BaseModel):
    """Bounds, safety limits, and execution controls for live API validation."""
    timeout_seconds: float = 3.0
    max_concurrency: int = 3
    max_requests: int = 20
    rate_limit_per_second: float = 10.0
    max_response_bytes: int = 1_000_000  # 1 MB
    allow_private_network: bool = True
    blocked_hosts: List[str] = Field(
        default_factory=lambda: ["169.254.169.254", "metadata.google.internal"]
    )

    model_config = ConfigDict(extra="ignore")


class LiveProbeResult(BaseModel):
    """Detailed observation of an executed safe HTTP probe."""
    endpoint_id: str
    service_name: str
    url: str
    method: str
    status_code: int
    status: ProbeStatus
    latency_ms: float
    error_message: Optional[str] = None
    fingerprint: str
    safe_headers: Dict[str, str] = Field(default_factory=dict)
    structural_schema: Optional[Dict[str, Any]] = None
    observed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    findings: List[Finding] = Field(default_factory=list)
    provenance: DetectionProvenance = DetectionProvenance.LIVE_PROBE

    model_config = ConfigDict(extra="ignore")


class LiveValidationReport(BaseModel):
    """Comprehensive report summarizing external API intelligence and live validation."""
    total_probes: int = 0
    reachable_count: int = 0
    auth_failure_count: int = 0
    client_error_count: int = 0
    server_failure_count: int = 0
    unreachable_count: int = 0
    contract_mismatch_count: int = 0
    security_blocked_count: int = 0
    duration_seconds: float = 0.0
    results: List[LiveProbeResult] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)
    config_source: Optional[str] = None
    mode: str = "algorithmic"
    ai_status: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    ai_error: Optional[str] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    model_config = ConfigDict(extra="ignore")
