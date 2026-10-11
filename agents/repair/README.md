# Dependency Guardian — Repair Agent

> **Proactive, backwards-compatible patch generation and temporary sandbox validation for API contract drift.**

The **Repair Agent** inspects breaking change findings emitted by Dependency Guardian, locates the affected application source code, generates backwards-compatible reviewable patches, and validates them in isolated temporary copy sandboxes.

---

## Core Safety Principle

> **Never modify original source files automatically.**

1. **Reviewable Diffs**: The agent generates clean, standard unified diffs (`difflib.unified_diff`) for developer review.
2. **Temporary Copy Sandboxes**: Proposed patches are written and validated exclusively inside temporary directory copies (`tempfile.TemporaryDirectory`).
3. **AST Safety & Syntax Checks**: Every candidate patch is validated using Python's Abstract Syntax Tree (`ast.parse`) to prevent syntax errors and block dangerous functions (`eval`, `exec`, `os.system`).
4. **Mandatory Human Approval**: All repair proposals flag `requires_human_review = True` by default.

---

## Architecture & Repair Pipeline

```
  Detection Finding (JSON)
           │
           ▼
┌────────────────────────────────────────────────────────┐
│ 1. Finding Normalizer & Validator                      │
│    - Verifies mandatory fields (id, rule_id, path)     │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 2. Code Inspector                                      │
│    - Locates target file directly or via workspace     │
│    - Reads content without modifying source code       │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 3. Patch Generator (Modular)                           │
│    - Deterministic compatibility adapters:             │
│        * Field rename & response removal adapters      │
│        * Numeric / string type coercion adapters       │
│        * Outbound request parameter handlers           │
│    - Local Ollama AI (qwen2.5-coder:3b) with fallback  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ 4. Temporary Copy Sandbox Validator                    │
│    - Copies target file to isolated temp directory     │
│    - AST syntax validation & safety inspection         │
│    - Optional test execution runner in sandbox         │
│    - Original source file remains 100% untouched       │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
  Structured RepairResult (JSON / Diff / Summary)
```

---

## Setup & Installation

### Kali / Linux / macOS

```bash
# 1. Activate project virtual environment
cd /path/to/HackWave
source agents/detection/.venv/bin/activate

# 2. Install Repair Agent in editable mode
pip install -e agents/repair

# 3. Verify CLI availability
dependency-guardian-repair --version
# Output: dependency-guardian-repair 0.1.0
```

### Windows (PowerShell)

```powershell
# 1. Activate virtual environment
cd \path\to\HackWave
.\agents\detection\.venv\Scripts\Activate.ps1

# 2. Install Repair Agent
pip install -e agents\repair

# 3. Verify CLI availability
dependency-guardian-repair --version
```

---

## Command Reference & Usage Examples

### 1. Basic Deterministic Repair

Generate a backwards-compatible field adapter and display a human-readable summary table:

```bash
dependency-guardian-repair \
  --finding finding.json \
  --file demo-app/src/services/user_service.py \
  --format summary
```

### 2. Inline Finding Payload

You can supply the detection finding directly as a JSON string:

```bash
dependency-guardian-repair \
  --finding '{"id": "find_001", "rule_id": "RULE-FIELD-RENAME-CANDIDATE", "path": "/users/{id}", "evidence": {"renamed_from": "name", "renamed_to": "display_name"}}' \
  --file demo-app/src/services/user_service.py \
  --format summary
```

### 3. Workspace Auto-Discovery

If `--file` is omitted, the inspector automatically searches the `--workspace` directory for files referencing the endpoint or affected fields:

```bash
dependency-guardian-repair \
  --finding finding.json \
  --workspace demo-app \
  --format summary
```

### 4. Local Ollama AI Patch Generation

When local Ollama is running (`http://localhost:11434`), request AI patch synthesis with automatic deterministic fallback if offline:

```bash
dependency-guardian-repair \
  --finding finding.json \
  --file demo-app/src/services/user_service.py \
  --provider ollama \
  --model qwen2.5-coder:3b \
  --format summary
```

### 5. Sandbox Validation with Automated Tests

Execute an automated test command inside the isolated temporary sandbox before declaring the patch validated:

```bash
dependency-guardian-repair \
  --finding finding.json \
  --file demo-app/src/services/user_service.py \
  --workspace demo-app \
  --test-cmd "pytest tests/test_user_profile.py" \
  --format summary
```

### 6. Output Formats

```bash
# Unified diff only
dependency-guardian-repair --finding finding.json --file service.py --format diff

# Machine-readable JSON
dependency-guardian-repair --finding finding.json --file service.py --format json

# Save JSON result to file
dependency-guardian-repair --finding finding.json --file service.py --output reports/repair-result.json
```

---

## Running Focused Tests

All 13 unit and integration tests run offline without external network dependencies:

```bash
PYTHONPATH=agents/repair pytest agents/repair/tests -v
```

Expected output:
```text
agents/repair/tests/test_repair_pipeline.py::test_successful_repair_proposal_field_rename PASSED
agents/repair/tests/test_repair_pipeline.py::test_successful_repair_proposal_removed_response_property PASSED
agents/repair/tests/test_repair_pipeline.py::test_successful_repair_proposal_field_type_coercion PASSED
agents/repair/tests/test_repair_pipeline.py::test_successful_repair_with_passing_sandbox_test PASSED
agents/repair/tests/test_repair_pipeline.py::test_invalid_finding_missing_required_fields PASSED
agents/repair/tests/test_repair_pipeline.py::test_invalid_finding_nonexistent_target_file PASSED
agents/repair/tests/test_repair_pipeline.py::test_invalid_finding_malformed_json_type PASSED
agents/repair/tests/test_repair_pipeline.py::test_failed_validation_syntax_error PASSED
agents/repair/tests/test_repair_pipeline.py::test_failed_validation_ast_safety_violation PASSED
agents/repair/tests/test_repair_pipeline.py::test_failed_validation_sandbox_test_failure PASSED
agents/repair/tests/test_repair_pipeline.py::test_cli_execution_with_finding_file PASSED
agents/repair/tests/test_repair_pipeline.py::test_workspace_auto_discovery_of_affected_file PASSED
agents/repair/tests/test_repair_pipeline.py::test_ollama_fallback_to_deterministic_when_offline PASSED

============================== 13 passed in 1.10s ==============================
```
