def test_not_found_errors(client):
    fake_id = "00000000-0000-0000-0000-000000000999"

    res = client.get(f"/api/v1/projects/{fake_id}")
    assert res.status_code == 404
    assert res.json()["error"] == "not_found"

    res = client.get(f"/api/v1/dependencies/{fake_id}")
    assert res.status_code == 404
    assert res.json()["error"] == "not_found"

    res = client.get(f"/api/v1/incidents/{fake_id}")
    assert res.status_code == 404
    assert res.json()["error"] == "not_found"

    res = client.get(f"/api/v1/repair-proposals/{fake_id}")
    assert res.status_code == 404
    assert res.json()["error"] == "not_found"

    res = client.get(f"/api/v1/baselines/{fake_id}")
    assert res.status_code == 404
    assert res.json()["error"] == "not_found"

    res = client.get(f"/api/v1/scans/{fake_id}")
    assert res.status_code == 404
    assert res.json()["error"] == "not_found"


def test_cannot_apply_unapproved_repair(client):
    # Setup
    p = client.post("/api/v1/projects", json={"name": "Guard Test Project"}).json()
    dep = client.post(f"/api/v1/projects/{p['id']}/dependencies", json={"name": "dep-guard"}).json()
    inc = client.post(
        f"/api/v1/projects/{p['id']}/incidents",
        json={"dependency_id": dep["id"], "title": "Guard Incident"},
    ).json()
    prop = client.post(
        f"/api/v1/incidents/{inc['id']}/repair-proposals",
        json={"rationale": "Fix without approval", "strategy": "compatibility_adapter"},
    ).json()

    # Attempt to apply unapproved repair directly
    res_apply = client.post(
        f"/api/v1/repair-proposals/{prop['id']}/applications",
        json={"status": "applied", "message": "Applied early"},
    )
    assert res_apply.status_code == 409
    assert res_apply.json()["error"] == "conflict"
    assert "not been approved" in res_apply.json()["message"]


def test_cannot_reapprove_or_reject_already_decided_repair(client):
    # Setup
    p = client.post("/api/v1/projects", json={"name": "Decided Test Project"}).json()
    dep = client.post(f"/api/v1/projects/{p['id']}/dependencies", json={"name": "dep-decided"}).json()
    inc = client.post(
        f"/api/v1/projects/{p['id']}/incidents",
        json={"dependency_id": dep["id"], "title": "Decided Incident"},
    ).json()
    prop = client.post(
        f"/api/v1/incidents/{inc['id']}/repair-proposals",
        json={"rationale": "Approve twice", "strategy": "compatibility_adapter"},
    ).json()

    # Approve once
    res_appr1 = client.post(
        f"/api/v1/repair-proposals/{prop['id']}/approvals",
        json={"reviewer_id": "00000000-0000-0000-0000-000000000010", "decision": "approved"},
    )
    assert res_appr1.status_code == 201

    # Attempt to approve again -> 409
    res_appr2 = client.post(
        f"/api/v1/repair-proposals/{prop['id']}/approvals",
        json={"reviewer_id": "00000000-0000-0000-0000-000000000011", "decision": "approved"},
    )
    assert res_appr2.status_code == 409
    assert res_appr2.json()["error"] == "conflict"

    # Attempt to reject an already approved proposal -> 409
    res_rej = client.post(
        f"/api/v1/repair-proposals/{prop['id']}/rejection",
        json={"reviewer_id": "00000000-0000-0000-0000-000000000011", "reason": "Late rejection"},
    )
    assert res_rej.status_code == 409


def test_duplicate_project_member_error(client):
    p = client.post("/api/v1/projects", json={"name": "Member Project"}).json()
    member_data = {"user_id": "00000000-0000-0000-0000-000000000020", "role": "developer"}

    res1 = client.post(f"/api/v1/projects/{p['id']}/members", json=member_data)
    assert res1.status_code == 201

    # Add same member again -> 409
    res2 = client.post(f"/api/v1/projects/{p['id']}/members", json=member_data)
    assert res2.status_code == 409
    assert res2.json()["error"] == "conflict"


def test_invalid_incident_lifecycle_transition(client):
    p = client.post("/api/v1/projects", json={"name": "Transition Project"}).json()
    dep = client.post(f"/api/v1/projects/{p['id']}/dependencies", json={"name": "dep-trans"}).json()
    inc = client.post(
        f"/api/v1/projects/{p['id']}/incidents",
        json={"dependency_id": dep["id"], "title": "Transition Incident"},
    ).json()

    # Move to dismissed
    res_dismiss = client.patch(f"/api/v1/incidents/{inc['id']}", json={"status": "dismissed"})
    assert res_dismiss.status_code == 200
    assert res_dismiss.json()["status"] == "dismissed"

    # Invalid transition: dismissed -> resolved directly without reopening
    res_invalid = client.patch(f"/api/v1/incidents/{inc['id']}", json={"status": "resolved"})
    assert res_invalid.status_code == 409
    assert res_invalid.json()["error"] == "invalid_lifecycle_transition"
