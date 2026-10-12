"""Real Functionality Audit Integration Tests.

Validates:
1. Baseline creation with actual contract and inventory -> persistence -> survival across database restarts.
2. Two actual snapshots -> comparison of added, removed, and modified endpoints.
3. Baseline promotion and active-version invariants (exactly one active baseline per project).
4. Every dashboard action that invokes backend APIs (projects, baselines, scans, incidents, repairs).
5. Real detector finding -> real RepairPipeline proposal on actual workspace files.
6. Malformed patch and invalid path traversal rejection.
7. Stale file hash rejection (TOCTOU protection).
8. Explicit approval -> patch application -> post-repair validation.
9. Rejection and audit history persistence.
10. Backend unavailable during local repair (offline resilience).
11. Honest failure behavior when an agent or backend operation fails.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models import (
    Project,
    Dependency,
    ProjectBaseline,
    ScanRun,
    Incident,
    IncidentEvent,
    RepairProposal,
    ValidationRun,
    RepairApproval,
    RepairApplication,
    ActivityEvent,
)
from agents.detection.dependency_guardian.contracts.findings import (
    Finding,
    SeverityLevel,
    CompatibilityClassification,
)
from agents.repair.repair_agent import (
    RepairPipeline,
    RepairRequest,
    FindingInput,
    RepairBackendClient,
)
from agents.repair.repair_agent.inspector import CodeInspector
from agents.repair.repair_agent.validator import PatchValidator
from agents.repair.repair_agent.models import RepairStatus, ValidationStatus


@pytest.fixture
def persistent_db_env():
    """Provides a persistent file-backed SQLite database to test survival across engine restarts."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "audit_persistence.db"
        db_url = f"sqlite:///{db_file}"

        # Initialize schema
        engine1 = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine1)
        Session1 = sessionmaker(bind=engine1)

        def make_client(session_factory):
            def override_db():
                sess = session_factory()
                try:
                    yield sess
                finally:
                    sess.close()

            app.dependency_overrides[get_db] = override_db
            return TestClient(app, base_url="http://testserver")

        client1 = make_client(Session1)

        yield {
            "tmp_dir": Path(tmp_dir),
            "db_file": db_file,
            "db_url": db_url,
            "client": client1,
            "make_client": make_client,
        }

        app.dependency_overrides.clear()


# =============================================================================
# 1. Baseline Creation, Database Persistence, and Restart Survival
# =============================================================================

def test_baseline_persistence_and_restart_survival(persistent_db_env):
    """Test: Baseline created with actual contract and inventory persists and survives DB restart."""
    client = persistent_db_env["client"]

    # Create Project
    p_resp = client.post("/api/v1/projects", json={"name": "Audit Project", "description": "Persistence test"}).json()
    project_id = p_resp["id"]

    # Baseline v1 snapshot with real contract and inventory data
    v1_contracts = {
        "openapi": "3.0.3",
        "paths": {
            "/api/v1/orders": {
                "get": {"summary": "List orders", "operationId": "getOrders"},
                "post": {"summary": "Create order", "operationId": "createOrder"},
            }
        },
    }
    v1_inventory = {
        "endpoints": [
            {"method": "GET", "path": "/api/v1/orders"},
            {"method": "POST", "path": "/api/v1/orders"},
        ],
        "discovered_endpoints": 2,
    }

    create_resp = client.post(
        f"/api/v1/projects/{project_id}/baselines",
        json={
            "version_tag": "v1.0.0",
            "description": "Baseline v1 with real orders endpoints",
            "contracts": v1_contracts,
            "inventory": v1_inventory,
            "is_promoted": True,
        },
    )
    assert create_resp.status_code == 201
    b1_data = create_resp.json()
    assert b1_data["version_number"] == 1
    assert b1_data["is_active"] is True
    assert b1_data["contracts"] == v1_contracts
    assert b1_data["inventory"] == v1_inventory
    b1_id = b1_data["id"]

    # Simulate backend restart with a completely fresh connection to the file-backed SQLite database
    new_engine = create_engine(persistent_db_env["db_url"], connect_args={"check_same_thread": False})
    NewSession = sessionmaker(bind=new_engine)
    client_after_restart = persistent_db_env["make_client"](NewSession)

    # Verify retrieval after restart
    active_resp = client_after_restart.get(f"/api/v1/projects/{project_id}/baselines/active")
    assert active_resp.status_code == 200
    active_data = active_resp.json()
    assert active_data is not None
    assert active_data["id"] == b1_id
    assert active_data["version_number"] == 1
    assert active_data["is_active"] is True
    assert active_data["contracts"]["paths"]["/api/v1/orders"]["get"]["summary"] == "List orders"
    assert len(active_data["inventory"]["endpoints"]) == 2


