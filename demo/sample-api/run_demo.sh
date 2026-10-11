#!/usr/bin/env bash
# ==============================================================================
# Dependency Guardian — End-to-End Multi-Mode Demo Runner
# Kali Linux, Ubuntu, & POSIX Bash Script
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

# Set up PYTHONPATH
export PYTHONPATH="${REPO_ROOT}/agents/detection:${REPO_ROOT}/demo/sample-api:${REPO_ROOT}:${PYTHONPATH:-}"

# Locate Python environment
if [ -d "services/backend/.venv" ]; then
    VENV_PY="services/backend/.venv/bin/python3"
    VENV_PYTEST="services/backend/.venv/bin/pytest"
elif [ -d "agents/detection/.venv" ]; then
    VENV_PY="agents/detection/.venv/bin/python3"
    VENV_PYTEST="agents/detection/.venv/bin/pytest"
else
    VENV_PY="python3"
    VENV_PYTEST="pytest"
fi

DG_CMD="${VENV_PY} -m dependency_guardian.cli"

REPORTS_DIR="${SCRIPT_DIR}/reports"
CONTRACTS_DIR="${SCRIPT_DIR}/contracts"
GENERATED_TESTS_DIR="${SCRIPT_DIR}/generated-tests"
mkdir -p "${REPORTS_DIR}" "${CONTRACTS_DIR}" "${GENERATED_TESTS_DIR}"

echo "========================================================================"
echo " Dependency Guardian Demo: Multi-Mode Contract Evolution & Regression"
echo "========================================================================"
echo "Python binary:     $(${VENV_PY} --version) (${VENV_PY})"
echo "Working directory: ${REPO_ROOT}"
echo ""

# 0. AI Provider Diagnostic Health Check
echo "[0/9] Checking Local Ollama AI Provider Health..."
OLLAMA_AVAILABLE=false
if ${DG_CMD} --check-ai --provider ollama; then
    echo "[+] Local Ollama endpoint is reachable with an available model!"
    OLLAMA_AVAILABLE=true
else
    echo "[!] Ollama is not currently available locally. Algorithmic mode remains authoritative;"
    echo "    offline testing will use mock AI provider."
fi
echo ""

# 1. Run Demo API Runtime Tests (v1 & v2)
echo "[1/9] Running runtime tests for Sample API v1 and v2..."
${VENV_PYTEST} "${SCRIPT_DIR}/tests/test_v1_api.py" "${SCRIPT_DIR}/tests/test_v2_api.py" -q
echo "[+] All v1 and v2 runtime tests passed!"
echo ""

# 2. Generate Genuine OpenAPI Specifications from v1 and v2
echo "[2/9] Generating genuine OpenAPI 3.1 contracts..."
${VENV_PY} "${SCRIPT_DIR}/scripts/generate_contracts.py"
echo ""

# 3. Mode A: Algorithmic Detection
echo "[3/9] Running Mode A: Algorithmic Detection (Deterministic Offline)..."
${DG_CMD} "${CONTRACTS_DIR}/openapi-v1.json" "${CONTRACTS_DIR}/openapi-v2.json" \
    --mode algorithmic \
    --format json \
    --output "${REPORTS_DIR}/findings.json"

${DG_CMD} "${CONTRACTS_DIR}/openapi-v1.json" "${CONTRACTS_DIR}/openapi-v2.json" \
    --mode algorithmic \
    --format summary > "${REPORTS_DIR}/summary.txt"

echo "[+] Algorithmic reports saved:"
echo "    - JSON report:    ${REPORTS_DIR}/findings.json"
echo "    - Summary report: ${REPORTS_DIR}/summary.txt"
echo ""

# 4. Mode B: Pure AI Detection (Ollama or Mock)
echo "[4/9] Running Mode B: AI Detection..."
if [ "${OLLAMA_AVAILABLE}" = "true" ]; then
    echo "    Executing pure AI contract comparison with local Ollama..."
    ${DG_CMD} "${CONTRACTS_DIR}/openapi-v1.json" "${CONTRACTS_DIR}/openapi-v2.json" \
        --mode ai \
        --provider ollama \
        --timeout 90 \
        --format json \
        --output "${REPORTS_DIR}/findings-ai.json"
    ${DG_CMD} "${CONTRACTS_DIR}/openapi-v1.json" "${CONTRACTS_DIR}/openapi-v2.json" \
        --mode ai \
        --provider ollama \
        --timeout 90 \
        --format summary > "${REPORTS_DIR}/summary-ai.txt"
    echo "[+] AI reports saved (Ollama inference):"
    echo "    - JSON report:    ${REPORTS_DIR}/findings-ai.json"
    echo "    - Summary report: ${REPORTS_DIR}/summary-ai.txt"
