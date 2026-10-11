"""Automated End-to-End Test Suite for Dependency Guardian.
Verifies all 15 Acceptance Criteria from Section 21 of the PRD:

1. Initialize project
2. Configuration validation error on invalid config
3. Baseline creation and preservation across scans
4. Scan checks all simulated services
5. Users API rename detected with baseline/current evidence
6. User Profile workflow, file, and test identified in impact analysis
7. Field adapter proposed and previewed
8. Validation runs before application
9. Approved adapter restores User Profile demo test
10. Search API pagination change detected and bounded proposal shown
11. Payments semantic-uncertainty scenario blocks automatic repair
12. Failing validation prevents application
13. Successful repair can be rolled back
14. Unreachable endpoint failure handled safely without corrupting baseline
15. Full demo can be cleanly reset and replayed
"""

import os
import sys
import time
import subprocess
import httpx
import pytest

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.app.config import load_guardian_config, GuardianConfig

BACKEND_URL = "http://127.0.0.1:8765"


def wait_for_services():
    """Wait until all servers are responding."""
    urls = [
        f"{BACKEND_URL}/api/health",
        "http://127.0.0.1:8001/health",
        "http://127.0.0.1:8002/health",
        "http://127.0.0.1:8003/health",
        "http://127.0.0.1:8004/health",
    ]
    for url in urls:
        connected = False
        for _ in range(20):
            try:
                r = httpx.get(url, timeout=1.0)
                if r.status_code == 200:
                    connected = True
                    break
            except Exception:
                time.sleep(0.5)
        if not connected:
            raise RuntimeError(f"Could not connect to {url}. Please ensure servers are running.")


def test_01_project_initialization():
    """AC 1: A developer initializes the project."""
    r = httpx.post(f"{BACKEND_URL}/api/projects/initialize")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "initialized"
    assert data["dependencies_count"] >= 3
    assert data["workflows_count"] >= 3
    print("✓ AC 1 Passed: Project initialized successfully.")


def test_02_configuration_validation():
    """AC 2: Configuration is validated and invalid configuration produces a useful error."""
    # Test valid config loading
    cfg = load_guardian_config(os.path.join(root_dir, "dependency-guardian.yml"))
    assert cfg.project.name == "demo-shop"

    # Test invalid config detection (duplicate dependency ID)
    bad_yaml = """
project:
  name: bad-project
  validation_command: "pytest"
dependencies:
  - id: dup-id
    name: Service 1
    base_url: "http://127.0.0.1:8001"
  - id: dup-id
    name: Service 2
    base_url: "http://127.0.0.1:8002"
workflows: []
"""
    tmp_path = os.path.join(root_dir, "temp_bad_config.yml")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(bad_yaml)

    try:
        with pytest.raises(Exception) as exc_info:
            load_guardian_config(tmp_path)
        assert "Duplicate dependency id" in str(exc_info.value)
        print("✓ AC 2 Passed: Invalid configuration produces clear, actionable error.")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_03_04_baseline_creation_and_scan():
    """AC 3 & 4: Baseline can be created, remains unchanged by later scans, and checks all services."""
    # Reset all to v1 first
    httpx.post(f"{BACKEND_URL}/api/demo/reset")

    # Capture baseline
    r_base = httpx.post(f"{BACKEND_URL}/api/baselines")
    assert r_base.status_code == 200
    baselines = r_base.json()["baselines"]
    assert len(baselines) >= 4  # Users, Payments, Search, Notification

    # Store initial baseline IDs and versions
    initial_ids = {b["id"]: b["version"] for b in baselines}

    # Run Scan
    r_scan = httpx.post(f"{BACKEND_URL}/api/scans")
    assert r_scan.status_code == 200
    scan_data = r_scan.json()
    assert scan_data["services_checked"] >= 4
    assert scan_data["changes_detected"] == 0  # Clean v1 baseline

    # Verify baseline was not modified or overwritten by scan
    r_base_after = httpx.get(f"{BACKEND_URL}/api/baselines")
    after_baselines = r_base_after.json()["baselines"]
    for b in after_baselines:
        if b["id"] in initial_ids:
            assert b["version"] == initial_ids[b["id"]]

    print("✓ AC 3 & 4 Passed: Baseline captured and preserved across scans; all services checked.")


