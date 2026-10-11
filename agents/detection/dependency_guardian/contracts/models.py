from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from .findings import CompatibilityClassification, DetectionMode, Finding


class DetectionRequest(BaseModel):
    """Input payload to trigger detection."""

    baseline_spec: Dict[str, Any]
    current_spec: Dict[str, Any]
    dependency_id: Optional[str] = None
    project_id: Optional[str] = None
    mode: Optional[DetectionMode] = None
    context: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class DiffSummary(BaseModel):
    """Aggregate statistics for detection findings."""

    total_findings: int = 0
    breaking_count: int = 0
    potentially_breaking_count: int = 0
    non_breaking_count: int = 0
    unknown_count: int = 0
    by_severity: Dict[str, int] = Field(
        default_factory=lambda: {"critical": 0, "high": 0, "medium": 0, "low": 0}
    )

    @classmethod
    def from_findings(cls, findings: List[Finding]) -> "DiffSummary":
        summary = cls(total_findings=len(findings))
        for f in findings:
            if f.compatibility == CompatibilityClassification.BREAKING:
                summary.breaking_count += 1
            elif f.compatibility == CompatibilityClassification.POTENTIALLY_BREAKING:
                summary.potentially_breaking_count += 1
            elif f.compatibility == CompatibilityClassification.NON_BREAKING:
                summary.non_breaking_count += 1
            elif f.compatibility == CompatibilityClassification.UNKNOWN:
                summary.unknown_count += 1

            sev = f.severity.value
            summary.by_severity[sev] = summary.by_severity.get(sev, 0) + 1
        return summary


class DetectionResult(BaseModel):
    """Structured detection outcome produced by the orchestrator."""

    success: bool
    mode: DetectionMode
    findings: List[Finding]
    summary: DiffSummary
    ai_status: Optional[str] = None  # completed | failed | skipped | not_configured
    ai_error: Optional[str] = None
    fallback_triggered: bool = False
    execution_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ai_insights: Optional[Dict[str, Any]] = None
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
