from datetime import datetime, timezone
from enum import Enum
import hashlib
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class DetectionMode(str, Enum):
    ALGORITHMIC = "algorithmic"
    AI = "ai"
    HYBRID = "hybrid"


class CompatibilityClassification(str, Enum):
    BREAKING = "breaking"
    POTENTIALLY_BREAKING = "potentially_breaking"
    NON_BREAKING = "non_breaking"
    UNKNOWN = "unknown"


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DetectionSource(str, Enum):
    ALGORITHMIC = "algorithmic"
    AI = "ai"
    HYBRID = "hybrid"


class RuleId(str, Enum):
    PATH_REMOVED = "RULE-PATH-REMOVED"
    METHOD_REMOVED = "RULE-METHOD-REMOVED"
    RESPONSE_FIELD_REMOVED = "RULE-RESPONSE-FIELD-REMOVED"
    FIELD_TYPE_CHANGED = "RULE-FIELD-TYPE-CHANGED"
    REQUIRED_PARAM_ADDED = "RULE-REQUIRED-PARAM-ADDED"
    REQUIRED_FIELD_ADDED = "RULE-REQUIRED-FIELD-ADDED"
    ENUM_VALUE_REMOVED = "RULE-ENUM-VALUE-REMOVED"
    STATUS_CODE_REMOVED = "RULE-STATUS-CODE-REMOVED"
    FIELD_ADDED_OPTIONAL = "RULE-FIELD-ADDED-OPTIONAL"
    UNKNOWN_CHANGE = "RULE-UNKNOWN-CHANGE"


class Finding(BaseModel):
    """Canonical detection finding shared across algorithmic, AI, and hybrid engines."""

    id: str = Field(default_factory=lambda: f"find_{uuid.uuid4()}")
    rule_id: str
    fingerprint: str
    compatibility: CompatibilityClassification
    severity: SeverityLevel
    path: str
    method: Optional[str] = None
    schema_location: str
    previous_value: Optional[Any] = None
    current_value: Optional[Any] = None
    message: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: DetectionSource = DetectionSource.ALGORITHMIC
    review_required: bool = False
    ai_reasoning: Optional[str] = None
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def generate_fingerprint(
        cls,
        path: str,
        method: Optional[str],
        schema_location: str,
        rule_id: str,
    ) -> str:
        """Create a stable, collision-resistant fingerprint for deduplication."""
        norm_method = (method or "*").upper()
        raw = f"{path}:{norm_method}:{schema_location}:{rule_id}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return f"dg:{rule_id.lower()}:{digest}"

    def to_backend_observation(self, scan_id: str, dependency_id: str) -> Dict[str, Any]:
        """Map canonical finding to the FastAPI ObservationCreate schema."""
        obs_type = "response_shape"
        if "param" in self.rule_id.lower() or "request" in self.schema_location.lower():
            obs_type = "tool_schema"
        elif self.compatibility == CompatibilityClassification.UNKNOWN:
            obs_type = "semantic_change"

        return {
            "dependency_id": dependency_id,
            "observation_type": obs_type,
            "endpoint": self.path,
            "method": self.method,
            "observed_at": self.created_at.isoformat() if self.created_at else datetime.now(timezone.utc).isoformat(),
            "fingerprint": self.fingerprint,
            "payload": {
                "finding_id": self.id,
                "rule_id": self.rule_id,
                "compatibility": self.compatibility.value,
                "severity": self.severity.value,
                "schema_location": self.schema_location,
                "previous_value": self.previous_value,
                "current_value": self.current_value,
                "message": self.message,
                "evidence": self.evidence,
                "confidence": self.confidence,
                "source": self.source.value,
                "review_required": self.review_required,
                "ai_reasoning": self.ai_reasoning,
            },
        }

    def to_backend_incident(
        self,
        dependency_id: str,
        observation_ids: Optional[List[str]] = None,
        affected_workflows: Optional[List[str]] = None,
        affected_files: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Map finding to the FastAPI IncidentCreate schema."""
        change_type = "unknown"
        if "RESPONSE-FIELD-REMOVED" in self.rule_id:
            change_type = "field_removed"
        elif "TYPE-CHANGED" in self.rule_id:
            change_type = "type_change"
        elif "STATUS-CODE" in self.rule_id:
            change_type = "status_change"
        elif "PARAM" in self.rule_id or "FIELD-ADDED" in self.rule_id:
            change_type = "tool_schema_change"

        method_prefix = f"[{self.method.upper()}] " if self.method else ""
        title = f"{method_prefix}{self.path} - {self.rule_id}"
        if len(title) > 200:
            title = title[:197] + "..."

        description = self.message
        if self.ai_reasoning:
            description += f"\n\nAI Reasoning: {self.ai_reasoning}"

        return {
            "dependency_id": dependency_id,
            "title": title,
            "description": description,
            "change_type": change_type,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "fingerprint": self.fingerprint,
            "observation_ids": observation_ids or [],
            "affected_workflows": affected_workflows or [],
            "affected_files": affected_files or [],
            "evidence": {
                "finding_id": self.id,
                "rule_id": self.rule_id,
                "compatibility": self.compatibility.value,
                "schema_location": self.schema_location,
                "previous_value": self.previous_value,
                "current_value": self.current_value,
                "source": self.source.value,
                "review_required": self.review_required,
                "evidence_details": self.evidence,
                "ai_reasoning": self.ai_reasoning,
            },
        }