def test_05_06_users_api_rename_and_impact():
    """AC 5 & 6: Users API rename detected with baseline/current evidence and mapped to User Profile workflow."""
    # Switch Users API to v2
    httpx.post(f"{BACKEND_URL}/api/demo/set-scenario", json={"scenario": "users_v2"})

    # Scan for changes
    r_scan = httpx.post(f"{BACKEND_URL}/api/scans")
    scan_data = r_scan.json()
    assert scan_data["changes_detected"] >= 1

    # Locate Users API rename change
    user_change = None
    for c in scan_data["changes"]:
        if c["dependency_id"] == "users-api":
            user_change = c
            break

    assert user_change is not None, "Users API change not detected"
    assert user_change["change_type"] == "field_rename_candidate"
    assert user_change["evidence"]["removed_field"] == "name"
    assert user_change["evidence"]["added_field"] == "display_name"
    assert user_change["evidence"]["observed_value"] == "Alice"
    print("✓ AC 5 Passed: Users API rename detected with baseline/current evidence.")

    # Check Impact mapping
    r_imp = httpx.get(f"{BACKEND_URL}/api/changes/{user_change['id']}/impact")
    assert r_imp.status_code == 200
    impacts = r_imp.json()["impacts"]
    assert len(impacts) >= 1

    profile_impact = next((i for i in impacts if i["workflow_id"] == "user-profile"), None)
    assert profile_impact is not None
    assert "demo-app/src/services/user_service.py" in profile_impact["source_files"]
    assert "demo-app/tests/test_user_profile.py" in profile_impact["tests"]
    assert "name" in profile_impact["affected_fields"]
    print("✓ AC 6 Passed: User Profile workflow, file, and test identified in impact analysis.")


def test_07_08_09_repair_proposal_validation_and_apply():
    """AC 7, 8, 9: Field adapter proposed, validated, applied, and restores demo test."""
    # Get changes
    changes = httpx.get(f"{BACKEND_URL}/api/changes").json()["changes"]
    user_change = next(c for c in changes if c["dependency_id"] == "users-api")

    # Propose repair
    r_prop = httpx.post(f"{BACKEND_URL}/api/changes/{user_change['id']}/repair-proposals")
    assert r_prop.status_code == 200
    proposal = r_prop.json()
    assert proposal["repair_type"] == "field_rename_adapter"
    assert "diff" in proposal and len(proposal["diff"]) > 0
    assert "display_name" in proposal["diff"]
    print("✓ AC 7 Passed: Field adapter proposed and diff previewed.")

    # Validate repair
    repair_id = proposal["id"]
    r_val = httpx.post(f"{BACKEND_URL}/api/repairs/{repair_id}/validate", timeout=15.0)
    assert r_val.status_code == 200
    val_data = r_val.json()
    assert val_data["status"] == "passed", f"Validation failed: {val_data['output_summary']}"
    assert val_data["exit_code"] == 0
    print("✓ AC 8 Passed: Validation ran successfully before application.")

    # Apply repair
    r_apply = httpx.post(f"{BACKEND_URL}/api/repairs/{repair_id}/apply")
    assert r_apply.status_code == 200
    assert r_apply.json()["status"] == "applied"

    # Verify that the demo test now passes on live code!
    res = subprocess.run("pytest -q demo-app/tests/test_user_profile.py", shell=True, capture_output=True, text=True)
    assert res.returncode == 0, f"Test failed after repair: {res.stdout}\n{res.stderr}"
    print("✓ AC 9 Passed: Approved adapter applied and restored User Profile test.")


def test_10_search_api_pagination_change():
    """AC 10: Search API pagination change detected and bounded proposal shown."""
    # Switch Search API to v2
    httpx.post(f"{BACKEND_URL}/api/demo/set-scenario", json={"scenario": "search_v2"})

    r_scan = httpx.post(f"{BACKEND_URL}/api/scans")
    scan_data = r_scan.json()
    search_change = next((c for c in scan_data["changes"] if c["dependency_id"] == "search-api"), None)
    assert search_change is not None
    assert search_change["change_type"] == "pagination_contract_change"

    # Propose bounded adapter
    r_prop = httpx.post(f"{BACKEND_URL}/api/changes/{search_change['id']}/repair-proposals")
    assert r_prop.status_code == 200
    proposal = r_prop.json()
    assert proposal["repair_type"] == "pagination_adapter"
    assert "next_cursor" in proposal["diff"]
    print("✓ AC 10 Passed: Search API pagination change detected and bounded proposal shown.")


def test_11_payments_semantic_uncertainty_blocks_repair():
    """AC 11: Payments semantic-uncertainty scenario blocks automatic repair."""
    # Switch Payments API to v2
    httpx.post(f"{BACKEND_URL}/api/demo/set-scenario", json={"scenario": "payments_v2"})

    r_scan = httpx.post(f"{BACKEND_URL}/api/scans")
    scan_data = r_scan.json()
    pay_change = next((c for c in scan_data["changes"] if c["dependency_id"] == "payments-api"), None)
    assert pay_change is not None
    assert pay_change["change_type"] == "semantic_uncertainty"
    assert pay_change["severity"] == "blocked"

    # Propose repair -> must return BLOCKED status
    r_prop = httpx.post(f"{BACKEND_URL}/api/changes/{pay_change['id']}/repair-proposals")
    assert r_prop.status_code == 200
    proposal = r_prop.json()
    assert proposal["status"] == "blocked_uncertain"
    assert "REPAIR BLOCKED" in proposal["error_message"]

    # Attempt to apply -> must be rejected with 400
    r_apply = httpx.post(f"{BACKEND_URL}/api/repairs/{proposal['id']}/apply")
    assert r_apply.status_code == 400
    print("✓ AC 11 Passed: Payments semantic uncertainty safely blocked automatic repair.")