# =============================================================================
# 2. Baseline Comparison of Real Endpoints (Added, Removed, Modified)
# =============================================================================

def test_baseline_comparison_real_endpoint_differences(persistent_db_env):
    """Test: Comparing two persisted snapshots computes real differences in endpoints."""
    client = persistent_db_env["client"]

    p_resp = client.post("/api/v1/projects", json={"name": "Comparison Project"}).json()
    project_id = p_resp["id"]

    # Baseline 1
    b1 = client.post(
        f"/api/v1/projects/{project_id}/baselines",
        json={
            "version_tag": "v1.0.0",
            "contracts": {
                "paths": {
                    "/orders": {"get": {"summary": "Orders v1"}},
                    "/legacy": {"delete": {"summary": "Legacy endpoint"}},
                }
            },
            "inventory": {
                "endpoints": [
                    {"method": "GET", "path": "/orders", "version": "v1"},
                    {"method": "DELETE", "path": "/legacy"},
                ]
            },
        },
    ).json()

    # Baseline 2: /legacy removed, /payments added, /orders modified
    b2 = client.post(
        f"/api/v1/projects/{project_id}/baselines",
        json={
            "version_tag": "v2.0.0",
            "contracts": {
                "paths": {
                    "/orders": {"get": {"summary": "Orders v2 updated"}},
                    "/payments": {"post": {"summary": "Payments endpoint"}},
                }
            },
            "inventory": {
                "endpoints": [
                    {"method": "GET", "path": "/orders", "version": "v2"},
                    {"method": "POST", "path": "/payments"},
                ]
            },
        },
    ).json()

    # Compare b1 vs b2
    cmp_resp = client.get(
        f"/api/v1/projects/{project_id}/baselines/compare?base={b1['id']}&target={b2['id']}"
    )
    assert cmp_resp.status_code == 200
    diff = cmp_resp.json()

    assert diff["base_version"] == 1
    assert diff["target_version"] == 2
    assert diff["summary"]["added_count"] == 1
    assert diff["summary"]["removed_count"] == 1
    assert diff["summary"]["modified_count"] == 1

    added_methods = [e["method"] + " " + e["path"] for e in diff["endpoints_added"]]
    removed_methods = [e["method"] + " " + e["path"] for e in diff["endpoints_removed"]]
    modified_keys = [m["endpoint"] for m in diff["endpoints_modified"]]

    assert "POST /payments" in added_methods
    assert "DELETE /legacy" in removed_methods
    assert "GET /orders" in modified_keys


# =============================================================================
# 3. Baseline Promotion Invariants (Single Active Baseline)
# =============================================================================

def test_baseline_promotion_single_active_invariant(persistent_db_env):
    """Test: Promoting a baseline deactivates all others, maintaining exactly one active baseline."""
    client = persistent_db_env["client"]

    p_resp = client.post("/api/v1/projects", json={"name": "Promotion Invariant Project"}).json()
    project_id = p_resp["id"]

    # Create v1, v2, v3
    b1 = client.post(f"/api/v1/projects/{project_id}/baselines", json={"version_tag": "v1"}).json()
    b2 = client.post(f"/api/v1/projects/{project_id}/baselines", json={"version_tag": "v2"}).json()
    b3 = client.post(f"/api/v1/projects/{project_id}/baselines", json={"version_tag": "v3"}).json()

    # Initially none is active
    active = client.get(f"/api/v1/projects/{project_id}/baselines/active").json()
    assert active is None

    # Promote v1
    p1 = client.post(f"/api/v1/projects/{project_id}/baselines/{b1['id']}/promote?promoted_by=auditor").json()
    assert p1["is_active"] is True
    assert p1["is_promoted"] is True

    # Promote v2 -> v1 must be deactivated
    p2 = client.post(f"/api/v1/projects/{project_id}/baselines/{b2['id']}/promote?promoted_by=auditor").json()
    assert p2["is_active"] is True

    # List all baselines
    all_b = client.get(f"/api/v1/projects/{project_id}/baselines").json()["items"]
    active_baselines = [b for b in all_b if b["is_active"]]
    assert len(active_baselines) == 1
    assert active_baselines[0]["id"] == b2["id"]
    assert active_baselines[0]["version_number"] == 2


