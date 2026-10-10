"""
Dependency Guardian Detection Agent
Modular, configurable detection engine supporting algorithmic, AI, and hybrid modes.
"""

from .config import DetectionConfig, load_configuration
from .contracts.findings import (
    CompatibilityClassification,
    DetectionMode,
    DetectionSource,
    Finding,
    RuleId,
    SeverityLevel,
)
from .contracts.models import DetectionRequest, DetectionResult, DiffSummary
from .engines.algorithmic import AlgorithmicDetectionEngine
from .orchestrator import DetectionOrchestrator

__version__ = "0.1.0"

__all__ = [
    "DetectionConfig",
    "load_configuration",
    "DetectionMode",
    "CompatibilityClassification",
    "DetectionSource",
    "Finding",
    "RuleId",
    "SeverityLevel",
    "DetectionRequest",
    "DetectionResult",
    "DiffSummary",
    "AlgorithmicDetectionEngine",
    "DetectionOrchestrator",
]
