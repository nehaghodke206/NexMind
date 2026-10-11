# Dependency Guardian — Modular Detection Agent & Local Ollama AI Integration

The **Detection Agent** evaluates OpenAPI 3.0.x, 3.1.x, and Swagger 2.0 specifications against known-good baselines to proactively identify breaking changes, classify compatibility risks, generate AST-safe regression test suites, and deliver AI-grounded risk insights via local Ollama inference.

---

## Architecture & Execution Modes

Dependency Guardian provides four distinct, fully working operational modes:

| Mode | Flag | AI Required | Description |
| :--- | :--- | :--- | :--- |
| **A. Algorithmic** | `--mode algorithmic` | **No** (Deterministic offline) | Compares contracts with deterministic rule comparator. Produces canonical rule IDs, affected operations, compatibility classifications, and locations. Zero network transmission. |
| **B. AI** | `--mode ai --provider ollama` | **Yes** (Local Ollama or Mock) | Uses local Ollama model to evaluate semantic contract evolutions. Applies strict schema grounding to reject hallucinated endpoints. Generates risk insights and test guidance. |
| **C. Hybrid** | `--mode hybrid --provider ollama` | **Yes** (Ollama + Deterministic fallback) | Executes deterministic detection first; sends findings to local Ollama for enrichment (reasoning, consumer impact, remediation, test scenarios). Preserves all deterministic classifications as ground truth. |
| **D. Test Suite** | `--generate-tests`, `--approve-tests`, `--execute-tests` | Optional (AI or Algorithmic) | Generates targeted pytest regression tests for 7+ contract breaking changes. Enforces AST safety validation, isolated directory sandboxing, candidate-approval gates, and safe execution. |

---

## Local Ollama Setup & Diagnostic Verification

Dependency Guardian runs inference **entirely locally** through Ollama's HTTP API (`http://localhost:11434`), keeping specifications, code, and findings private and air-gapped.

### 1. Verify Ollama Installation & Running Daemon

**Linux / Kali:**
```bash
# Verify CLI
ollama --version

# Verify Ollama service is active
systemctl status ollama || curl -s http://localhost:11434/api/tags

# Download a code-specialized model
ollama pull qwen2.5-coder:3b
```

**Windows (PowerShell):**
```powershell
# Verify Ollama service
Get-Service ollama
curl.exe http://localhost:11434/api/tags

# Pull model
ollama pull qwen2.5-coder:3b
```

### 2. Run Dependency Guardian AI Diagnostic Check

Verify endpoint connectivity and model availability before running analyses:

```bash
dependency-guardian --check-ai --provider ollama
```

Expected output:
```text
========================================================================
 Dependency Guardian AI Provider Diagnostic
========================================================================
 Provider:         ollama
 Endpoint:         http://localhost:11434
 Reachable:        True
 Installed Models: ['qwen2.5-coder:3b']
 Selected Model:   qwen2.5-coder:3b
 Model Ready:      True
========================================================================
```

---

## Configuration & Precedence

Dependency Guardian resolves configurations following a strict 5-level hierarchy:

1. **CLI Arguments**: (Highest priority) `--base-url`, `--model`, `--timeout`, `--fallback-policy`, `--mode`
2. **Environment Variables**:
   - `DEPENDENCY_GUARDIAN_AI_PROVIDER` (e.g. `ollama`, `mock`)
   - `DEPENDENCY_GUARDIAN_AI_MODEL` (e.g. `qwen2.5-coder:3b`)
   - `DEPENDENCY_GUARDIAN_AI_BASE_URL` (default: `http://localhost:11434`)
   - `DEPENDENCY_GUARDIAN_AI_TIMEOUT_SECONDS` (default: `60.0`)
   - `DEPENDENCY_GUARDIAN_AI_FALLBACK_POLICY` (`fallback_to_algorithmic` or `fail`)
3. **Workspace Configuration**: `.dependency-guardian.json` in workspace root
4. **User Configuration**: `~/.dependency-guardian/config.json`
5. **Built-in Defaults**: (Lowest priority)

---

## Command Reference & Usage Examples

### Mode A: Deterministic Algorithmic Detection
```bash
# Output JSON
dependency-guardian baseline.json current.json --mode algorithmic --format json --output reports/findings.json

# Output human-readable summary table
dependency-guardian baseline.json current.json --mode algorithmic --format summary

# Fail CI/CD build if breaking changes exist (exit code 1)
dependency-guardian baseline.json current.json --mode algorithmic --fail-on-breaking
```

### Mode B: Pure AI Detection (Local Ollama)
```bash
dependency-guardian baseline.json current.json \
  --mode ai \
  --provider ollama \
  --model qwen2.5-coder:3b \
  --format summary
```

### Mode C: Hybrid Detection & Risk Insights
```bash
dependency-guardian baseline.json current.json \
  --mode hybrid \
  --provider ollama \
  --format summary \
  --insights-output reports/insights-hybrid.txt
```

### Mode D: Regression Test Generation & Execution Workflow

#### Step 1: Dry-Run Preview
Preview candidate regression tests in stdout without writing any files:
```bash
dependency-guardian baseline.json current.json --mode algorithmic --preview-tests
```

#### Step 2: Generate Candidate Tests
Synthesize targeted, AST-validated pytest regression tests into isolated directory:
```bash
dependency-guardian baseline.json current.json \
  --mode algorithmic \
  --generate-tests demo/sample-api/generated-tests \
  --test-target v2
```

Artifacts created:
- `demo/sample-api/generated-tests/candidate_tests.json`: Structured test metadata
- `demo/sample-api/generated-tests/test_candidate_regression_v2.py`: Candidate pytest test file

#### Step 3: Review & Explicit Approval
Before executing newly synthesized test code, explicit approval promotes candidate tests:
```bash
dependency-guardian --approve-tests demo/sample-api/generated-tests --test-target v2
```
Artifacts promoted:
- `demo/sample-api/generated-tests/test_approved_regression_v2.py`
- `demo/sample-api/generated-tests/approved_tests.json`

#### Step 4: Safe Execution
Safely executes approved regression tests against the target API version with configurable timeout:
```bash
dependency-guardian --execute-tests demo/sample-api/generated-tests --test-target v2
```

---

## Running the Test Suite (Offline / Air-Gapped)

All 59 unit and integration tests run **100% offline** without requiring a live Ollama daemon, paid API keys, or databases:

```bash
# From repository root
PYTHONPATH=agents/detection pytest agents/detection/tests -v

# Run demo runtime and detection assertion tests
PYTHONPATH=demo/sample-api:agents/detection pytest demo/sample-api/tests -v
```

---

## Troubleshooting Common Ollama Issues

| Issue | Cause | Resolution |
| :--- | :--- | :--- |
| `Connection refused to http://localhost:11434` | Ollama daemon not running | Run `ollama serve` or `systemctl start ollama` |
| `Model 'xyz' not found in Ollama` | Requested model not downloaded | Run `ollama pull qwen2.5-coder:3b` |
| `Ollama inference timed out after 30s` | Complex prompt or slow CPU inference | Pass `--timeout 90` or set `DEPENDENCY_GUARDIAN_AI_TIMEOUT_SECONDS=90` |
| `Ollama output was not valid JSON` | Model generated conversational text | OllamaProvider automatically strips markdown code fences and sets `format: json` |
