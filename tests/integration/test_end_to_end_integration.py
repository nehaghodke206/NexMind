"""End-to-End Integration Tests for Dependency Guardian.

Validates the complete lifecycle:
1. Detection Agent executes contract diffing and synchronizes findings to the backend.
2. Backend creates Projects, Dependencies, Scans, Observations, and Incidents.
3. Repair Agent fetches incidents and linked observation evidence without data invention.
4. Repair Agent synthesizes backwards-compatible repairs, executing sandbox validation.
5. Repair proposals and validation runs are persisted to the backend.
6. Proposal transitions through ready_for_review, human approval, and application recording.
7. Safety invariants are enforced: no auto-approvals, failed repairs never marked successful.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models import *

from agents.detection.dependency_guardian.client.backend import BackendClient as DetectionBackendClient
from agents.detection.dependency_guardian.contracts.findings import (
    Finding,
    SeverityLevel,
    CompatibilityClassification,
    DetectionMode,
)
from agents.detection.dependency_guardian.contracts.models import DetectionResult, DiffSummary
from agents.repair.repair_agent import (
    RepairPipeline,
    RepairRequest,
    FindingInput,
    RepairBackendClient,
    incident_to_finding_input,
)
from agents.repair.repair_agent.models import RepairStatus, ValidationStatus


@pytest.fixture
def integrated_client():
    """Provides a fresh in-memory SQLite database and FastAPI TestClient."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(bind=test_engine)
    session = TestingSession()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, base_url="http://testserver") as tc:
        yield tc

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def test_full_detection_to_repair_application_lifecycle(integrated_client):
    """Verify complete end-to-end workflow: Detection -> Incident -> Repair -> Validation -> Approval -> Apply."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        source_file = workspace / "orders_client.py"
        source_file.write_text(
            "def get_order_total(order_dict):\n"
            "    return order_dict.get('subtotal_amount')\n",
            encoding="utf-8",
        )

        det_client = DetectionBackendClient(base_url="http://testserver/api/v1", client=integrated_client)
        repair_client = RepairBackendClient(base_url="http://testserver/api/v1", client=integrated_client)

        assert det_client.is_available() is True
        assert repair_client.is_available() is True

        # 1. Setup Project & Dependency on backend
        p_resp = integrated_client.post("/api/v1/projects", json={"name": "Guardian E2E Project"}).json()
        project_id = p_resp["id"]
        d_resp = integrated_client.post(
            f"/api/v1/projects/{project_id}/dependencies",
            json={"name": "orders-api", "kind": "rest_api"},
        ).json()
        dependency_id = d_resp["id"]

        # 2. Detection Agent identifies breaking field rename
        fingerprint = Finding.generate_fingerprint("/orders", "POST", "subtotal_amount", "RULE-FIELD-RENAMED")
        finding = Finding(
            rule_id="RULE-FIELD-RENAMED",
            fingerprint=fingerprint,
            path="/orders",
            method="POST",
            schema_location="subtotal_amount",
            previous_value="subtotal_amount",
            current_value="subtotal",
            message="Field 'subtotal_amount' renamed to 'subtotal'",
            compatibility=CompatibilityClassification.BREAKING,
            severity=SeverityLevel.HIGH,
            evidence={"renamed_from": "subtotal_amount", "renamed_to": "subtotal"},
        )
        det_result = DetectionResult(
            success=True,
            mode=DetectionMode.ALGORITHMIC,
            findings=[finding],
            summary=DiffSummary.from_findings([finding]),
        )

        sync_summary = det_client.sync_detection_result(
            project_id=project_id,
            dependency_id=dependency_id,
            result=det_result,
        )
        assert sync_summary["synced"] is True
        assert sync_summary["incidents_created"] == 1
        incident_id = sync_summary["incident_records"][0]["incident_id"]

        # 3. Retrieve incident & observations via RepairBackendClient
        incident_data = repair_client.get_incident(incident_id)
        assert incident_data["id"] == incident_id
        assert incident_data["status"] == "open"
        assert len(incident_data.get("observations", [])) == 1

        finding_input = incident_to_finding_input(incident_data)
        assert finding_input.rule_id == "RULE-FIELD-RENAMED"
        assert finding_input.evidence.get("renamed_from") == "subtotal_amount"
        assert finding_input.evidence.get("renamed_to") == "subtotal"

        # 4. Repair Agent runs pipeline with sandbox validation
        test_command = 'python3 -c "import orders_client; assert orders_client.get_order_total({\'subtotal\': 99.5}) == 99.5"'
        repair_pipeline = RepairPipeline()
        repair_req = RepairRequest(
            finding=finding_input,
            target_file=str(source_file),
            workspace_dir=str(workspace),
            test_command=test_command,
        )
        repair_result = repair_pipeline.run(repair_req)

        assert repair_result.status == RepairStatus.VALIDATED
        assert repair_result.proposal_generated is True
        assert repair_result.is_validated is True
        assert repair_result.validation.ast_valid is True
        # Safety invariant: original file was not modified
        assert "order_dict.get('subtotal_amount')" in source_file.read_text(encoding="utf-8")

        # 5. Persist repair proposal and validation run
        lifecycle_pub = repair_client.publish_repair_lifecycle(
            incident_id=incident_id,
            result=repair_result,
            test_command=test_command,
        )
        repair_id = lifecycle_pub["repair_id"]
        assert lifecycle_pub["human_approval_pending"] is True

        # Verify proposal retrievability and status transition
        persisted_prop = repair_client.get_proposal(repair_id)
        assert persisted_prop["id"] == repair_id
        assert persisted_prop["status"] == "ready_for_review"
        assert persisted_prop["incident_id"] == incident_id

        # Verify validation run recorded on backend
        validation_runs = repair_client.list_validation_runs(repair_id)
        assert len(validation_runs) == 1
        assert validation_runs[0]["status"] == "passed"
        assert validation_runs[0]["test_command"] == test_command

        # Invariant check: Proposal is NOT approved, and incident is NOT resolved
        assert persisted_prop["status"] != "approved"
        assert persisted_prop["status"] != "applied"
        inc_check = repair_client.get_incident(incident_id)
        assert inc_check["status"] != "resolved"

        # 6. Human Reviewer Approves
        approval_res = repair_client.approve_proposal(
            repair_id=repair_id,
            reviewer_id="lead-reviewer@company.com",
            comment="Backwards-compatible get fallback verified.",
        )
        assert approval_res["decision"] == "approved"

        prop_approved = repair_client.get_proposal(repair_id)
        assert prop_approved["status"] == "approved"
        # Invariant: Approval does not resolve incident until applied
        assert repair_client.get_incident(incident_id)["status"] != "resolved"

        # 7. Local Patch Application Reporting
        apply_res = repair_client.record_application(
            repair_id=repair_id,
            agent_id="dependency-guardian-repair",
            status="applied",
            workspace_reference="git:branch:patch-subtotal",
            message="Cleanly patched and verified in developer workspace.",
        )
        assert apply_res["status"] == "applied"

        # Verify final state
        prop_applied = repair_client.get_proposal(repair_id)
        assert prop_applied["status"] == "applied"
        inc_resolved = repair_client.get_incident(incident_id)
        assert inc_resolved["status"] == "resolved"


def test_insufficient_evidence_flow_safety_invariants(integrated_client):
    """Verify that insufficient evidence triggers needs_review and blocks auto-repair."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        source_file = workspace / "service.py"
        source_file.write_text("def handle_payment(data):\n    return data['amount']\n", encoding="utf-8")

        repair_client = RepairBackendClient(base_url="http://testserver/api/v1", client=integrated_client)

        # Setup Project, Dependency, Incident
        p_resp = integrated_client.post("/api/v1/projects", json={"name": "Safety Test Project"}).json()
        d_resp = integrated_client.post(
            f"/api/v1/projects/{p_resp['id']}/dependencies",
            json={"name": "payments-api", "kind": "rest_api"},
        ).json()
        inc_resp = integrated_client.post(
            f"/api/v1/projects/{p_resp['id']}/incidents",
            json={
                "dependency_id": d_resp["id"],
                "title": "[POST] /payments - RULE-FIELD-RENAME-UNKNOWN",
                "change_type": "field_rename",
                "severity": "high",
            },
        ).json()
        incident_id = inc_resp["id"]

        # Rename finding without 'renamed_to' target attribute
        finding_input = FindingInput(
            id="find-uncertain-01",
            rule_id="RULE-FIELD-RENAMED",
            path="/payments",
            method="POST",
            message="Field renamed but target property name is unknown in contract diff",
            evidence={"renamed_from": "amount"},  # Missing renamed_to
            compatibility="breaking",
            severity="high",
        )

        pipeline = RepairPipeline()
        req = RepairRequest(
            finding=finding_input,
            target_file=str(source_file),
            workspace_dir=str(workspace),
        )
        result = pipeline.run(req)

        # Safety: Must be NEEDS_REVIEW
        assert result.status == RepairStatus.NEEDS_REVIEW
        assert result.proposal_generated is False
        assert result.requires_human_review is True
        assert "target field name" in result.explanation.lower() or "insufficient evidence" in (result.rationale or "").lower()

        # Persist through RepairBackendClient
        pub = repair_client.publish_repair_lifecycle(incident_id, result)
        repair_id = pub["repair_id"]
        assert pub["human_approval_pending"] is True
        assert pub["is_validated"] is False

        # Proposal status on backend must be proposed with manual_review strategy
        prop = repair_client.get_proposal(repair_id)
        assert prop["status"] == "proposed"
        assert prop["strategy"] == "manual_review"

        # Incident remains open
        inc = repair_client.get_incident(incident_id)
        assert inc["status"] == "open"


