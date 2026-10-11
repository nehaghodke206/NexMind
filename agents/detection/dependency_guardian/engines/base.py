from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from ..contracts.findings import Finding


class BaseDetectionEngine(ABC):
    """Abstract base class for specification comparison engines."""

    @abstractmethod
    def detect(
        self,
        baseline_spec: Dict[str, Any],
        current_spec: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Finding]:
        """
        Compare baseline and current specifications and return detected findings.

        Args:
            baseline_spec: Known-good baseline specification document (parsed dict).
            current_spec: Current observed specification document (parsed dict).
            context: Additional contextual metadata (project, dependency info).

        Returns:
            List of validated Finding objects adhering to finding-v1 contract.
        """
        raise NotImplementedError
