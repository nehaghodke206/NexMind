import uuid
from typing import Dict, Any


def test_project_baselines_versioning_and_promotion(client):
    # 1. Create a project
    proj_res = client.post(
        "/api/v1/projects",
        json={"name": "Guardian Core", "description": "Backend engine"},
    )
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # 2. Check no active baseline initially (returns 200 with null body)
    active_res = client.get(f"/api/v1/projects/{project_id}/baselines/active")
    assert active_res.status_code == 200
    assert active_res.json() is None

    # 3. Create baseline v1
    v1_payload = {
        "version_tag": "v1.0.0-snapshot",
        "description": "Initial baseline snapshot",
        "contracts": {
            "paths": {
                "/api/users": {"get": {"summary": "List users"}},
                "/api/orders": {"post": {"summary": "Create order"}},
            }
        },
        "inventory": {
            "endpoints": [
                {"method": "GET", "path": "/api/users"},
                {"method": "POST", "path": "/api/orders"},
            ],
            "discovered_endpoints": 2,
            "external_services": ["auth-provider"],
        },
        "metadata_json": {"creator": "cli"},
    }
    b1_res = client.post(f"/api/v1/projects/{project_id}/baselines", json=v1_payload)
    assert b1_res.status_code == 201
    b1 = b1_res.json()
    assert b1["version_number"] == 1
    assert b1["version_tag"] == "v1.0.0-snapshot"
    assert b1["is_promoted"] is False
    assert b1["is_active"] is False

    # 4. Create baseline v2
    v2_payload = {
        "version_tag": "v1.1.0-snapshot",
        "description": "Added payments endpoint",
        "contracts": {
            "paths": {
                "/api/users": {"get": {"summary": "List users"}},
                "/api/orders": {"post": {"summary": "Create order"}},
                "/api/payments": {"post": {"summary": "Process payment"}},
            }
        },
        "inventory": {
            "endpoints": [
                {"method": "GET", "path": "/api/users"},
                {"method": "POST", "path": "/api/orders"},
                {"method": "POST", "path": "/api/payments"},
            ],
            "discovered_endpoints": 3,
            "external_services": ["auth-provider", "stripe"],
        },
    }
    b2_res = client.post(f"/api/v1/projects/{project_id}/baselines", json=v2_payload)
    assert b2_res.status_code == 201
    b2 = b2_res.json()
    assert b2["version_number"] == 2

    # 5. List baselines
    list_res = client.get(f"/api/v1/projects/{project_id}/baselines")
    assert list_res.status_code == 200
    baselines_resp = list_res.json()
    assert baselines_resp["total"] == 2
    assert len(baselines_resp["items"]) == 2

    # 6. Promote v1 as active baseline
    promote1_res = client.post(f"/api/v1/projects/{project_id}/baselines/{b1['id']}/promote")
    assert promote1_res.status_code == 200
    p1 = promote1_res.json()
    assert p1["is_promoted"] is True
    assert p1["is_active"] is True

    # Check active endpoint returns b1
    active_res = client.get(f"/api/v1/projects/{project_id}/baselines/active")
    assert active_res.status_code == 200
    assert active_res.json()["id"] == b1["id"]

    # 7. Promote v2 as active baseline -> b1 should be deactivated
    promote2_res = client.post(f"/api/v1/projects/{project_id}/baselines/{b2['id']}/promote")
    assert promote2_res.status_code == 200
    p2 = promote2_res.json()
    assert p2["is_promoted"] is True
    assert p2["is_active"] is True

    # Verify active endpoint returns b2 now
    active_res2 = client.get(f"/api/v1/projects/{project_id}/baselines/active")
    assert active_res2.status_code == 200
    assert active_res2.json()["id"] == b2["id"]

    # Verify b1 is no longer active
    b1_get = client.get(f"/api/v1/projects/{project_id}/baselines/{b1['id']}")
    assert b1_get.status_code == 200
    assert b1_get.json()["is_active"] is False

    # 8. Compare baseline v1 and v2
    compare_res = client.get(
        f"/api/v1/projects/{project_id}/baselines/compare",
        params={"base": b1["id"], "target": b2["id"]},
    )
    assert compare_res.status_code == 200
    diff = compare_res.json()
    assert diff["base_id"] == b1["id"]
    assert diff["target_id"] == b2["id"]
    assert diff["summary"]["added_count"] == 1
    assert len(diff["endpoints_added"]) == 1
    assert diff["endpoints_added"][0]["path"] == "/api/payments"


