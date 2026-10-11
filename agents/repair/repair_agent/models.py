from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from .settings import get_settings


class ValidationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class RepairStatus(str, Enum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"
    REJECTED = "rejected"
    ERROR = "error"
    NEEDS_REVIEW = "needs_review"


class FindingInput(BaseModel):
    """Normalized finding representation accepted by the Repair Agent."""

    id: str = Field(description="Unique identifier for the finding")
    rule_id: str = Field(description="Canonical rule ID e.g. RULE-FIELD-TYPE-CHANGED")
    path: str = Field(description="Affected API endpoint path")
    method: Optional[str] = Field(default=None, description="HTTP method if applicable")
    schema_location: Optional[str] = Field(default="", description="Pointer to changed schema property")
    previous_value: Optional[Any] = Field(default=None, description="Baseline value")
    current_value: Optional[Any] = Field(default=None, description="Observed current value")
    message: Optional[str] = Field(default="", description="Explanation of detection finding")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Structured diff evidence")
    compatibility: Optional[str] = Field(default="breaking", description="Compatibility classification")
    severity: Optional[str] = Field(default="high", description="Finding severity level")

    model_config = ConfigDict(extra="ignore")


class ValidationDetails(BaseModel):
    """Detailed results from validating the candidate patch in a temporary sandbox."""

    status: ValidationStatus = ValidationStatus.SKIPPED
    ast_valid: bool = False
    syntax_error: Optional[str] = None
    test_executed: bool = False
    test_passed: Optional[bool] = None
    test_output: Optional[str] = None
    validation_time_ms: float = 0.0

    model_config = ConfigDict(extra="ignore")


class RepairRequest(BaseModel):
    """Request payload sent to the Repair Pipeline."""

    finding: FindingInput
    target_file: Optional[str] = None
    workspace_dir: Optional[str] = None
    provider: str = Field(default="deterministic", description="Patch generation provider: deterministic or ollama")
    model: str = Field(default_factory=lambda: get_settings().ollama_model, description="Model name if using local Ollama")
    base_url: str = Field(default_factory=lambda: get_settings().ollama_base_url, description="Ollama API base URL")
    test_command: Optional[str] = Field(default=None, description="Command to execute in sandbox for validation")

    model_config = ConfigDict(extra="ignore")


class RepairResult(BaseModel):
    """Structured result returned after patch generation and temporary copy validation."""

    repair_id: str = Field(default_factory=lambda: f"rep_{uuid.uuid4().hex[:12]}")
    finding_id: str
    status: RepairStatus
    target_file: Optional[str] = None

    # Stage 1: Proposal Generation
    proposal_generated: bool = Field(default=False, description="Stage 1: True if a candidate patch proposal was generated")
    diff: str = Field(default="", description="Unified diff showing proposed code changes")
    original_content: Optional[str] = None
    proposed_content: Optional[str] = None
    strategy: str = Field(default="deterministic", description="Strategy used: deterministic, ollama, or fallback")
    explanation: str = Field(default="", description="Human-readable rationale for the patch")
    rationale: Optional[str] = Field(default=None, description="Concise engineering rationale for the chosen repair")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions made by the reasoning layer")
    risks: List[str] = Field(default_factory=list, description="Potential risks and migration caveats")
    alternatives_considered: List[str] = Field(default_factory=list, description="Plausible alternative repair approaches evaluated")

    # Stages 2 & 3: Syntax and Test Sandbox Validation
    validation: ValidationDetails = Field(default_factory=ValidationDetails, description="Stages 2 & 3: Syntax and sandbox test validation results")

    # Stage 4: Human Review & Approval Lifecycle
    requires_human_review: bool = Field(default=True, description="Stage 4: Mandatory human approval safety flag")
    human_approved: bool = Field(default=False, description="Stage 4: True only when human approval is explicitly granted")
    approval_status: str = Field(default="pending", description="Stage 4: Lifecycle approval status: 'pending', 'approved', or 'rejected'")

    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(extra="ignore")

    @property
    def is_validated(self) -> bool:
        """Helper confirming that a proposal was generated and successfully passed sandbox validation."""
        return (
            self.status == RepairStatus.VALIDATED
            and self.proposal_generated
            and self.validation.status == ValidationStatus.SUCCESS
            and self.validation.ast_valid is True
            and (self.validation.test_passed is not False)
        )
