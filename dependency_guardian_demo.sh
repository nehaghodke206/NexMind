
#!/usr/bin/env bash
# Dependency Guardian: end-to-end hackathon demo runner.
# Run from any directory. Does not apply repairs or overwrite source files.

set -Eeuo pipefail

ROOT="${DG_ROOT:-$HOME/Dnyaneshwar/HackWave}"
PY="${DG_PYTHON:-$ROOT/agents/detection/.venv/bin/python3}"
DEMO="$ROOT/demo/sample-api"
CONTRACTS="$DEMO/contracts"
REPORTS="$DEMO/reports"
SCAN_OUT="$REPORTS/repo-scan"
TEST_OUT="$DEMO/generated-tests"
INSIGHTS="$REPORTS/insights-hybrid.txt"
LOG_DIR="$REPORTS/live-demo"
LOG="$LOG_DIR/demo-$(date +%Y%m%d-%H%M%S).log"


mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG") 2>&1

step() { printf '\n\033[1;36m[%s/%s] %s\033[0m\n' "$1" "$TOTAL" "$2"; }
die() { printf '\nERROR: %s\nSee log: %s\n' "$*" "$LOG" >&2; exit 1; }
run() {
  printf '\n$'
  printf ' %q' "$@"
  printf '\n'
  "$@"
}
need_file() { [[ -f "$1" ]] || die "Required file not found: $1"; }

TOTAL=8
printf 'Dependency Guardian — live demo\nRepository: %s\nLog: %s\n' "$ROOT" "$LOG"

[[ -d "$ROOT" ]] || die "Repository directory not found: $ROOT (set DG_ROOT to your repo path)"
[[ -x "$PY" ]] || die "Detection Python not found/executable: $PY (set DG_PYTHON if your venv differs)"
[[ -d "$DEMO" ]] || die "Sample API directory not found: $DEMO"

cd "$ROOT"
printf '\nWorking directory: %s\nPython: %s\n' "$PWD" "$PY"

step 1 "$TOTAL" "Preflight checks"
run "$PY" --version
run "$PY" -m dependency_guardian.cli --help >/dev/null || die "Detection CLI help failed. Check package/import setup."
if command -v ollama >/dev/null 2>&1; then
  echo "Ollama CLI found:"
  ollama list || echo "WARNING: ollama list failed; AI stage may fall back or fail."
else
  echo "WARNING: Ollama CLI not found. AI stage may use fallback or fail."
fi

step 2 "$TOTAL" "Scan repository and discover endpoints"
run "$PY" -m dependency_guardian.cli scan-repo "$DEMO" -o "$SCAN_OUT" --format summary

step 3 "$TOTAL" "Generate OpenAPI contracts from sample API apps"
run "$PY" "$DEMO/scripts/generate_contracts.py"
need_file "$CONTRACTS/openapi-v1.json"
need_file "$CONTRACTS/openapi-v2.json"
echo "Contract files verified:"
ls -lh "$CONTRACTS/openapi-v1.json" "$CONTRACTS/openapi-v2.json"

step 4 "$TOTAL" "Compare API versions with deterministic rules"
run "$PY" -m dependency_guardian.cli \
  "$CONTRACTS/openapi-v1.json" "$CONTRACTS/openapi-v2.json" \
  --mode algorithmic --format summary

step 5 "$TOTAL" "Generate AI risk insights (Ollama/hybrid)"
run "$PY" -m dependency_guardian.cli \
  "$CONTRACTS/openapi-v1.json" "$CONTRACTS/openapi-v2.json" \
  --mode hybrid --provider ollama --format summary \
  --insights-output "$INSIGHTS"
need_file "$INSIGHTS"
echo "AI insights preview:"
head -n 28 "$INSIGHTS"

step 6 "$TOTAL" "Generate candidate regression tests"
run "$PY" -m dependency_guardian.cli \
  "$CONTRACTS/openapi-v1.json" "$CONTRACTS/openapi-v2.json" \
  --generate-tests "$TEST_OUT" --test-target v2
need_file "$TEST_OUT/candidate_tests.json"

step 7 "$TOTAL" "Approve candidate tests and execute approved tests"
echo "Approval is an explicit gate. Review candidate tests before continuing."
echo "Candidate artifacts:"
ls -lh "$TEST_OUT"
if [[ "${DG_AUTO_APPROVE:-0}" == "1" ]]; then
  echo "DG_AUTO_APPROVE=1 set: proceeding to approval command."
else
  read -r -p "Have you reviewed the candidate tests and want to approve them? Type YES: " answer
  [[ "$answer" == "YES" ]] || die "Approval cancelled. Candidate tests remain available at $TEST_OUT"
fi
run "$PY" -m dependency_guardian.cli \
  --approve-tests "$TEST_OUT" --test-target v2
run "$PY" -m dependency_guardian.cli \
  --execute-tests "$TEST_OUT" --test-target v2

step 8 "$TOTAL" "Propose a repair (proposal only; does not apply it)"
FINDINGS="$REPORTS/findings.json"
TARGET="$DEMO/tests/test_v1_api.py"
if [[ -f "$FINDINGS" && -f "$TARGET" && -d "$ROOT/agents/repair" ]]; then
  PYTHONPATH="$ROOT/agents/repair:$ROOT/agents/detection${PYTHONPATH:+:$PYTHONPATH}" \
    "$PY" -m repair_agent.cli \
    --finding "$FINDINGS" --file "$TARGET" \
    --provider ollama --format summary
  echo "Repair proposal command completed. Inspect the emitted diff and proposal metadata."
else
  echo "SKIPPED repair proposal: required finding file, target file, or repair package is missing."
  echo "Finding expected: $FINDINGS"
  echo "Target expected:  $TARGET"
  echo "Confirm the actual findings output and Repair Agent CLI options before running repair manually."
fi

printf '\n\033[1;32mDemo sequence finished.\033[0m\n'
printf 'Reports: %s\nCandidate/approved tests: %s\nLog: %s\n' "$REPORTS" "$TEST_OUT" "$LOG"
printf 'No repair was automatically applied.\n'