def test_validation_failure_handling(integrated_client):
    """Verify that failing test command marks validation as failed and never reports success."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        workspace = Path(tmp_dir)
        source_file = workspace / "calc.py"
        source_file.write_text("def calc(d):\n    return d.get('old_val')\n", encoding="utf-8")

        repair_client = RepairBackendClient(base_url="http://testserver/api/v1", client=integrated_client)

        p_resp = integrated_client.post("/api/v1/projects", json={"name": "Val Fail Project"}).json()
        d_resp = integrated_client.post(
            f"/api/v1/projects/{p_resp['id']}/dependencies",
            json={"name": "calc-api", "kind": "rest_api"},
        ).json()
        inc_resp = integrated_client.post(
            f"/api/v1/projects/{p_resp['id']}/incidents",
            json={
                "dependency_id": d_resp["id"],
                "title": "[POST] /calc - RULE-FIELD-RENAMED",
                "change_type": "field_rename",
                "severity": "high",
            },
        ).json()
        incident_id = inc_resp["id"]

        finding_input = FindingInput(
            id="find-calc-01",
            rule_id="RULE-FIELD-RENAMED",
            path="/calc",
            method="POST",
            message="Field renamed",
            evidence={"renamed_from": "old_val", "renamed_to": "new_val"},
            compatibility="breaking",
            severity="high",
        )

        pipeline = RepairPipeline()
        # Test command intentionally fails with exit code 1
        req = RepairRequest(
            finding=finding_input,
            target_file=str(source_file),
            workspace_dir=str(workspace),
            test_command='python3 -c "import sys; sys.exit(1)"',
        )
        result = pipeline.run(req)

        assert result.status == RepairStatus.VALIDATION_FAILED
        assert result.validation.test_passed is False
        assert result.is_validated is False

        pub = repair_client.publish_repair_lifecycle(incident_id, result, test_command=req.test_command)
        repair_id = pub["repair_id"]

        # Backend proposal status must transition to 'failed' (never ready_for_review or approved)
        prop = repair_client.get_proposal(repair_id)
        assert prop["status"] == "failed"

        # Validation run record must be failed
        v_runs = repair_client.list_validation_runs(repair_id)
        assert len(v_runs) == 1
        assert v_runs[0]["status"] == "failed"

        # Incident remains open
        inc = repair_client.get_incident(incident_id)
        assert inc["status"] == "open"


def test_offline_backend_graceful_handling():
    """Verify that both agents handle offline backend gracefully without crashing."""
    offline_url = "http://127.0.0.1:59999/api/v1"  # Non-existent server
    det_client = DetectionBackendClient(base_url=offline_url, timeout=0.2)
    repair_client = RepairBackendClient(base_url=offline_url, timeout=0.2)

    assert det_client.is_available() is False
    assert repair_client.is_available() is False

    # Detection sync should return graceful failure dictionary, not crash
    sync_res = det_client.sync_detection_result(
        project_id="non-existent",
        dependency_id="non-existent",
        result=DetectionResult(
            success=True,
            mode=DetectionMode.ALGORITHMIC,
            findings=[],
            summary=DiffSummary(),
        ),
    )
    assert sync_res["synced"] is False
    assert "offline" in sync_res["reason"].lower()
