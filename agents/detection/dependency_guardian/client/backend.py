import logging
from typing import Any, Dict, List, Optional
import httpx
from ..contracts.findings import CompatibilityClassification, Finding
from ..contracts.models import DetectionResult
from ..settings import get_settings, normalize_backend_url

logger = logging.getLogger("dependency_guardian.client.backend")


class BackendClient:
    """
    HTTP client for interacting with the FastAPI Dependency Guardian backend service.
    Designed to fail gracefully when backend is offline so detection is never blocked.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        client: Optional[httpx.Client] = None,
    ):
        shared = get_settings()
        self.base_url = normalize_backend_url(base_url or shared.backend_base_url)
        self.timeout = timeout if timeout is not None else shared.backend_timeout_seconds
        self._client = client

    def _get_client(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        return httpx.Client(timeout=self.timeout)

    def is_available(self) -> bool:
        """Ping backend health endpoint to check accessibility."""
        # Check both /api/v1/health and root /health
        candidates = [
            f"{self.base_url}/health",
            self.base_url.replace("/api/v1", "/health"),
        ]
        client = self._get_client()
        should_close = self._client is None
        try:
            for url in candidates:
                try:
                    resp = client.get(url)
                    if resp.status_code == 200 and resp.json().get("status") == "ok":
                        return True
                except Exception:
                    continue
            return False
        finally:
            if should_close:
                client.close()

    def start_scan(
        self,
        project_id: str,
        dependency_id: Optional[str] = None,
        scan_type: str = "full",
        initiated_by: str = "detection-agent",
    ) -> Optional[str]:
        """Call POST /projects/{project_id}/scans to initiate a scan run."""
        if not project_id or not str(project_id).strip():
            raise ValueError("A valid, non-empty project_id is required to start a scan.")

        project_id = project_id.strip()
        dep_id = dependency_id.strip() if dependency_id else None

        url = f"{self.base_url}/projects/{project_id}/scans"
        payload = {
            "dependency_id": dep_id,
            "scan_type": scan_type,
            "initiated_by": initiated_by,
        }
        client = self._get_client()
        should_close = self._client is None
        try:
            resp = client.post(url, json=payload)
            if resp.status_code in (200, 201, 202):
                return resp.json().get("id")
            err = f"Backend scan start failed (HTTP {resp.status_code}): {resp.text}"
            logger.warning(err)
            self._last_error = err
        except Exception as exc:
            err = f"Failed to start scan on backend: {exc}"
            logger.warning(err)
            self._last_error = err
        finally:
            if should_close:
                client.close()
        return None

    def submit_observations(
        self,
        scan_id: str,
        findings: List[Finding],
        dependency_id: str,
    ) -> List[str]:
        """Call POST /scans/{scan_id}/observations with mapped observation payloads."""
        if not scan_id or not str(scan_id).strip():
            raise ValueError("A valid, non-empty scan_id is required to submit observations.")
        if not dependency_id or not str(dependency_id).strip():
            raise ValueError("A valid, non-empty dependency_id is required to submit observations.")

        if not findings:
            return []

        url = f"{self.base_url}/scans/{scan_id.strip()}/observations"
        obs_payloads = [f.to_backend_observation(scan_id.strip(), dependency_id.strip()) for f in findings]
        body = {"observations": obs_payloads}
        client = self._get_client()
        should_close = self._client is None
        try:
            resp = client.post(url, json=body)
            if resp.status_code in (200, 201):
                return resp.json().get("observation_ids", [])
            err = f"Backend submit observations failed (HTTP {resp.status_code}): {resp.text}"
            logger.warning(err)
            self._last_error = err
        except Exception as exc:
            err = f"Failed to submit observations to backend: {exc}"
            logger.warning(err)
            self._last_error = err
        finally:
            if should_close:
                client.close()
        return []

    def complete_scan(
        self,
        scan_id: str,
        status: str = "completed",
        summary: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Call POST /scans/{scan_id}/complete to finalize scan lifecycle."""
        if not scan_id or not str(scan_id).strip():
            return False

        url = f"{self.base_url}/scans/{scan_id.strip()}/complete"
        payload = {
            "status": status,
            "summary": summary,
            "error_message": error_message,
        }
        client = self._get_client()
        should_close = self._client is None
        try:
            resp = client.post(url, json=payload)
            if resp.status_code in (200, 201, 204):
                return True
            logger.warning("Backend scan complete returned HTTP %d: %s", resp.status_code, resp.text)
            return False
        except Exception as exc:
            logger.warning("Failed to complete scan %s: %s", scan_id, exc)
            return False
        finally:
            if should_close:
                client.close()

    def create_incidents_for_breaking_changes(
        self,
        project_id: str,
        dependency_id: str,
        findings: List[Finding],
        observation_ids: Optional[List[str]] = None,
        all_findings: Optional[List[Finding]] = None,
    ) -> List[str]:
        """Create incidents for breaking or potentially breaking findings, linking specific observations."""
        if not project_id or not str(project_id).strip():
            raise ValueError("A valid, non-empty project_id is required to create incidents.")
        if not dependency_id or not str(dependency_id).strip():
            raise ValueError("A valid, non-empty dependency_id is required to create incidents.")

        project_id = project_id.strip()
        dependency_id = dependency_id.strip()

        created_incident_ids: List[str] = []
        self._last_incident_records: List[Dict[str, Any]] = []
        self._incident_errors: List[str] = []

        breaking_findings = [
            f
            for f in findings
            if f.compatibility
            in (
                CompatibilityClassification.BREAKING,
                CompatibilityClassification.POTENTIALLY_BREAKING,
            )
        ]

        # Correlate findings with their specific observation IDs
        obs_map: Dict[str, str] = {}
        target_findings = all_findings or findings
        if observation_ids and target_findings:
            for idx, f in enumerate(target_findings):
                if idx < len(observation_ids):
                    obs_map[f.id] = observation_ids[idx]

        url = f"{self.base_url}/projects/{project_id}/incidents"
        client = self._get_client()
        should_close = self._client is None
        try:
            for f in breaking_findings:
                matched_obs = [obs_map[f.id]] if f.id in obs_map else (observation_ids or [])
                payload = f.to_backend_incident(
                    dependency_id=dependency_id,
                    observation_ids=matched_obs,
                )
                try:
                    resp = client.post(url, json=payload)
                    if resp.status_code in (200, 201):
                        inc_id = resp.json().get("id")
                        if inc_id:
                            created_incident_ids.append(inc_id)
                            self._last_incident_records.append({
                                "incident_id": inc_id,
                                "finding": f,
                                "payload": payload,
                            })
                    else:
                        err = f"Failed to create incident for '{f.id}' (HTTP {resp.status_code}): {resp.text}"
                        logger.warning(err)
                        self._incident_errors.append(err)
                except Exception as exc:
                    err = f"Exception creating incident for '{f.id}': {exc}"
                    logger.warning(err)
                    self._incident_errors.append(err)
        finally:
            if should_close:
                client.close()

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
        Never reports success if records failed to persist.
        """
        if not project_id or not str(project_id).strip():
            raise ValueError("A valid, non-empty project_id is required to synchronize detection results.")
        if not dependency_id or not str(dependency_id).strip():
            raise ValueError("A valid, non-empty dependency_id is required to synchronize detection results.")

        project_id = project_id.strip()
        dependency_id = dependency_id.strip()
        self._last_error = None
        sync_errors: List[str] = []

        if not self.is_available():
            logger.info("Backend is offline at %s; skipping remote sync.", self.base_url)
            return {
                "synced": False,
                "reason": f"Backend is offline or unreachable at {self.base_url}",
                "errors": [f"Backend is offline or unreachable at {self.base_url}"],
            }

        scan_id = self.start_scan(project_id, dependency_id, scan_type="full")
        if not scan_id:
            reason = self._last_error or "Could not initiate scan on backend"
            return {
                "synced": False,
                "reason": reason,
                "errors": [reason],
            }

        obs_ids = self.submit_observations(scan_id, result.findings, dependency_id)
        if result.findings and not obs_ids:
            sync_errors.append(
                f"Failed to submit {len(result.findings)} observations to scan {scan_id}: "
                f"{self._last_error or 'No observation IDs returned'}"
            )

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
            all_findings=result.findings,
        )

        breaking_findings = [
            f
            for f in result.findings
            if f.compatibility
            in (
                CompatibilityClassification.BREAKING,
                CompatibilityClassification.POTENTIALLY_BREAKING,
            )
        ]
        if breaking_findings and len(incident_ids) < len(breaking_findings):
            inc_errs = getattr(self, "_incident_errors", [])
            detail = f": {'; '.join(inc_errs)}" if inc_errs else ""
            sync_errors.append(
                f"Failed to create incidents for {len(breaking_findings) - len(incident_ids)} "
                f"of {len(breaking_findings)} breaking findings{detail}"
            )

        all_synced = len(sync_errors) == 0
        return {
            "synced": all_synced,
            "scan_id": scan_id,
            "observations_count": len(obs_ids),
            "incidents_created": len(incident_ids),
            "incident_ids": incident_ids,
            "incident_records": getattr(self, "_last_incident_records", []),
            "errors": sync_errors,
            "reason": None if all_synced else "; ".join(sync_errors),
        }
