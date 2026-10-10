import logging
from typing import Any, Dict, List, Optional
import httpx
from ..contracts.findings import CompatibilityClassification, Finding
from ..contracts.models import DetectionResult

logger = logging.getLogger("dependency_guardian.client.backend")


class BackendClient:
    """
    HTTP client for interacting with the FastAPI Dependency Guardian backend service.
    Designed to fail gracefully when backend is offline so detection is never blocked.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0):
        # Normalize base URL to point to /api/v1
        raw_url = (base_url or "http://127.0.0.1:8000/api/v1").rstrip("/")
        if not raw_url.endswith("/api/v1") and not raw_url.endswith("/health"):
            raw_url = f"{raw_url}/api/v1"
        self.base_url = raw_url
        self.timeout = timeout

    def is_available(self) -> bool:
        """Ping backend health endpoint to check accessibility."""
        # Check both /api/v1/health and root /health
        candidates = [
            f"{self.base_url}/health",
            self.base_url.replace("/api/v1", "/health"),
        ]
        for url in candidates:
            try:
                resp = httpx.get(url, timeout=self.timeout)
                if resp.status_code == 200 and resp.json().get("status") == "ok":
                    return True
            except Exception:
                continue
        return False

    def start_scan(
        self,
        project_id: str,
        dependency_id: Optional[str] = None,
        scan_type: str = "full",
        initiated_by: str = "detection-agent",
    ) -> Optional[str]:
        """Call POST /projects/{project_id}/scans to initiate a scan run."""
        url = f"{self.base_url}/projects/{project_id}/scans"
        payload = {
            "dependency_id": dependency_id,
            "scan_type": scan_type,
            "initiated_by": initiated_by,
        }
        try:
            resp = httpx.post(url, json=payload, timeout=self.timeout)
            if resp.status_code in (200, 201, 202):
                return resp.json().get("id")
            logger.warning("Backend scan start returned HTTP %d: %s", resp.status_code, resp.text)
        except Exception as exc:
            logger.warning("Failed to start scan on backend: %s", exc)
        return None

    def submit_observations(
        self,
        scan_id: str,
        findings: List[Finding],
        dependency_id: str,
    ) -> List[str]:
        """Call POST /scans/{scan_id}/observations with mapped observation payloads."""
        if not findings:
            return []
        url = f"{self.base_url}/scans/{scan_id}/observations"
        obs_payloads = [f.to_backend_observation(scan_id, dependency_id) for f in findings]
        body = {"observations": obs_payloads}
        try:
            resp = httpx.post(url, json=body, timeout=self.timeout)
            if resp.status_code in (200, 201):
                return resp.json().get("observation_ids", [])
            logger.warning("Backend submit observations returned HTTP %d: %s", resp.status_code, resp.text)
        except Exception as exc:
            logger.warning("Failed to submit observations to backend: %s", exc)
        return []

    def complete_scan(
        self,
        scan_id: str,
        status: str = "completed",
        summary: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Call POST /scans/{scan_id}/complete to finalize scan lifecycle."""
        url = f"{self.base_url}/scans/{scan_id}/complete"
        payload = {
            "status": status,
            "summary": summary,
            "error_message": error_message,
        }
        try:
            resp = httpx.post(url, json=payload, timeout=self.timeout)
            return resp.status_code in (200, 201, 204)
        except Exception as exc:
            logger.warning("Failed to complete scan %s: %s", scan_id, exc)
            return False

    def create_incidents_for_breaking_changes(
        self,
        project_id: str,
        dependency_id: str,
        findings: List[Finding],
        observation_ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Create incidents for breaking or potentially breaking findings."""
        created_incident_ids: List[str] = []
        breaking_findings = [
            f
            for f in findings
            if f.compatibility
            in (
                CompatibilityClassification.BREAKING,
                CompatibilityClassification.POTENTIALLY_BREAKING,
            )
        ]

        url = f"{self.base_url}/projects/{project_id}/incidents"
        for f in breaking_findings:
            payload = f.to_backend_incident(
                dependency_id=dependency_id,
                observation_ids=observation_ids,
            )
            try:
                resp = httpx.post(url, json=payload, timeout=self.timeout)
                if resp.status_code in (200, 201):
                    created_incident_ids.append(resp.json().get("id"))
                else:
                    logger.warning("Failed to create incident on backend: HTTP %d %s", resp.status_code, resp.text)
            except Exception as exc:
                logger.warning("Exception creating incident for %s: %s", f.fingerprint, exc)

        return created_incident_ids

    def sync_detection_result(
        self,
        project_id: str,
        dependency_id: str,
        result: DetectionResult,
    ) -> Dict[str, Any]:
        """
        Orchestrate complete backend sync lifecycle safely.
        If backend is offline, returns gracefully without failing detection.
        """
        if not self.is_available():
            logger.info("Backend is offline at %s; skipping remote sync.", self.base_url)
            return {"synced": False, "reason": "Backend is offline or unreachable"}

        scan_id = self.start_scan(project_id, dependency_id, scan_type="full")
        if not scan_id:
            return {"synced": False, "reason": "Could not initiate scan on backend"}

        obs_ids = self.submit_observations(scan_id, result.findings, dependency_id)
        summary_msg = (
            f"Detection completed in {result.mode.value} mode. "
            f"Total: {result.summary.total_findings}, Breaking: {result.summary.breaking_count}"
        )
        self.complete_scan(
            scan_id=scan_id,
            status="completed" if result.success else "failed",
            summary=summary_msg,
            error_message=result.ai_error,
        )

        incident_ids = self.create_incidents_for_breaking_changes(
            project_id=project_id,
            dependency_id=dependency_id,
            findings=result.findings,
            observation_ids=obs_ids,
        )

        return {
            "synced": True,
            "scan_id": scan_id,
            "observations_count": len(obs_ids),
            "incidents_created": len(incident_ids),
            "incident_ids": incident_ids,
        }
