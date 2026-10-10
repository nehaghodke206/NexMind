def test_end_to_end_first_vertical_slice(client):
    # 1. Create a project
    project_payload = {
        "name": "Checkout Service",
        "description": "Core checkout and payment processing service",
        "repository_url": "https://github.com/example/checkout-service",
    }
    res_proj = client.post("/api/v1/projects", json=project_payload)
    assert res_proj.status_code == 201
    proj_data = res_proj.json()
    project_id = proj_data["id"]
    assert proj_data["name"] == "Checkout Service"

    # Verify retrieval
    res_get_proj = client.get(f"/api/v1/projects/{project_id}")
    assert res_get_proj.status_code == 200
    assert res_get_proj.json()["id"] == project_id

    # 2. Register a dependency
    dep_payload = {
        "name": "users-service",
        "kind": "rest_api",
        "base_url": "https://api.example.com/users",
        "version": "1.0.0",
        "configuration": {"timeout_seconds": 5},
    }
    res_dep = client.post(f"/api/v1/projects/{project_id}/dependencies", json=dep_payload)
    assert res_dep.status_code == 201
    dep_data = res_dep.json()
    dependency_id = dep_data["id"]
    assert dep_data["name"] == "users-service"
    assert dep_data["project_id"] == project_id

    # 3. Store a versioned baseline
    baseline_payload_v1 = {
        "contract": {
            "fields": {"id": "int", "name": "string"},
            "sample": {"id": 1, "name": "Ada Lovelace"},
        },
        "source": "manual",
        "notes": "Initial known-good contract baseline",
    }
    res_base_v1 = client.post(f"/api/v1/dependencies/{dependency_id}/baselines", json=baseline_payload_v1)
    assert res_base_v1.status_code == 201
    base_v1_data = res_base_v1.json()
    assert base_v1_data["version"] == 1
    assert base_v1_data["dependency_id"] == dependency_id

    # Save a second baseline and verify version immutability (version increments to 2)
    baseline_payload_v2 = {
        "contract": {
            "fields": {"id": "int", "name": "string", "email": "string"},
            "sample": {"id": 1, "name": "Ada Lovelace", "email": "ada@example.com"},
        },
        "source": "scan",
        "notes": "Added email field in v2",
    }
    res_base_v2 = client.post(f"/api/v1/dependencies/{dependency_id}/baselines", json=baseline_payload_v2)
    assert res_base_v2.status_code == 201
    base_v2_data = res_base_v2.json()
    assert base_v2_data["version"] == 2

    # Verify both baseline versions are listed and preserved
    res_base_list = client.get(f"/api/v1/dependencies/{dependency_id}/baselines")
    assert res_base_list.status_code == 200
    baselines = res_base_list.json()
    assert len(baselines) == 2
    assert baselines[0]["version"] == 2
    assert baselines[1]["version"] == 1

    # 4. Accept a scan
    scan_payload = {
        "dependency_id": dependency_id,
        "scan_type": "targeted",
    }
    res_scan = client.post(f"/api/v1/projects/{project_id}/scans", json=scan_payload)
    assert res_scan.status_code == 202
    scan_data = res_scan.json()
    scan_id = scan_data["id"]
    assert scan_data["status"] == "running"

    # 5. Submit observation and preserve its evidence
    obs_payload = {
        "observations": [
            {
                "dependency_id": dependency_id,
                "observation_type": "response_shape",
                "endpoint": "/v1/users/1",
                "method": "GET",
                "payload": {
                    "removed_fields": ["name"],
                    "added_fields": ["display_name"],
                    "observed": {"id": 1, "display_name": "Ada Lovelace"},
                },
                "fingerprint": "users-api:name-to-display_name",
            }
        ]
    }
    res_obs = client.post(f"/api/v1/scans/{scan_id}/observations", json=obs_payload)
    assert res_obs.status_code == 201
    obs_res_data = res_obs.json()
    assert obs_res_data["accepted_count"] == 1
    observation_id = obs_res_data["observation_ids"][0]

    # Complete the scan
    res_comp = client.post(
        f"/api/v1/scans/{scan_id}/complete",
        json={"status": "completed", "summary": "Found 1 schema discrepancy"},
    )
    assert res_comp.status_code == 200
    assert res_comp.json()["status"] == "completed"

    # 6. Create an incident linked to the relevant project, dependency, and observation
    incident_payload = {
        "dependency_id": dependency_id,
        "title": "Users response field changed from name to display_name",
        "description": "Expected field name was not found; display_name was observed.",
        "change_type": "field_rename",
        "severity": "high",
        "confidence": 0.95,
        "fingerprint": "users-api:name-to-display_name",
        "observation_ids": [observation_id],
        "affected_workflows": ["user profile display"],
        "affected_files": ["src/users/client.ts"],
        "evidence": {
            "removed_fields": ["name"],
            "added_fields": ["display_name"],
            "observed": {"display_name": "Ada Lovelace"},
        },
    }
    res_inc = client.post(f"/api/v1/projects/{project_id}/incidents", json=incident_payload)
    assert res_inc.status_code == 201
    incident_data = res_inc.json()
    incident_id = incident_data["id"]
    assert incident_data["project_id"] == project_id
    assert incident_data["dependency_id"] == dependency_id
    assert incident_data["status"] == "open"
    assert incident_data["severity"] == "high"

    # 7. Retrieve the incident and its evidence
    res_get_inc = client.get(f"/api/v1/incidents/{incident_id}")
    assert res_get_inc.status_code == 200
    assert res_get_inc.json()["id"] == incident_id
    assert "src/users/client.ts" in res_get_inc.json()["affected_files"]

    # Retrieve attached observations
    res_get_obs = client.get(f"/api/v1/incidents/{incident_id}/observations")
    assert res_get_obs.status_code == 200
    obs_list = res_get_obs.json()
    assert len(obs_list) == 1
    assert obs_list[0]["id"] == observation_id
    assert obs_list[0]["fingerprint"] == "users-api:name-to-display_name"


