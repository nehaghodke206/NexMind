"""Dependency Guardian — Modular Repair Agent.

Inspects detection findings, locates affected application source code,
generates backwards-compatible reviewable patches, and validates them
in isolated temporary sandboxes without ever mutating original files.
"""

from .models import (
    FindingInput,
    RepairRequest,
    RepairResult,
    RepairStatus,
    ValidationDetails,
    ValidationStatus,
)
from .pipeline import RepairPipeline
from .reasoning import EngineeringReasoningLayer
from .backend_client import (
    RepairBackendClient,
    BackendCommunicationError,
    BackendNotFoundError,
    BackendValidationError,
    incident_to_finding_input,
)

__version__ = "0.1.0"
__all__ = [
    "FindingInput",
    "RepairRequest",
    "RepairResult",
    "RepairStatus",
    "ValidationDetails",
    "ValidationStatus",
    "RepairPipeline",
    "EngineeringReasoningLayer",
    "RepairBackendClient",
    "BackendCommunicationError",
    "BackendNotFoundError",
    "BackendValidationError",
    "incident_to_finding_input",
]