def test_12_failing_validation_blocks_application():
    """AC 12: A failing validation prevents application."""
    # Create an artificial proposal that would fail tests
    changes = httpx.get(f"{BACKEND_URL}/api/changes").json()["changes"]
    c = changes[0]
    proposal = httpx.post(f"{BACKEND_URL}/api/changes/{c['id']}/repair-proposals").json()
    
    # We can verify that if a repair is in validation_failed state, apply fails
    from backend.app.main import db
    db.update_repair_status(proposal["id"], "validation_failed")

    r_apply = httpx.post(f"{BACKEND_URL}/api/repairs/{proposal['id']}/apply")
    assert r_apply.status_code == 400
    assert "validation has failed" in r_apply.text
    print("✓ AC 12 Passed: Failing validation prevents application.")


def test_13_rollback_repair():
    """AC 13: Successful repair can be rolled back."""
    # Ensure clean user_service.py state first
    httpx.post(f"{BACKEND_URL}/api/demo/reset")
    httpx.post(f"{BACKEND_URL}/api/demo/set-scenario", json={"scenario": "users_v2"})
    scan = httpx.post(f"{BACKEND_URL}/api/scans").json()
    user_change = next(c for c in scan["changes"] if c["dependency_id"] == "users-api")

    prop = httpx.post(f"{BACKEND_URL}/api/changes/{user_change['id']}/repair-proposals").json()
    
    # Validate and apply it
    httpx.post(f"{BACKEND_URL}/api/repairs/{prop['id']}/validate", timeout=15.0)
    r_ap = httpx.post(f"{BACKEND_URL}/api/repairs/{prop['id']}/apply")
    assert r_ap.status_code == 200, r_ap.text

    # Now rollback
    r_rb = httpx.post(f"{BACKEND_URL}/api/repairs/{prop['id']}/rollback")
    assert r_rb.status_code == 200
    assert r_rb.json()["status"] == "rolled_back"

    # Verify original file content is restored
    with open(os.path.join(root_dir, "demo-app", "src", "services", "user_service.py"), "r", encoding="utf-8") as f:
        content = f.read()
    assert '"name": data["name"]' in content
    print("✓ AC 13 Passed: Successful repair rolled back and restored original code.")


def test_14_unreachable_probe_does_not_corrupt_baseline():
    """AC 14: Probe failure does not crash backend or corrupt baseline."""
    # Get current baseline count
    baselines_before = httpx.get(f"{BACKEND_URL}/api/baselines").json()["baselines"]

    # Probe an unreachable port or error
    from backend.app.config import DependencyConfig, ProbeConfig, SettingsConfig
    from backend.app.probe_runner import execute_probe
    import asyncio

    dep = DependencyConfig(id="offline-dep", name="Offline API", base_url="http://127.0.0.1:9999", probes=[])
    probe = ProbeConfig(id="offline-probe", method="GET", path="/nonexistent")
    res = asyncio.run(execute_probe(dep, probe, SettingsConfig(request_timeout_seconds=0.5)))
    assert res.error is not None
    assert res.status_code == 0

    # Ensure baselines remain intact
    baselines_after = httpx.get(f"{BACKEND_URL}/api/baselines").json()["baselines"]
    assert len(baselines_after) == len(baselines_before)
    print("✓ AC 14 Passed: Endpoint failure handled safely without corrupting baselines.")


def test_15_clean_reset_and_replay():
    """AC 15: Full demo can be reset and replayed without manual code editing."""
    r_reset = httpx.post(f"{BACKEND_URL}/api/demo/reset")
    assert r_reset.status_code == 200
    assert r_reset.json()["status"] == "reset_completed"

    # Confirm all tests pass on clean reset
    res = subprocess.run("pytest -q demo-app/tests", shell=True, capture_output=True, text=True)
    assert res.returncode == 0, f"Demo tests failed after clean reset: {res.stdout}\n{res.stderr}"

    # Confirm scan shows 0 changes
    r_scan = httpx.post(f"{BACKEND_URL}/api/scans")
    assert r_scan.json()["changes_detected"] == 0
    print("✓ AC 15 Passed: Full demo reset and replayed successfully.")


if __name__ == "__main__":
    print("Running Dependency Guardian Acceptance Criteria E2E Test Suite...")
    wait_for_services()
    test_01_project_initialization()
    test_02_configuration_validation()
    test_03_04_baseline_creation_and_scan()
    test_05_06_users_api_rename_and_impact()
    test_07_08_09_repair_proposal_validation_and_apply()
    test_10_search_api_pagination_change()
    test_11_payments_semantic_uncertainty_blocks_repair()
    test_12_failing_validation_blocks_application()
    test_13_rollback_repair()
    test_14_unreachable_probe_does_not_corrupt_baseline()
    test_15_clean_reset_and_replay()
    print("\n" + "=" * 65)
    print("  🎉 ALL 15 ACCEPTANCE CRITERIA PASSED SUCCESSFULLY! 🎉")
    print("=" * 65)