def test_fingerprint_deduplication(client):
    # Setup project and dependency
    p = client.post("/api/v1/projects", json={"name": "Dedup Test Project"}).json()
    dep = client.post(
        f"/api/v1/projects/{p['id']}/dependencies",
        json={"name": "auth-service", "kind": "rest_api"},
    ).json()

    scan = client.post(f"/api/v1/projects/{p['id']}/scans", json={}).json()
    obs1 = client.post(
        f"/api/v1/scans/{scan['id']}/observations",
        json={
            "observations": [
                {
                    "dependency_id": dep["id"],
                    "observation_type": "status_code",
                    "payload": {"code": 500},
                    "fingerprint": "auth:login:500_error",
                }
            ]
        },
    ).json()

    # Create initial incident
    inc1 = client.post(
        f"/api/v1/projects/{p['id']}/incidents",
        json={
            "dependency_id": dep["id"],
            "title": "Auth API 500 error",
            "change_type": "status_change",
            "severity": "critical",
            "fingerprint": "auth:login:500_error",
            "observation_ids": obs1["observation_ids"],
        },
    ).json()

    # Add second observation with same fingerprint
    obs2 = client.post(
        f"/api/v1/scans/{scan['id']}/observations",
        json={
            "observations": [
                {
                    "dependency_id": dep["id"],
                    "observation_type": "status_code",
                    "payload": {"code": 500, "detail": "retry failure"},
                    "fingerprint": "auth:login:500_error",
                }
            ]
        },
    ).json()

    # Submit second detection with the same fingerprint
    inc2 = client.post(
        f"/api/v1/projects/{p['id']}/incidents",
        json={
            "dependency_id": dep["id"],
            "title": "Auth API 500 error repeated",
            "change_type": "status_change",
            "severity": "critical",
            "fingerprint": "auth:login:500_error",
            "observation_ids": obs2["observation_ids"],
        },
    ).json()

    # Must be deduplicated to the same incident ID
    assert inc2["id"] == inc1["id"]

    # Verify both observations are linked to the incident
    linked_obs = client.get(f"/api/v1/incidents/{inc1['id']}/observations").json()
    assert len(linked_obs) == 2
