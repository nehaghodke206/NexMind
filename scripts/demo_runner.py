"""Live Interactive Walkthrough & Demonstration Runner for Dependency Guardian.
Executes the full live demonstration sequence from Section 22 of the PRD:

1. Reset environment to clean baseline & confirm tests pass.
2. Introduce Users API rename (name -> display_name) & observe test failure.
3. Run scan & inspect evidence-backed detection.
4. Trace impact to User Profile workflow and source files.
5. Propose backward-compatible field adapter.
6. Run sandbox validation.
7. Apply approved repair & verify workflow passes again.
8. Introduce Search API cursor pagination contract change & generate bounded proposal.
9. Introduce Payments API semantic uncertainty & prove automatic repair is strictly BLOCKED.
10. Reset environment to clean baseline.
"""

import os
import sys
import time
import subprocess
import httpx

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BACKEND_URL = "http://127.0.0.1:8765"


def print_step(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def run_demo():
    print_step("STEP 1: INITIALIZE ENVIRONMENT & CONFIRM CLEAN BASELINE")
    r_reset = httpx.post(f"{BACKEND_URL}/api/demo/reset")
    print(f"Reset services: {r_reset.json()['status']}")

    r_base = httpx.post(f"{BACKEND_URL}/api/baselines")
    print(f"Captured baselines: {len(r_base.json()['baselines'])} endpoints stored in SQLite.")

    test_res = subprocess.run("pytest -q demo-app/tests", shell=True, capture_output=True, text=True)
    print(f"Baseline tests output:\n{test_res.stdout.strip()}")
    assert test_res.returncode == 0, "Initial tests must pass on clean baseline"

    print_step("STEP 2: INTRODUCE BREAKING DRIFT IN USERS API (name -> display_name)")
    httpx.post(f"{BACKEND_URL}/api/demo/set-scenario", json={"scenario": "users_v2"})
    print("Users API (Port 8001) switched to v2 (display_name).")

    # Run demo test to show failure
    test_fail = subprocess.run("pytest -q demo-app/tests/test_user_profile.py", shell=True, capture_output=True, text=True)
    print("Running client test without adapter (Expected Failure):")
    print(test_fail.stdout.strip())
    assert test_fail.returncode != 0, "Test should fail due to missing 'name' field"

    print_step("STEP 3: RUN DEPENDENCY GUARDIAN SCAN")
    scan = httpx.post(f"{BACKEND_URL}/api/scans").json()
    print(f"Scan ID: {scan['scan_id']}")
    print(f"Services Checked: {scan['services_checked']}")
    print(f"Changes Detected: {scan['changes_detected']}")

    user_change = next(c for c in scan["changes"] if c["dependency_id"] == "users-api")
    print("\nDetected Finding:")
    print(f"  Type: {user_change['change_type']}")
    print(f"  Severity: {user_change['severity']}")
    print(f"  Evidence: Removed '{user_change['evidence']['removed_field']}', Added '{user_change['evidence']['added_field']}'")
    print(f"  Value Match: '{user_change['evidence']['observed_value']}'")

    print_step("STEP 4: TRACE WORKFLOW IMPACT")
    impacts = httpx.get(f"{BACKEND_URL}/api/changes/{user_change['id']}/impact").json()["impacts"]
    for imp in impacts:
        print(f"  Workflow: {imp['workflow_name']}")
        print(f"  Reason: {imp['reason']}")
        print(f"  Source Files: {imp['source_files']}")
        print(f"  Tests: {imp['tests']}")

    print_step("STEP 5: PROPOSE BACKWARD-COMPATIBLE ADAPTER")
    proposal = httpx.post(f"{BACKEND_URL}/api/changes/{user_change['id']}/repair-proposals").json()
    print(f"Proposal ID: {proposal['id']}")
    print(f"Adapter Type: {proposal['repair_type']}")
    print(f"Confidence: {int(proposal['confidence'] * 100)}%")
    print("Generated Diff:")
    print(proposal["diff"].strip())

    print_step("STEP 6: RUN SANDBOX VALIDATION")
    val = httpx.post(f"{BACKEND_URL}/api/repairs/{proposal['id']}/validate", timeout=15.0).json()
    print(f"Validation Status: {val['status'].upper()} ({val['duration_ms']}ms)")
    print(f"Command Output:\n{val['output_summary']}")
    assert val["status"] == "passed", "Validation must pass before applying"

    print_step("STEP 7: APPLY APPROVED REPAIR & RE-RUN CLIENT WORKFLOW")
    app_res = httpx.post(f"{BACKEND_URL}/api/repairs/{proposal['id']}/apply").json()
    print(f"Apply Result: {app_res['status']} - {app_res['message']}")

    # Verify live test now passes
    test_pass = subprocess.run("pytest -q demo-app/tests/test_user_profile.py", shell=True, capture_output=True, text=True)
    print(f"Live Client Test After Repair:\n{test_pass.stdout.strip()}")
    assert test_pass.returncode == 0, "Test must pass after repair is applied"

    print_step("STEP 8: TEST SEARCH API CURSOR PAGINATION DRIFT")
    httpx.post(f"{BACKEND_URL}/api/demo/set-scenario", json={"scenario": "search_v2"})
    scan_search = httpx.post(f"{BACKEND_URL}/api/scans").json()
    search_change = next(c for c in scan_search["changes"] if c["dependency_id"] == "search-api")
    print(f"Detected: {search_change['change_type']} (Severity: {search_change['severity']})")

    search_prop = httpx.post(f"{BACKEND_URL}/api/changes/{search_change['id']}/repair-proposals").json()
    print(f"Bounded Proposal: {search_prop['repair_type']}")
    print(f"Assumptions: {search_prop['assumptions']}")

    print_step("STEP 9: SAFETY ENFORCEMENT ON PAYMENTS SEMANTIC UNCERTAINTY")
    httpx.post(f"{BACKEND_URL}/api/demo/set-scenario", json={"scenario": "payments_v2"})
    scan_pay = httpx.post(f"{BACKEND_URL}/api/scans").json()
    pay_change = next(c for c in scan_pay["changes"] if c["dependency_id"] == "payments-api")
    print(f"Detected: {pay_change['change_type']} (Severity: {pay_change['severity']})")

    pay_prop = httpx.post(f"{BACKEND_URL}/api/changes/{pay_change['id']}/repair-proposals").json()
    print(f"Status: {pay_prop['status']}")
    print(f"Policy Action: {pay_prop['error_message']}")

    # Verify attempt to apply is blocked
    r_block = httpx.post(f"{BACKEND_URL}/api/repairs/{pay_prop['id']}/apply")
    print(f"Attempt Apply: HTTP {r_block.status_code} - {r_block.json()['detail']}")
    assert r_block.status_code == 400, "Applying uncertain repair must be blocked"

    print_step("STEP 10: CLEAN RESET")
    httpx.post(f"{BACKEND_URL}/api/demo/reset")
    final_test = subprocess.run("pytest -q demo-app/tests", shell=True, capture_output=True, text=True)
    print(f"All demo tests restored to clean baseline:\n{final_test.stdout.strip()}")
    assert final_test.returncode == 0

    print("\n" + "=" * 70)
    print("  LIVE DEMO & ACCEPTANCE CRITERIA WALKTHROUGH COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
