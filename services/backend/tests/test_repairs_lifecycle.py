def test_repair_lifecycle_end_to_end(client):
    # 1. Setup project, dependency, incident
    p = client.post("/api/v1/projects", json={"name": "Lifecycle Test Project"}).json()
    dep = client.post(
        f"/api/v1/projects/{p['id']}/dependencies",
        json={"name": "orders-service", "kind": "rest_api"},
    ).json()
    inc = client.post(
        f"/api/v1/projects/{p['id']}/incidents",
        json={
            "dependency_id": dep["id"],
            "title": "Orders item schema renamed",
            "change_type": "field_rename",
            "severity": "high",
        },
    ).json()

    incident_id = inc["id"]
    assert inc["status"] == "open"

    # 2. Propose repair
    repair_payload = {
        "rationale": "Add backward-compatibility transformer mapping 'item_id' to 'id'.",
        "strategy": "compatibility_adapter",
        "diff_preview": "--- a/src/client.ts\n+++ b/src/client.ts\n@@ -10,1 +10,1 @@\n- item_id\n+ id",
        "confidence": 0.88,
        "created_by": "00000000-0000-0000-0000-000000000001",
    }
    res_prop = client.post(f"/api/v1/incidents/{incident_id}/repair-proposals", json=repair_payload)
    assert res_prop.status_code == 201
    proposal = res_prop.json()
    repair_id = proposal["id"]
    assert proposal["status"] == "proposed"
    assert proposal["strategy"] == "compatibility_adapter"

    # Invariant: A proposal does NOT mark incident resolved
    inc_check_1 = client.get(f"/api/v1/incidents/{incident_id}").json()
    assert inc_check_1["status"] != "resolved"

    # Also check the route alias /repairs/{repair_id} works
    res_prop_alias = client.get(f"/api/v1/repairs/{repair_id}")
    assert res_prop_alias.status_code == 200
    assert res_prop_alias.json()["id"] == repair_id

    # 3. Validation Run (simulating automated test validation)
    val_payload = {
        "status": "passed",
        "test_command": "pytest tests/integration/test_orders_compat.py",
        "output": "3 passed in 0.42s",
        "details": {"tests_total": 3, "tests_passed": 3, "tests_failed": 0},
    }
    res_val = client.post(f"/api/v1/repair-proposals/{repair_id}/validation-runs", json=val_payload)
    assert res_val.status_code == 201
    val_run = res_val.json()
    assert val_run["status"] == "passed"

    # Verify proposal status moved to ready_for_review
    prop_check_1 = client.get(f"/api/v1/repair-proposals/{repair_id}").json()
    assert prop_check_1["status"] == "ready_for_review"

    # Invariant: Validation pass is NOT approval, NOT application, NOT resolution!
    assert prop_check_1["status"] != "approved"
    assert prop_check_1["status"] != "applied"
    inc_check_2 = client.get(f"/api/v1/incidents/{incident_id}").json()
    assert inc_check_2["status"] != "resolved"

    # 4. Human Approval
    approval_payload = {
        "reviewer_id": "00000000-0000-0000-0000-000000000002",
        "decision": "approved",
        "comment": "Reviewed compatibility adapter diff; looks clean.",
    }
    res_appr = client.post(f"/api/v1/repair-proposals/{repair_id}/approvals", json=approval_payload)
    assert res_appr.status_code == 201
    appr_data = res_appr.json()
    assert appr_data["decision"] == "approved"

    # Verify proposal status is now approved
    prop_check_2 = client.get(f"/api/v1/repair-proposals/{repair_id}").json()
    assert prop_check_2["status"] == "approved"

    # Invariant: Approval is NOT application! Incident is still NOT resolved!
    assert prop_check_2["status"] != "applied"
    inc_check_3 = client.get(f"/api/v1/incidents/{incident_id}").json()
    assert inc_check_3["status"] != "resolved"

    # 5. Local Extension/Agent Patch Application Reporting
    # The client/extension applies the patch locally and reports results back
    appl_payload = {
        "agent_id": "00000000-0000-0000-0000-000000000003",
        "status": "applied",
        "workspace_reference": "git:branch:fix-orders-adapter",
        "message": "Patch cleanly applied to developer workspace and tests passed",
    }
    res_appl = client.post(f"/api/v1/repair-proposals/{repair_id}/applications", json=appl_payload)
    assert res_appl.status_code == 201
    appl_data = res_appl.json()
    assert appl_data["status"] == "applied"

    # Now verify the repair is applied and incident is resolved
    prop_check_3 = client.get(f"/api/v1/repair-proposals/{repair_id}").json()
    assert prop_check_3["status"] == "applied"

    inc_final = client.get(f"/api/v1/incidents/{incident_id}").json()
    assert inc_final["status"] == "resolved"


def test_repair_rejection_flow(client):
    # Setup
    p = client.post("/api/v1/projects", json={"name": "Rejection Project"}).json()
    dep = client.post(f"/api/v1/projects/{p['id']}/dependencies", json={"name": "dep-rej"}).json()
    inc = client.post(
        f"/api/v1/projects/{p['id']}/incidents",
        json={"dependency_id": dep["id"], "title": "Rejection Test Incident"},
    ).json()

    prop = client.post(
        f"/api/v1/incidents/{inc['id']}/repair-proposals",
        json={"rationale": "Risky patch", "strategy": "callsite_update"},
    ).json()

    # Reviewer rejects the proposal
    res_rej = client.post(
        f"/api/v1/repair-proposals/{prop['id']}/rejection",
        json={"reviewer_id": "00000000-0000-0000-0000-000000000099", "reason": "Causes breaking change downstream"},
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "rejected"

    # Proposal is rejected, incident is not resolved
    inc_check = client.get(f"/api/v1/incidents/{inc['id']}").json()
    assert inc_check["status"] != "resolved"


def test_project_activity_and_dashboard_summary(client):
    p = client.post("/api/v1/projects", json={"name": "Dashboard Project"}).json()
    project_id = p["id"]

    dep = client.post(f"/api/v1/projects/{project_id}/dependencies", json={"name": "d1"}).json()
    inc = client.post(f"/api/v1/projects/{project_id}/incidents", json={"dependency_id": dep["id"], "title": "inc 1"}).json()

    # Add member
    client.post(
        f"/api/v1/projects/{project_id}/members",
        json={"user_id": "00000000-0000-0000-0000-000000000005", "role": "developer"},
    )

    # Check activity endpoint
    res_act = client.get(f"/api/v1/projects/{project_id}/activity")
    assert res_act.status_code == 200
    acts = res_act.json()
    assert acts["total"] >= 3
    event_types = [item["event_type"] for item in acts["items"]]
    assert "project.created" in event_types
    assert "dependency.registered" in event_types
    assert "member.added" in event_types

    # Check dashboard summary endpoint
    res_sum = client.get(f"/api/v1/projects/{project_id}/summary")
    assert res_sum.status_code == 200
    summary = res_sum.json()
    assert summary["project_id"] == project_id
    assert summary["dependency_count"] == 1
    assert summary["open_incident_count"] == 1