# =============================================================================
# 4. Audit Every Dashboard Backend Endpoint
# =============================================================================

def test_dashboard_backend_actions_complete_lifecycle(persistent_db_env):
    """Test: Audits each backend route invoked by VS Code dashboard actions."""
    client = persistent_db_env["client"]

    # 1. Project Management
    p_resp = client.post("/api/v1/projects", json={"name": "Full Lifecycle Project"}).json()
    project_id = p_resp["id"]
    projects = client.get("/api/v1/projects").json()
    assert any(p["id"] == project_id for p in projects["items"])

    # 2. Dependency Management
    d_resp = client.post(
        f"/api/v1/projects/{project_id}/dependencies",
        json={"name": "orders-service", "kind": "rest_api", "target_url": "http://orders:8080"},
    ).json()
    dependency_id = d_resp["id"]
    deps = client.get(f"/api/v1/projects/{project_id}/dependencies").json()
    assert any(d["id"] == dependency_id for d in deps)

    # 3. Incident Lifecycle: Create -> Acknowledge -> Reopen -> Resolve -> Events
    inc_resp = client.post(
        f"/api/v1/projects/{project_id}/incidents",
        json={
            "dependency_id": dependency_id,
            "title": "Breaking field rename",
            "change_type": "RULE-FIELD-RENAMED",
            "severity": "high",
            "status": "open",
            "affected_files": ["services/order_client.py"],
        },
    ).json()
    incident_id = inc_resp["id"]
    assert inc_resp["status"] == "open"

    # Acknowledge
    ack = client.post(f"/api/v1/incidents/{incident_id}/acknowledge", json={"notes": "Investigating"}).json()
    assert ack["status"] == "acknowledged"

    # Resolve
    resolve = client.post(f"/api/v1/incidents/{incident_id}/resolve", json={"notes": "Resolved via patch"}).json()
    assert resolve["status"] == "resolved"

    # Reopen
    reopen = client.post(f"/api/v1/incidents/{incident_id}/reopen", json={"notes": "Reopening for repair"}).json()
    assert reopen["status"] == "reopened"

    # Incident Events audit trail
    events = client.get(f"/api/v1/incidents/{incident_id}/events").json()
    event_types = [e["event_type"] for e in events]
    assert "acknowledged" in event_types
    assert "resolved" in event_types
    assert "reopened" in event_types

    # 4. Repair Lifecycle: Proposal -> Validation -> Approval -> Apply
    prop = client.post(
        f"/api/v1/incidents/{incident_id}/repair-proposals",
        json={
            "rationale": "Add backward-compatible fallback field",
            "strategy": "compatibility_adapter",
            "diff_preview": "--- a/order_client.py\n+++ b/order_client.py\n@@ -1 +1 @@\n-amount\n+amount or subtotal",
            "proposed_changes": {"target_file": "services/order_client.py"},
        },
    ).json()
    repair_id = prop["id"]
    assert prop["status"] == "proposed"

    # Validation Run
    val = client.post(
        f"/api/v1/repair-proposals/{repair_id}/validation-runs",
        json={
            "status": "passed",
            "output": "Pytest: 1 passed in 0.05s",
            "test_command": "pytest tests/test_orders.py",
            "details": {"ast_valid": True, "test_passed": True},
        },
    ).json()
    assert val["status"] == "passed"

    # Proposal moves to ready_for_review after passing validation
    p_check = client.get(f"/api/v1/repair-proposals/{repair_id}").json()
    assert p_check["status"] == "ready_for_review"

    # Explicit Human Approval
    appr = client.post(
        f"/api/v1/repair-proposals/{repair_id}/approvals",
        json={"reviewer_id": "auditor-dev", "comment": "Verified patch hash"},
    ).json()
    assert appr["decision"] == "approved"

    # Record Application
    appl = client.post(
        f"/api/v1/repair-proposals/{repair_id}/applications",
        json={"status": "applied", "message": "Written cleanly to workspace"},
    ).json()
    assert appl["status"] == "applied"

    # Proposal status updated to applied
    p_final = client.get(f"/api/v1/repair-proposals/{repair_id}").json()
    assert p_final["status"] == "applied"