else
    echo "    [i] Ollama unavailable; demonstrating AI mode with mock provider..."
    ${DG_CMD} "${CONTRACTS_DIR}/openapi-v1.json" "${CONTRACTS_DIR}/openapi-v2.json" \
        --mode ai \
        --provider mock \
        --format json \
        --output "${REPORTS_DIR}/findings-ai.json"
fi
echo ""

# 5. Mode C: Hybrid Detection (Algorithmic + AI Enrichment & Risk Insights)
echo "[5/9] Running Mode C: Hybrid Mode & Risk Insights..."
if [ "${OLLAMA_AVAILABLE}" = "true" ]; then
    ${DG_CMD} "${CONTRACTS_DIR}/openapi-v1.json" "${CONTRACTS_DIR}/openapi-v2.json" \
        --mode hybrid \
        --provider ollama \
        --timeout 90 \
        --format json \
        --output "${REPORTS_DIR}/findings-hybrid.json" \
        --insights-output "${REPORTS_DIR}/insights-hybrid.txt"

    ${DG_CMD} "${CONTRACTS_DIR}/openapi-v1.json" "${CONTRACTS_DIR}/openapi-v2.json" \
        --mode hybrid \
        --provider ollama \
        --timeout 90 \
        --format summary > "${REPORTS_DIR}/summary-hybrid.txt"
    echo "[+] Hybrid reports & Risk Insights saved:"
    echo "    - JSON report:     ${REPORTS_DIR}/findings-hybrid.json"
    echo "    - Summary report:  ${REPORTS_DIR}/summary-hybrid.txt"
    echo "    - Risk Insights:   ${REPORTS_DIR}/insights-hybrid.txt"
else
    ${DG_CMD} "${CONTRACTS_DIR}/openapi-v1.json" "${CONTRACTS_DIR}/openapi-v2.json" \
        --mode hybrid \
        --provider mock \
        --format json \
        --output "${REPORTS_DIR}/findings-hybrid.json" \
        --insights-output "${REPORTS_DIR}/insights-hybrid.txt"
    ${DG_CMD} "${CONTRACTS_DIR}/openapi-v1.json" "${CONTRACTS_DIR}/openapi-v2.json" \
        --mode hybrid \
        --provider mock \
        --format summary > "${REPORTS_DIR}/summary-hybrid.txt"
fi
echo ""

# 6. Mode D - Step 1: Candidate Regression Test Generation & Dry-Run Preview
echo "[6/9] Mode D (Step 1): Generating Candidate Regression Tests..."
${DG_CMD} "${CONTRACTS_DIR}/openapi-v1.json" "${CONTRACTS_DIR}/openapi-v2.json" \
    --mode algorithmic \
    --generate-tests "${GENERATED_TESTS_DIR}" \
    --test-target v2

echo "[+] Candidate test artifacts created in ${GENERATED_TESTS_DIR}:"
ls -lh "${GENERATED_TESTS_DIR}"
echo ""

# 7. Mode D - Step 2: Test Validation & Explicit Approval
echo "[7/9] Mode D (Step 2): Reviewing and Approving Candidate Tests..."
${DG_CMD} --approve-tests "${GENERATED_TESTS_DIR}" --test-target v2
echo ""

# 8. Mode D - Step 3: Safe Execution of Approved Regression Tests
echo "[8/9] Mode D (Step 3): Executing Approved Regression Tests against v2..."
${DG_CMD} --execute-tests "${GENERATED_TESTS_DIR}" --test-target v2
echo ""

# 9. Run Automated Assertion Suite
echo "[9/9] Running Automated Validation Assertion Suite..."
${VENV_PYTEST} "${SCRIPT_DIR}/tests/test_detection_assertions.py" -v
echo ""

echo "========================================================================"
echo " Dependency Guardian Multi-Mode Demo Completed Successfully!"
echo "========================================================================"
echo ""
echo "Executive Risk Insights Preview:"
if [ -f "${REPORTS_DIR}/insights-hybrid.txt" ]; then
    head -n 28 "${REPORTS_DIR}/insights-hybrid.txt"
fi
echo ""
echo "Summary Table Preview (First 20 findings):"
head -n 25 "${REPORTS_DIR}/summary.txt"
echo ""