def test_scan_ingest_idempotency(client):
    proj_res = client.post(
        "/api/v1/projects",
        json={"name": "Ingest Target Project"},
    )
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    client_run_id = f"run-{uuid.uuid4().hex[:8]}"

    ingest_payload = {
        "client_run_id": client_run_id,
        "scan_type": "full",
        "detection_mode": "hybrid",
        "capabilities_executed": ["codebase_scanner", "external_api_drift"],
        "duration_seconds": 12.5,
        "scanner_version": "1.2.0",
        "summary_counts": {
            "discovered_endpoints": 14,
            "discrepancies": 1,
            "undocumented_endpoints": 1,
        },
        "findings": [
            {
                "title": "Undocumented endpoint /api/legacy/export",
                "severity": "medium",
                "category": "drift",
                "provenance": "codebase_scanner",
                "confidence": 0.95,
                "fingerprint": f"fp-{uuid.uuid4().hex[:12]}",
                "description": "Route discovered in code but missing from OpenAPI documentation.",
                "evidence": {"route": "/api/legacy/export", "method": "GET"},
            }
        ],
        "status": "succeeded",
    }

    # First ingest
    res1 = client.post(f"/api/v1/projects/{project_id}/scans/ingest", json=ingest_payload)
    assert res1.status_code == 201
    scan1 = res1.json()
    assert scan1["client_run_id"] == client_run_id
    assert scan1["detection_mode"] == "hybrid"
    assert scan1["duration_seconds"] == 12.5
    scan_id_1 = scan1["id"]

    # Verify incident was created
    incidents_list = client.get(f"/api/v1/projects/{project_id}/incidents")
    assert incidents_list.status_code == 200
    inc_data = incidents_list.json()
    assert inc_data["total"] == 1
    assert len(inc_data["items"]) == 1
    assert inc_data["items"][0]["title"] == "Undocumented endpoint /api/legacy/export"
    assert inc_data["items"][0]["provenance"] == "codebase_scanner"

    # Second ingest with same client_run_id (idempotency check)
    res2 = client.post(f"/api/v1/projects/{project_id}/scans/ingest", json=ingest_payload)
    assert res2.status_code == 201
    scan2 = res2.json()
    assert scan2["id"] == scan_id_1

    # Verify no duplicate incident was created
    incidents_list2 = client.get(f"/api/v1/projects/{project_id}/incidents")
    assert incidents_list2.status_code == 200
    inc_data2 = incidents_list2.json()
    assert inc_data2["total"] == 1
    assert len(inc_data2["items"]) == 1