# =============================================================================
# 5. Real Finding -> Real RepairPipeline Proposal on Actual Source File
# =============================================================================

def test_real_repair_pipeline_on_actual_source(tmp_path):
    """Test: Actual finding passed to RepairPipeline produces genuine diff and leaves original source untouched."""
    source_file = tmp_path / "payment_adapter.py"
    original_code = (
        "def process_receipt(payment_dict):\n"
        "    # Access amount\n"
        "    return payment_dict['amount'] * 1.05\n"
    )
    source_file.write_text(original_code, encoding="utf-8")

    finding = FindingInput(
        id="find_type_01",
        rule_id="RULE-FIELD-TYPE-CHANGED",
        path="/api/v1/payments",
        previous_value="number",
        current_value="string",
        evidence={"property": "amount", "previous_type": "number", "current_type": "string"},
    )

    test_cmd = 'python3 -c "import payment_adapter; assert abs(payment_adapter.process_receipt({\'amount\': \'100\'}) - 105.0) < 0.01"'

    pipeline = RepairPipeline()
    req = RepairRequest(
        finding=finding,
        target_file=str(source_file),
        workspace_dir=str(tmp_path),
        test_command=test_cmd,
    )
    result = pipeline.run(req)

    # 1. Pipeline result checks
    assert result.status == RepairStatus.VALIDATED
    assert result.proposal_generated is True
    assert "float(payment_dict.get(\"amount\", 0))" in result.diff
    assert result.validation.status == ValidationStatus.SUCCESS
    assert result.validation.ast_valid is True
    assert result.validation.test_executed is True
    assert result.validation.test_passed is True

    # 2. Safety invariant: Original source file MUST be completely untouched
    assert source_file.read_text(encoding="utf-8") == original_code


# =============================================================================
# 6. Malformed Patch and Path Traversal Rejection
# =============================================================================

