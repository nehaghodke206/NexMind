def test_incident_filters_and_pagination(client):
    p = client.post("/api/v1/projects", json={"name": "Filters Test Project"}).json()
    dep = client.post(f"/api/v1/projects/{p['id']}/dependencies", json={"name": "dep-filt"}).json()

    # Create 3 incidents with different severity and status
    inc1 = client.post(
        f"/api/v1/projects/{p['id']}/incidents",
        json={"dependency_id": dep["id"], "title": "Low 1", "severity": "low"},
    ).json()

    inc2 = client.post(
        f"/api/v1/projects/{p['id']}/incidents",
        json={"dependency_id": dep["id"], "title": "Critical 1", "severity": "critical"},
    ).json()

    inc3 = client.post(
        f"/api/v1/projects/{p['id']}/incidents",
        json={"dependency_id": dep["id"], "title": "High 1", "severity": "high"},
    ).json()

    # Move inc2 to in_progress and assign to user
    assignee = "00000000-0000-0000-0000-000000000077"
    client.patch(
        f"/api/v1/incidents/{inc2['id']}",
        json={"status": "in_progress", "assignee_id": assignee},
    )

    # Filter by severity: critical
    res_crit = client.get(f"/api/v1/projects/{p['id']}/incidents?severity=critical")
    assert res_crit.status_code == 200
    crit_items = res_crit.json()["items"]
    assert len(crit_items) == 1
    assert crit_items[0]["id"] == inc2["id"]

    # Filter by status: in_progress
    res_inp = client.get(f"/api/v1/projects/{p['id']}/incidents?status=in_progress")
    assert res_inp.status_code == 200
    inp_items = res_inp.json()["items"]
    assert len(inp_items) == 1
    assert inp_items[0]["id"] == inc2["id"]

    # Filter by assignee
    res_ass = client.get(f"/api/v1/projects/{p['id']}/incidents?assignee_id={assignee}")
    assert res_ass.status_code == 200
    ass_items = res_ass.json()["items"]
    assert len(ass_items) == 1
    assert ass_items[0]["id"] == inc2["id"]

    # Pagination: page_size = 2
    res_page = client.get(f"/api/v1/projects/{p['id']}/incidents?page=1&page_size=2")
    assert res_page.status_code == 200
    page_data = res_page.json()
    assert len(page_data["items"]) == 2
    assert page_data["total"] == 3


def test_dependency_patch_update(client):
    p = client.post("/api/v1/projects", json={"name": "Dep Patch Project"}).json()
    dep = client.post(
        f"/api/v1/projects/{p['id']}/dependencies",
        json={"name": "old-name", "kind": "rest_api", "version": "1.0.0"},
    ).json()

    res_patch = client.patch(
        f"/api/v1/dependencies/{dep['id']}",
        json={"name": "new-name", "version": "2.0.0", "kind": "sdk"},
    )
    assert res_patch.status_code == 200
    updated = res_patch.json()
    assert updated["name"] == "new-name"
    assert updated["version"] == "2.0.0"
    assert updated["kind"] == "sdk"