def test_incident_lifecycle_and_reopen_on_recurrence(client):
    proj_res = client.post(
        "/api/v1/projects",
        json={"name": "Lifecycle Test Project"},
    )
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    shared_fingerprint = f"drift-fp-{uuid.uuid4().hex[:10]}"

    finding = {
        "title": "Breaking change in auth parameter",
        "severity": "high",
        "category": "contract_drift",
        "provenance": "external_api_drift",
        "confidence": 0.98,
        "fingerprint": shared_fingerprint,
        "description": "Parameter 'token' changed to 'access_token'",
        "evidence": {"param": "token", "status": "removed"},
    }

    # 1. Ingest scan 1
    scan1_payload = {
        "client_run_id": f"run-1-{uuid.uuid4().hex[:6]}",
        "scan_type": "contract_drift",
        "detection_mode": "algorithmic",
        "findings": [finding],
        "summary_counts": {"findings_total": 1},
        "status": "succeeded",
    }
    res1 = client.post(f"/api/v1/projects/{project_id}/scans/ingest", json=scan1_payload)
    assert res1.status_code == 201

    inc_list = client.get(f"/api/v1/projects/{project_id}/incidents").json()
    assert inc_list["total"] == 1
    inc1 = inc_list["items"][0]
    incident_id = inc1["id"]
    assert inc1["status"] == "open"
    assert inc1["occurrence_count"] == 1
    assert inc1["title"] == "Breaking change in auth parameter"

    # 2. Acknowledge incident
    ack_res = client.post(
        f"/api/v1/incidents/{incident_id}/acknowledge",
        json={"notes": "Investigating token rename"},
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "acknowledged"
    assert ack_res.json()["review_notes"] == "Investigating token rename"

    # 3. Resolve incident
    resolve_res = client.post(
        f"/api/v1/incidents/{incident_id}/resolve",
        json={"notes": "Updated client code to use access_token"},
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "resolved"
    assert resolve_res.json()["resolution_notes"] == "Updated client code to use access_token"

    # 4. Ingest scan 2 with recurring finding -> Incident should automatically REOPEN
    scan2_payload = {
        "client_run_id": f"run-2-{uuid.uuid4().hex[:6]}",
        "scan_type": "contract_drift",
        "detection_mode": "algorithmic",
        "findings": [finding],
        "summary_counts": {"findings_total": 1},
        "status": "succeeded",
    }
    res2 = client.post(f"/api/v1/projects/{project_id}/scans/ingest", json=scan2_payload)
    assert res2.status_code == 201

    inc2 = client.get(f"/api/v1/incidents/{incident_id}").json()
    assert inc2["status"] == "reopened"
    assert inc2["occurrence_count"] == 2

    # 5. Check incident event history timeline
    events_res = client.get(f"/api/v1/incidents/{incident_id}/events")
    assert events_res.status_code == 200
    events = events_res.json()
    # Should contain detected, acknowledged, resolved, and reopened events
    event_types = [e["event_type"] for e in events]
    assert "detected" in event_types
    assert "acknowledged" in event_types
    assert "resolved" in event_types
    assert "reopened" in event_types

    # 6. Reopen manually endpoint test
    # Resolve first
    client.post(f"/api/v1/incidents/{incident_id}/resolve", json={"notes": "Fixed again"})
    # Reopen
    manual_reopen = client.post(
        f"/api/v1/incidents/{incident_id}/reopen",
        json={"notes": "Reopened by engineer manually"},
    )
    assert manual_reopen.status_code == 200
    assert manual_reopen.json()["status"] == "reopened"


def test_top_level_and_canonical_baseline_creation_regression(client):
    """
    Regression test verifying baseline creation succeeds without 404
    across both canonical project route and top-level route, preserving
    baseline versioning and explicit promotion semantics.
    """
    # 1. Create test project
    proj_res = client.post(
        "/api/v1/projects",
        json={"name": "Baseline Route Regression Project"},
    )
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # 2. Test canonical route POST /api/v1/projects/{project_id}/baselines
    canonical_res = client.post(
        f"/api/v1/projects/{project_id}/baselines",
        json={
            "version_tag": "v1.0.0-canonical",
            "contracts": {"/api/v1/users": {"get": {}}},
            "inventory": {"endpoints": [{"route_path": "/api/v1/users"}]},
            "notes": "Created via canonical project route",
        },
    )
    assert canonical_res.status_code == 201
    can_data = canonical_res.json()
    assert can_data["project_id"] == project_id
    assert can_data["version_number"] == 1
    assert can_data["version"] == 1
    assert can_data["version_tag"] == "v1.0.0-canonical"
    assert can_data["is_active"] is False
    assert can_data["is_promoted"] is False

    # 3. Test top-level route POST /api/v1/baselines?project_id={project_id}
    top_level_res = client.post(
        f"/api/v1/baselines?project_id={project_id}",
        json={
            "version_tag": "v2.0.0-top-level",
            "contracts": {"/api/v1/users": {"get": {}, "post": {}}},
            "inventory": {"endpoints": [{"route_path": "/api/v1/users"}]},
            "notes": "Created via top-level baseline route",
        },
    )
    assert top_level_res.status_code == 201
    top_data = top_level_res.json()
    assert top_data["project_id"] == project_id
    assert top_data["version_number"] == 2
    assert top_data["version"] == 2
    assert top_data["version_tag"] == "v2.0.0-top-level"
    assert top_data["is_active"] is False
    assert top_data["is_promoted"] is False

    # 4. List baselines via GET /api/v1/baselines?project_id={project_id}
    list_res = client.get(f"/api/v1/baselines?project_id={project_id}")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] == 2
    assert len(list_data["items"]) == 2


def test_project_baseline_creation_empty_scan_id_regression(client):
    """
    Regression test: Verifies baseline creation succeeds without HTTP 500 when:
    1. source_scan_id is an empty string ""
    2. source_scan_id is a non-existent or client scan run ID
    3. description is sent instead of or alongside notes
    4. non-existent project_id returns clean 404 rather than 500
    """
    # 1. Create a project
    proj_res = client.post(
        "/api/v1/projects",
        json={"name": "Baseline Test Project", "description": "Regression test project"},
    )
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # 2. Test empty string source_scan_id (was 500 ForeignKeyViolation)
    res_empty_scan = client.post(
        f"/api/v1/projects/{project_id}/baselines",
        json={
            "version_tag": "v1.0.0-empty-scan",
            "source_scan_id": "",
            "description": "Baseline captured from extension with empty scan ID",
            "contracts": {},
            "inventory": {"endpoints": [{"method": "GET", "path": "/test"}]},
        },
    )
    assert res_empty_scan.status_code == 201
    b1 = res_empty_scan.json()
    assert b1["version_number"] == 1
    assert b1["source_scan_id"] is None
    assert b1["description"] == "Baseline captured from extension with empty scan ID"

    # 3. Test non-existent scan ID
    res_invalid_scan = client.post(
        f"/api/v1/projects/{project_id}/baselines",
        json={
            "version_tag": "v2.0.0-nonexistent-scan",
            "source_scan_id": "scan_nonexistent_12345",
            "description": "Baseline captured with non-persisted client scan ID",
            "contracts": {},
            "inventory": {},
        },
    )
    assert res_invalid_scan.status_code == 201
    b2 = res_invalid_scan.json()
    assert b2["version_number"] == 2
    assert b2["source_scan_id"] is None

    # 4. Test non-existent project ID returns 404
    missing_id = str(uuid.uuid4())
    res_missing_proj = client.post(
        f"/api/v1/projects/{missing_id}/baselines",
        json={"version_tag": "v1.0.0"},
    )
    assert res_missing_proj.status_code == 404
    assert res_missing_proj.json()["error"] == "not_found"


