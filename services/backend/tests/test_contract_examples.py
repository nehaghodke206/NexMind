def test_compatibility_with_shared_contract_examples(client):
    # 1. Setup project and dependency
    p = client.post("/api/v1/projects", json={"name": "Contract Examples Test"}).json()
    dep = client.post(
        f"/api/v1/projects/{p['id']}/dependencies",
        json={"name": "users-service", "kind": "rest_api"},
    ).json()

    # 2. Incident payload structured like contracts/examples/incident.json
    incident_example_payload = {
        "dependency_id": dep["id"],
        "title": "Users API response field renamed",
        "description": "Expected field name was not found; display_name was observed.",
        "severity": "high",
        "fingerprint": "users-api:name-to-display_name",
        "evidence": {
            "removed_fields": ["name"],
            "added_fields": ["display_name"],
            "type_changes": [],
            "baseline": {"name": "Ada Lovelace"},
            "observed": {"display_name": "Ada Lovelace"},
        },
        "affected_files": ["src/users/client.ts"],
        "affected_workflows": ["user profile display"],
    }
    res_inc = client.post(f"/api/v1/projects/{p['id']}/incidents", json=incident_example_payload)
    assert res_inc.status_code == 201
    inc_data = res_inc.json()
    incident_id = inc_data["id"]
    assert inc_data["title"] == "Users API response field renamed"
    assert inc_data["affected_files"] == ["src/users/client.ts"]

    # 3. Repair proposal payload structured like contracts/examples/repair-proposal.json
    repair_example_payload = {
        "rationale": "Update the consumer mapping to use display_name.",
        "strategy": "compatibility_adapter",
        "patch": {
            "format": "unified_diff",
            "content": "--- a/src/users/client.ts\n+++ b/src/users/client.ts\n@@ -5,1 +5,1 @@\n- name\n+ display_name",
        },
    }
    # Test both standard route and api-contract.md alias /repairs
    res_repair = client.post(f"/api/v1/incidents/{incident_id}/repairs", json=repair_example_payload)
    assert res_repair.status_code == 201
    repair_data = res_repair.json()
    repair_id = repair_data["id"]
    assert repair_data["rationale"] == "Update the consumer mapping to use display_name."
    assert "display_name" in repair_data["diff_preview"]

    # 4. Validation result payload structured like contracts/examples/validation-result.json
    validation_example_payload = {
        "result": "failed",
        "summary": "One test still expects the old field.",
        "details": {
            "tests_total": 3,
            "tests_passed": 2,
            "tests_failed": 1,
        },
    }
    # Test both standard route and api-contract.md alias /validate
    res_val = client.post(f"/api/v1/repairs/{repair_id}/validate", json=validation_example_payload)
    assert res_val.status_code == 201
    val_data = res_val.json()
    assert val_data["status"] == "failed"

    # Repair proposal status reflects validation failure
    rep_status = client.get(f"/api/v1/repairs/{repair_id}").json()
    assert rep_status["status"] == "failed"
