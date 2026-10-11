"""Backend client adapter for the Dependency Guardian Repair Agent.

Persists repair proposals and validation runs to the existing backend API
without modifying backend schemas or bypassing human review.
"""

import json
import logging
from typing import Any, Dict, List, Optional
import httpx

from .models import RepairResult, RepairStatus, ValidationDetails, ValidationStatus
from .settings import get_settings, normalize_backend_url

logger = logging.getLogger("repair_agent.backend_client")


class BackendCommunicationError(Exception):
    """Raised when communication with the Dependency Guardian backend fails."""
    pass


class BackendNotFoundError(BackendCommunicationError):
    """Raised when a referenced entity (e.g. incident or repair) is not found."""
    pass


class BackendValidationError(BackendCommunicationError):
    """Raised when backend rejects payload with an HTTP 400 validation error."""
    pass


class RepairBackendClient:
    """HTTP client adapting Repair Agent outcomes to the existing backend REST API.

    Safety principles enforced:
    1. Requires a valid, non-empty incident_id; never invents or guesses an incident.
    2. Maps Repair Agent strategy to allowed backend enum values:
       - 'compatibility_adapter', 'callsite_update', 'pagination_adapter', 'manual_review', 'other'.
    3. Never claims validation succeeded unless configured validation actually passed.
    4. Preserves human approval as a separate, pending step; never auto-approves or applies patches.
    5. Avoids fabricating confidence scores.
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

    def map_strategy_to_backend(self, result: RepairResult) -> str:
        """Map Repair Agent strategy to backend-accepted schema enum."""
        if not result.proposal_generated or result.status == RepairStatus.NEEDS_REVIEW:
            return "manual_review"

        allowed = {
            "compatibility_adapter",
            "callsite_update",
            "pagination_adapter",
            "manual_review",
            "other",
        }
        if result.strategy in allowed:
            return result.strategy

        # Deterministic adapters, ollama patches, and fallbacks map to compatibility_adapter
        return "compatibility_adapter"

    def build_proposal_payload(
        self,
        result: RepairResult,
        confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Construct a payload conforming strictly to backend RepairProposalCreate schema."""
        strategy = self.map_strategy_to_backend(result)
        rationale = result.rationale or result.explanation or "Automated repair proposal from Dependency Guardian."

        proposed_changes = {
            "target_file": result.target_file,
            "finding_id": result.finding_id,
            "engine_strategy": result.strategy,
            "assumptions": result.assumptions,
            "risks": result.risks,
            "alternatives_considered": result.alternatives_considered,
            "proposed_content": result.proposed_content,
            "proposal_generated": result.proposal_generated,
            "repair_agent_status": result.status.value,
        }

        payload: Dict[str, Any] = {
            "rationale": rationale,
            "strategy": strategy,
            "diff_preview": result.diff if result.diff else None,
            "proposed_changes": proposed_changes,
            "created_by": "repair-agent",
        }

        # Avoid fabricating confidence: only include if provided
        if confidence is not None:
            payload["confidence"] = confidence

        if result.diff:
            payload["patch"] = {"format": "unified_diff", "content": result.diff}

        return payload

    def create_proposal(
        self,
        incident_id: str,
        result: RepairResult,
        confidence: Optional[float] = None,
    ) -> str:
        """Submit a RepairProposal under the specified incident_id. Returns repair_id."""
        if not incident_id or not str(incident_id).strip():
            raise ValueError(
                "A valid, non-empty incident_id is required to persist a repair proposal; "
                "refusing to invent an ID or silently associate with the wrong incident."
            )

        incident_id = incident_id.strip()
        payload = self.build_proposal_payload(result, confidence=confidence)
        url = f"{self.base_url}/incidents/{incident_id}/repair-proposals"

        client = self._get_client()
        should_close = self._client is None
        try:
            resp = client.post(url, json=payload)
            if resp.status_code == 404:
                raise BackendNotFoundError(
                    f"Incident '{incident_id}' not found on backend (HTTP 404)."
                )
            if resp.status_code in (400, 422):
                raise BackendValidationError(
                    f"Backend rejected proposal payload with HTTP {resp.status_code}: {resp.text}"
                )
            if resp.status_code not in (200, 201):
                raise BackendCommunicationError(
                    f"Backend proposal creation failed with HTTP {resp.status_code}: {resp.text}"
                )

            data = resp.json()
            repair_id = data.get("id")
            if not repair_id:
                raise BackendCommunicationError(
                    f"Incomplete backend response: missing 'id' in {data}"
                )
            return repair_id
        except httpx.RequestError as exc:
            raise BackendCommunicationError(
                f"Network request to backend failed: {exc}"
            ) from exc
        finally:
            if should_close:
                client.close()

    def submit_validation_run(
        self,
        repair_id: str,
        validation: ValidationDetails,
        test_command: Optional[str] = None,
    ) -> str:
        """Record validation evidence under repair_id. Returns run_id."""
        if not repair_id or not str(repair_id).strip():
            raise ValueError("A valid, non-empty repair_id is required to record a validation run.")

        repair_id = repair_id.strip()

        # Strict validation status mapping: never claim passed unless actually passed
        if validation.status == ValidationStatus.SKIPPED:
            val_status = "blocked"
        elif (
            validation.status == ValidationStatus.SUCCESS
            and validation.ast_valid is True
            and validation.test_passed is not False
        ):
            val_status = "passed"
        elif (
            validation.status == ValidationStatus.FAILED
            or validation.ast_valid is False
            or validation.test_passed is False
        ):
            val_status = "failed"
        else:
            val_status = "error"

        payload = {
            "status": val_status,
            "test_command": test_command,
            "output": validation.test_output,
            "details": {
                "ast_valid": validation.ast_valid,
                "syntax_error": validation.syntax_error,
                "test_executed": validation.test_executed,
                "validation_time_ms": validation.validation_time_ms,
            },
        }

        url = f"{self.base_url}/repair-proposals/{repair_id}/validation-runs"
        client = self._get_client()
        should_close = self._client is None
        try:
            resp = client.post(url, json=payload)
            if resp.status_code == 404:
                raise BackendNotFoundError(
                    f"Repair proposal '{repair_id}' not found on backend (HTTP 404)."
                )
            if resp.status_code in (400, 422):
                raise BackendValidationError(
                    f"Backend rejected validation run payload with HTTP {resp.status_code}: {resp.text}"
                )
            if resp.status_code not in (200, 201):
                raise BackendCommunicationError(
                    f"Backend validation run creation failed with HTTP {resp.status_code}: {resp.text}"
                )

            data = resp.json()
            run_id = data.get("id")
            if not run_id:
                raise BackendCommunicationError(
                    f"Incomplete backend response: missing 'id' in {data}"
                )
            return run_id
        except httpx.RequestError as exc:
            raise BackendCommunicationError(
                f"Network request to backend failed: {exc}"
            ) from exc
        finally:
            if should_close:
                client.close()

    def publish_repair_lifecycle(
        self,
        incident_id: str,
        result: RepairResult,
        test_command: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Publish full repair result (proposal and validation evidence) to backend.

        Ensures human review is preserved as a separate, pending step.
        """
        # Step 1: Create repair proposal
        repair_id = self.create_proposal(
            incident_id=incident_id,
            result=result,
            confidence=confidence,
        )

        # Step 2: Record validation run if validation was run or proposal was generated
        validation_run_id = None
        if result.proposal_generated or result.validation.test_executed or result.validation.status != ValidationStatus.SKIPPED:
            validation_run_id = self.submit_validation_run(
                repair_id=repair_id,
                validation=result.validation,
                test_command=test_command,
            )

        # Safety: Human approval is strictly pending; never auto-approved
        return {
            "incident_id": incident_id,
            "repair_id": repair_id,
            "validation_run_id": validation_run_id,
            "proposal_generated": result.proposal_generated,
            "is_validated": result.is_validated,
            "human_approval_pending": True,
        }

    def get_proposal(self, repair_id: str) -> Dict[str, Any]:
        """Retrieve a repair proposal by its ID."""
        if not repair_id or not str(repair_id).strip():
            raise ValueError("A valid, non-empty repair_id is required to fetch a proposal.")

        repair_id = repair_id.strip()
        url = f"{self.base_url}/repair-proposals/{repair_id}"

        client = self._get_client()
        should_close = self._client is None
        try:
            resp = client.get(url)
            if resp.status_code == 404:
                raise BackendNotFoundError(
                    f"Repair proposal '{repair_id}' not found on backend (HTTP 404)."
                )
            if resp.status_code != 200:
                raise BackendCommunicationError(
                    f"Backend failed to retrieve proposal (HTTP {resp.status_code}): {resp.text}"
                )

            data = resp.json()
            if not isinstance(data, dict) or "id" not in data:
                raise BackendCommunicationError(
                    f"Incomplete backend response: missing 'id' in {data}"
                )
            return data
        except httpx.RequestError as exc:
            raise BackendCommunicationError(
                f"Network request to backend failed: {exc}"
            ) from exc
        finally:
            if should_close:
                client.close()

    def list_validation_runs(self, repair_id: str) -> List[Dict[str, Any]]:
        """Retrieve all validation runs for a repair proposal."""
        if not repair_id or not str(repair_id).strip():
            raise ValueError("A valid, non-empty repair_id is required to fetch validation runs.")

        repair_id = repair_id.strip()
        url = f"{self.base_url}/repair-proposals/{repair_id}/validation-runs"

        client = self._get_client()
        should_close = self._client is None
        try:
            resp = client.get(url)
            if resp.status_code == 404:
                raise BackendNotFoundError(
                    f"Repair proposal '{repair_id}' not found on backend (HTTP 404)."
                )
            if resp.status_code != 200:
                raise BackendCommunicationError(
                    f"Backend failed to retrieve validation runs (HTTP {resp.status_code}): {resp.text}"
                )

            data = resp.json()
            if not isinstance(data, list):
                raise BackendCommunicationError(
                    f"Invalid backend response: expected list, got {type(data).__name__}"
                )
            return data
        except httpx.RequestError as exc:
            raise BackendCommunicationError(
                f"Network request to backend failed: {exc}"
            ) from exc
        finally:
            if should_close:
                client.close()

    def list_proposals(self, incident_id: str) -> List[Dict[str, Any]]:
        """Retrieve all repair proposals associated with an incident."""
        if not incident_id or not str(incident_id).strip():
            raise ValueError("A valid, non-empty incident_id is required to list repair proposals.")

        incident_id = incident_id.strip()
        url = f"{self.base_url}/incidents/{incident_id}/repair-proposals"

        client = self._get_client()
        should_close = self._client is None
        try:
            resp = client.get(url)
            if resp.status_code == 404:
                raise BackendNotFoundError(
                    f"Incident '{incident_id}' not found on backend (HTTP 404)."
                )
            if resp.status_code != 200:
                raise BackendCommunicationError(
                    f"Backend failed to retrieve repair proposals (HTTP {resp.status_code}): {resp.text}"
                )

            data = resp.json()
            if not isinstance(data, list):
                raise BackendCommunicationError(
                    f"Invalid backend response: expected list, got {type(data).__name__}"
                )
            return data
        except httpx.RequestError as exc:
            raise BackendCommunicationError(
                f"Network request to backend failed: {exc}"
            ) from exc
        finally:
            if should_close:
                client.close()

    def get_incident_observations(self, incident_id: str) -> List[Dict[str, Any]]:
        """Retrieve evidence observations attached to an incident."""
        if not incident_id or not str(incident_id).strip():
            raise ValueError("A valid, non-empty incident_id is required to fetch observations.")

        incident_id = incident_id.strip()
        url = f"{self.base_url}/incidents/{incident_id}/observations"

        client = self._get_client()
        should_close = self._client is None
        try:
            resp = client.get(url)
            if resp.status_code == 404:
                return []
            if resp.status_code != 200:
                raise BackendCommunicationError(
                    f"Backend failed to retrieve observations (HTTP {resp.status_code}): {resp.text}"
                )
            data = resp.json()
            return data if isinstance(data, list) else []
        except httpx.RequestError as exc:
            raise BackendCommunicationError(
                f"Network request to backend failed: {exc}"
            ) from exc
        finally:
            if should_close:
                client.close()

    def get_incident(self, incident_id: str, fetch_observations: bool = True) -> Dict[str, Any]:
        """Retrieve incident details from backend, optionally enriched with linked observations."""
        if not incident_id or not str(incident_id).strip():
            raise ValueError("A valid, non-empty incident_id is required to fetch an incident.")

        incident_id = incident_id.strip()
        url = f"{self.base_url}/incidents/{incident_id}"

        client = self._get_client()
        should_close = self._client is None
        try:
            resp = client.get(url)
            if resp.status_code == 404:
                raise BackendNotFoundError(
                    f"Incident '{incident_id}' not found on backend (HTTP 404)."
                )
            if resp.status_code != 200:
                raise BackendCommunicationError(
                    f"Backend failed to retrieve incident (HTTP {resp.status_code}): {resp.text}"
                )

            data = resp.json()
            if not isinstance(data, dict) or "id" not in data:
                raise BackendCommunicationError(
                    f"Incomplete backend response: missing 'id' in {data}"
                )

            if fetch_observations:
                try:
                    obs_list = self.get_incident_observations(incident_id)
                    if obs_list:
                        data["observations"] = obs_list
                        first_obs = obs_list[0]
                        payload = first_obs.get("payload") or {}
                        if "evidence" not in data or not data["evidence"]:
                            data["evidence"] = payload
                except Exception:
                    pass

            return data
        except httpx.RequestError as exc:
            raise BackendCommunicationError(
                f"Network request to backend failed: {exc}"
            ) from exc
        finally:
            if should_close:
                client.close()

    def list_incidents(self, project_id: str) -> List[Dict[str, Any]]:
        """Retrieve all incidents associated with a project."""
        if not project_id or not str(project_id).strip():
            raise ValueError("A valid, non-empty project_id is required to list incidents.")

        project_id = project_id.strip()
        url = f"{self.base_url}/projects/{project_id}/incidents"

        client = self._get_client()
        should_close = self._client is None
        try:
            resp = client.get(url)
            if resp.status_code == 404:
                raise BackendNotFoundError(
                    f"Project '{project_id}' not found on backend (HTTP 404)."
                )
            if resp.status_code != 200:
                raise BackendCommunicationError(
                    f"Backend failed to retrieve incidents (HTTP {resp.status_code}): {resp.text}"
                )

            data = resp.json()
            items = data.get("items", []) if isinstance(data, dict) else data
            return items if isinstance(items, list) else []
        except httpx.RequestError as exc:
            raise BackendCommunicationError(
                f"Network request to backend failed: {exc}"
            ) from exc
        finally:
            if should_close:
                client.close()

    def approve_proposal(
        self,
        repair_id: str,
        reviewer_id: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit explicit human reviewer approval for a repair proposal."""
        if not repair_id or not str(repair_id).strip():
            raise ValueError("A valid, non-empty repair_id is required for approval.")

        repair_id = repair_id.strip()
        url = f"{self.base_url}/repair-proposals/{repair_id}/approvals"
        payload = {
            "reviewer_id": reviewer_id or "reviewer-admin",
            "decision": "approved",
            "comment": comment or "Manual review sign-off via Dependency Guardian",
        }

        client = self._get_client()
        should_close = self._client is None
        try:
            resp = client.post(url, json=payload)
            if resp.status_code == 404:
                raise BackendNotFoundError(f"Repair proposal '{repair_id}' not found on backend (HTTP 404).")
            if resp.status_code not in (200, 201):
                raise BackendCommunicationError(
                    f"Backend failed to approve repair proposal (HTTP {resp.status_code}): {resp.text}"
                )
            return resp.json()
        except httpx.RequestError as exc:
            raise BackendCommunicationError(f"Network request to backend failed: {exc}") from exc
        finally:
            if should_close:
                client.close()

    def record_application(
        self,
        repair_id: str,
        agent_id: Optional[str] = None,
        status: str = "applied",
        workspace_reference: Optional[str] = None,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record local application result of an approved repair patch."""
        if not repair_id or not str(repair_id).strip():
            raise ValueError("A valid, non-empty repair_id is required to record application.")

        repair_id = repair_id.strip()
        url = f"{self.base_url}/repair-proposals/{repair_id}/applications"
        payload = {
            "agent_id": agent_id or "repair-agent",
            "status": status,
            "workspace_reference": workspace_reference or "local:workspace",
            "message": message or "Patch applied cleanly to workspace",
        }

        client = self._get_client()
        should_close = self._client is None
        try:
            resp = client.post(url, json=payload)
            if resp.status_code == 404:
                raise BackendNotFoundError(f"Repair proposal '{repair_id}' not found on backend (HTTP 404).")
            if resp.status_code not in (200, 201):
                raise BackendCommunicationError(
                    f"Backend failed to record application (HTTP {resp.status_code}): {resp.text}"
                )
            return resp.json()
        except httpx.RequestError as exc:
            raise BackendCommunicationError(f"Network request to backend failed: {exc}") from exc
        finally:
            if should_close:
                client.close()


def incident_to_finding_input(incident: Dict[str, Any]) -> FindingInput:
    """Map a backend IncidentResponse dictionary (optionally enriched with observations) to a Repair Agent FindingInput."""
    from .models import FindingInput

    evidence = incident.get("evidence") or {}
    if not evidence and incident.get("observations"):
        obs_list = incident["observations"]
        if obs_list and isinstance(obs_list[0], dict):
            evidence = obs_list[0].get("payload") or {}

    evidence_details = evidence.get("evidence_details") or {}

    # Extract path and method from evidence or incident title e.g. "[GET] /users/{id} - RULE-FIELD-REMOVED"
    title = incident.get("title", "")
    method = evidence.get("method")
    path = evidence.get("endpoint") or "/"

    if path == "/" or not method:
        if "[" in title and "]" in title:
            m_part = title.split("]")[0].replace("[", "").strip()
            if not method:
                method = m_part.upper()
            rem = title.split("]")[1].strip()
            title_path = rem.split(" - ")[0].strip()
            if title_path and path == "/":
                path = title_path
        elif " - " in title:
            title_path = title.split(" - ")[0].strip()
            if title_path and path == "/":
                path = title_path
        elif incident.get("endpoint"):
            path = incident.get("endpoint")

    finding_id = evidence.get("finding_id") or incident.get("id") or "find_unknown"
    rule_id = evidence.get("rule_id") or incident.get("change_type") or "RULE-DRIFT"

    # Merge evidence details
    merged_evidence = dict(evidence_details)
    inner_ev = evidence.get("evidence")
    if isinstance(inner_ev, dict):
        for k, v in inner_ev.items():
            if k not in merged_evidence:
                merged_evidence[k] = v

    for k in (
        "removed_property",
        "renamed_from",
        "renamed_to",
        "removed_field",
        "added_field",
        "observed_value",
        "previous_type",
        "current_type",
        "property",
        "field",
        "old_type",
        "new_type",
    ):
        if k in evidence and k not in merged_evidence:
            merged_evidence[k] = evidence[k]

    return FindingInput(
        id=str(finding_id),
        rule_id=str(rule_id),
        path=path,
        method=method,
        schema_location=evidence.get("schema_location") or "",
        previous_value=evidence.get("previous_value"),
        current_value=evidence.get("current_value"),
        message=incident.get("description") or title,
        evidence=merged_evidence,
        compatibility=evidence.get("compatibility") or "breaking",
        severity=incident.get("severity", "high"),
    )


