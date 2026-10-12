#!/usr/bin/env bash
# ==============================================================================
# Dependency Guardian — Minimal Localhost Integration Demo Runner
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

# Set up PYTHONPATH
export PYTHONPATH="${REPO_ROOT}/agents/detection:${REPO_ROOT}/agents/repair:${REPO_ROOT}/services/backend:${REPO_ROOT}/demo/sample-api:${REPO_ROOT}:${PYTHONPATH:-}"

# Locate Python environment
if [ -d "services/backend/.venv" ]; then
    VENV_PY="services/backend/.venv/bin/python3"
    VENV_PYTEST="services/backend/.venv/bin/pytest"
else
    VENV_PY="python3"
    VENV_PYTEST="pytest"
fi

BACKEND_URL="${GUARDIAN_BACKEND_URL:-http://localhost:8000}"

echo "========================================================================"
echo " Dependency Guardian — Localhost External Integration Demo"
echo "========================================================================"
echo "Python binary:     $(${VENV_PY} --version) (${VENV_PY})"
echo "Working directory: ${REPO_ROOT}"
echo "Target Backend:    ${BACKEND_URL}"
echo ""

# 1. Check Local Backend Health
echo "[1/3] Checking connectivity to Dependency Guardian backend at ${BACKEND_URL}..."
if curl -s -f "${BACKEND_URL}/api/v1/health" > /dev/null 2>&1; then
    echo "[+] Upstream Guardian Backend is ACTIVE at ${BACKEND_URL}!"
    curl -s "${BACKEND_URL}/api/v1/health" | head -n 5
    echo ""
else
    echo "[!] Warning: Upstream backend at ${BACKEND_URL} is not responding."
    echo "    Start it in another terminal: cd services/backend && uvicorn app.main:app --port 8000"
fi
echo ""

# 2. Run Automated Pytest Suite
echo "[2/4] Running automated tests (working, contract drift, detection assertions)..."
${VENV_PYTEST} "${SCRIPT_DIR}/tests" -v
echo "[+] All automated endpoint and contract drift tests PASSED!"
echo ""

# 3. Run Dependency Guardian Repository Scan for Contract Reconciliation
echo "[3/4] Running Dependency Guardian Repository Intelligence Scan..."
${VENV_PY} -m dependency_guardian.cli scan-repo demo/sample-api --format summary
echo ""

# 4. Run Dependency Guardian Live API Contract Validation
echo "[4/4] Running Dependency Guardian Live External API Contract Validation..."
${VENV_PY} -m dependency_guardian.cli validate-api "${SCRIPT_DIR}/dependency-guardian.yml" --format summary || true
echo ""

echo "========================================================================"
echo " Demo Completed Successfully!"
echo " Review reports/repository-inventory/INTEGRATION_MAP.md to inspect"
echo " all discovered external API calls to http://localhost:8000."
echo " Review openapi.json for the canonical demo API contract specification."
echo "========================================================================"