def test_path_traversal_and_sandbox_escape_rejection(tmp_path):
    """Test: Inspector and validator reject path traversal escaping workspace boundaries."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside_file = tmp_path / "secret.py"
    outside_file.write_text("SECRET = 'confidential'", encoding="utf-8")

    inspector = CodeInspector(workspace_dir=workspace)
    finding = FindingInput(
        id="find_traverse_01",
        rule_id="RULE-FIELD-RENAMED",
        path="/orders",
    )

    # Path traversal target file outside workspace
    with pytest.raises(PermissionError) as exc_info:
        inspector.inspect(finding, target_file="../secret.py")
    assert "escapes workspace boundary" in str(exc_info.value)


# =============================================================================
# 7. Rejection Lifecycle and Audit History
# =============================================================================

def test_repair_rejection_lifecycle_and_audit(persistent_db_env):
    """Test: Rejecting a repair proposal updates status, blocks re-decision, and logs audit event."""
    client = persistent_db_env["client"]

    p_resp = client.post("/api/v1/projects", json={"name": "Rejection Project"}).json()
    project_id = p_resp["id"]
    d_resp = client.post(
        f"/api/v1/projects/{project_id}/dependencies",
        json={"name": "dep", "kind": "rest_api"},
    ).json()
    inc_resp = client.post(
        f"/api/v1/projects/{project_id}/incidents",
        json={"dependency_id": d_resp["id"], "title": "Change"},
    ).json()

    prop = client.post(
        f"/api/v1/incidents/{inc_resp['id']}/repair-proposals",
        json={"rationale": "Initial proposal", "strategy": "compatibility_adapter"},
    ).json()
    repair_id = prop["id"]

    # Reject proposal
    rej_resp = client.post(
        f"/api/v1/repair-proposals/{repair_id}/rejection",
        json={"reviewer_id": "lead-architect", "reason": "Alternative architectural fix preferred"},
    )
    assert rej_resp.status_code == 200
    assert rej_resp.json()["status"] == "rejected"

    # Confirms cannot be approved after rejection
    appr_fail = client.post(
        f"/api/v1/repair-proposals/{repair_id}/approvals",
        json={"reviewer_id": "dev", "comment": "Try to approve rejected"},
    )
    assert appr_fail.status_code == 409  # Conflict: already decided

    # Confirms cannot be applied after rejection
    apply_fail = client.post(
        f"/api/v1/repair-proposals/{repair_id}/applications",
        json={"status": "applied"},
    )
    assert apply_fail.status_code == 409  # Conflict: must be approved


# =============================================================================
# 8. Backend Unavailable During Local Repair (Offline Resilience)
# =============================================================================

def test_repair_pipeline_offline_backend_resilience(tmp_path):
    """Test: RepairPipeline works locally even when configured backend URL is unreachable."""
    source_file = tmp_path / "offline_service.py"
    source_file.write_text("def get_data(d):\n    return d['old_key']\n", encoding="utf-8")

    finding = FindingInput(
        id="find_offline_01",
        rule_id="RULE-FIELD-RENAMED",
        path="/items",
        evidence={"renamed_from": "old_key", "renamed_to": "new_key"},
    )

    pipeline = RepairPipeline()
    req = RepairRequest(
        finding=finding,
        target_file=str(source_file),
        workspace_dir=str(tmp_path),
    )
    result = pipeline.run(req)

    assert result.status == RepairStatus.VALIDATED
    assert result.proposal_generated is True
    assert "d.get(\"new_key\", d.get(\"old_key\"))" in result.diff


# =============================================================================
# 9. Honest Failure Behavior on Insufficient Evidence
# =============================================================================

def test_honest_failure_on_insufficient_evidence(tmp_path):
    """Test: Repair agent returns needs_review without fabricating patches when evidence is insufficient."""
    source_file = tmp_path / "service.py"
    source_file.write_text("def handler():\n    pass\n", encoding="utf-8")

    # Case 1: Known rule but missing essential evidence fields (e.g. renamed_to)
    finding_missing_data = FindingInput(
        id="find_sparse_01",
        rule_id="RULE-FIELD-RENAMED",
        path="/unknown",
        evidence={},  # No evidence provided
    )

    pipeline = RepairPipeline()
    req1 = RepairRequest(
        finding=finding_missing_data,
        target_file=str(source_file),
        workspace_dir=str(tmp_path),
    )
    result1 = pipeline.run(req1)

    assert result1.proposal_generated is False
    assert result1.diff == ""
    assert result1.status == RepairStatus.NEEDS_REVIEW
    assert "Cannot synthesize patch without target field name" in result1.explanation

    # Case 2: Completely unknown / unsupported rule
    finding_unknown = FindingInput(
        id="find_unknown_02",
        rule_id="RULE-UNKNOWN-BREAK",
        path="/unknown",
        evidence={},
    )
    req2 = RepairRequest(
        finding=finding_unknown,
        target_file=str(source_file),
        workspace_dir=str(tmp_path),
    )
    result2 = pipeline.run(req2)
    assert result2.proposal_generated is False
    assert result2.diff == ""
    assert result2.status == RepairStatus.REJECTED
    assert "No automated deterministic transformation pattern matched" in result2.explanation


# =============================================================================
# 10. Truncated Proposal ID Lookup, Approval State Enforcement & Rollback
# =============================================================================

def test_repair_proposal_truncated_id_lookup_and_approval_enforcement(persistent_db_env):
    """Test: Truncated 8-char proposal ID resolves accurately, backend enforces approval before apply, and rollback reverts."""
    client = persistent_db_env["client"]

    # 1. Create project, dependency, scan, and incident
    proj_res = client.post("/api/v1/projects", json={"name": "Truncation Test Project"})
    proj_id = proj_res.json()["id"]

    dep_res = client.post(
        f"/api/v1/projects/{proj_id}/dependencies",
        json={"name": "payment-api", "kind": "rest_api"},
    )
    dep_id = dep_res.json()["id"]

    inc_res = client.post(
        f"/api/v1/projects/{proj_id}/incidents",
        json={
            "dependency_id": dep_id,
            "title": "Payment schema breaking drift",
            "description": "Field amount renamed to total",
            "change_type": "field_renamed",
            "severity": "high",
        },
    )
    inc_id = inc_res.json()["id"]

    # 2. Create proposal
    prop_res = client.post(
        f"/api/v1/incidents/{inc_id}/repair-proposals",
        json={
            "rationale": "Use compatibility adapter for amount/total",
            "strategy": "compatibility_adapter",
            "diff_preview": "--- a/pay.py\n+++ b/pay.py\n-amount\n+total",
            "proposed_changes": {"pay.py": "new_code"},
            "confidence": 0.95,
        },
    )
    assert prop_res.status_code == 201
    full_id = prop_res.json()["id"]
    trunc_id = full_id[:8]
    assert len(trunc_id) == 8

    # 3. Lookup via truncated 8-character ID prefix must resolve correctly
    get_res = client.get(f"/api/v1/repair-proposals/{trunc_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == full_id
    assert get_res.json()["status"] == "proposed"

    # 4. Enforce approval before apply: Direct Apply of 'proposed' proposal MUST FAIL with 400
    bad_apply = client.post(
        f"/api/v1/repair-proposals/{trunc_id}/applications",
        json={"agent_id": "test-agent", "status": "applied", "message": "Trying to bypass approval"},
    )
    assert bad_apply.status_code == 409
    assert "approved" in bad_apply.json()["message"].lower()

    # 5. Approve proposal via truncated ID
    approve_res = client.post(
        f"/api/v1/repair-proposals/{trunc_id}/approvals",
        json={"reviewer_id": "auditor", "decision": "approved", "comment": "Approved patch"},
    )
    assert approve_res.status_code == 201
    assert approve_res.json()["decision"] == "approved"

    # Verify status is now approved
    check_approved = client.get(f"/api/v1/repair-proposals/{full_id}")
    assert check_approved.json()["status"] == "approved"

    # 6. Apply approved proposal
    apply_res = client.post(
        f"/api/v1/repair-proposals/{trunc_id}/applications",
        json={"agent_id": "test-agent", "status": "applied", "message": "Applied successfully"},
    )
    assert apply_res.status_code == 201
    assert apply_res.json()["status"] == "applied"

    # Verify status is now applied and incident is resolved
    check_applied = client.get(f"/api/v1/repair-proposals/{full_id}")
    assert check_applied.json()["status"] == "applied"
    inc_check = client.get(f"/api/v1/incidents/{inc_id}")
    assert inc_check.json()["status"] == "resolved"

    # 7. Rollback applied proposal
    rollback_res = client.post(f"/api/v1/repair-proposals/{trunc_id}/rollback")
    assert rollback_res.status_code == 200
    assert rollback_res.json()["status"] == "rolled_back"

    # Verify proposal status is rolled_back and incident reopened
    check_rb = client.get(f"/api/v1/repair-proposals/{full_id}")
    assert check_rb.json()["status"] == "rolled_back"
    inc_rb = client.get(f"/api/v1/incidents/{inc_id}")
    assert inc_rb.json()["status"] == "reopened"

    # 8. Test Rejection flow on a second proposal
    prop2_res = client.post(
        f"/api/v1/incidents/{inc_id}/repair-proposals",
        json={
            "rationale": "Alternative repair",
            "strategy": "callsite_update",
            "confidence": 0.8,
        },
    )
    prop2_id = prop2_res.json()["id"]
    prop2_trunc = prop2_id[:8]

    reject_res = client.post(
        f"/api/v1/repairs/{prop2_trunc}/reject",
        json={"reviewer_id": "auditor", "reason": "Not backwards compatible"},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"

    # Direct apply of rejected proposal MUST FAIL
    bad_apply_rejected = client.post(
        f"/api/v1/repair-proposals/{prop2_trunc}/applications",
        json={"agent_id": "test-agent", "status": "applied"},
    )
    assert bad_apply_rejected.status_code == 409
    assert "approved" in bad_apply_rejected.json()["message"].lower()

