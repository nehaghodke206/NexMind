# Dependency Guardian — End-to-End Sample API Demo

This demo provides a realistic, multi-file FastAPI e-commerce application demonstrating API contract evolution, breaking and non-breaking change detection, **local Ollama AI reasoning and risk insights**, and **automated regression test generation and safe execution**.

---

## 1. Architecture Overview

The demo models an e-commerce backend across two versions:
- **`v1` (Baseline)**: Initial production release.
- **`v2` (Current)**: Evolved revision introducing deliberate breaking and non-breaking contract changes.

Both versions share an identical layered architecture:

```
demo/sample-api/
├── contracts/
│   ├── openapi-v1.json            # Genuine baseline OpenAPI 3.1 contract
│   └── openapi-v2.json            # Genuine current OpenAPI 3.1 contract
├── generated-tests/               # Isolated sandbox for candidate & approved regression tests
│   ├── candidate_tests.json       # Synthesized candidate test metadata
│   ├── test_candidate_regression_v2.py # Candidate pytest suite
│   ├── approved_tests.json        # Explicitly approved test metadata
│   └── test_approved_regression_v2.py  # Approved pytest suite ready for execution
├── reports/
│   ├── findings.json              # Algorithmic detection results (JSON)
│   ├── summary.txt                # Algorithmic detection summary (table)
│   ├── findings-ai.json           # Pure AI detection results (JSON)
│   ├── summary-ai.txt             # Pure AI detection summary (table)
│   ├── findings-hybrid.json       # Hybrid AI detection results (JSON)
│   ├── summary-hybrid.txt         # Hybrid AI detection summary (table)
│   └── insights-hybrid.txt        # Structured AI risk insights & mitigation guidance
├── scripts/
│   └── generate_contracts.py      # Dynamic contract extraction from FastAPI apps
├── tests/
│   ├── conftest.py                # Test environment configuration
│   ├── test_v1_api.py             # Runtime tests for v1 endpoints (5 tests)
│   ├── test_v2_api.py             # Runtime tests for v2 endpoints (5 tests)
│   └── test_detection_assertions.py # Automated verification of findings and rules (4 tests)
├── versions/
│   ├── v1/app/                    # Baseline FastAPI application
│   │   ├── api/                   # Users, Products, Orders, Payments routers
│   │   ├── core/                  # Configuration & settings
│   │   ├── repositories/          # In-memory data repositories
│   │   ├── schemas/               # Pydantic v2 data transfer models
│   │   ├── services/              # Business logic workflows
│   │   └── main.py                # FastAPI application entrypoint
│   └── v2/app/                    # Modified FastAPI application (with contract changes)
│       ├── api/
│       ├── core/
│       ├── repositories/
│       ├── schemas/
│       ├── services/
│       └── main.py
├── requirements.txt               # Demo Python package requirements
├── run_demo.sh                    # Automated demo runner (Kali Linux/POSIX)
└── README.md                      # This documentation
```

---

## 2. Matrix of Deliberate Contract Changes & Detection Rules

| Location / Endpoint | Change Description | Compatibility | Detection Rule ID |
| :--- | :--- | :--- | :--- |
| `GET /api/v1/payments/{payment_id}/receipt` | Deprecated receipt path removed | `breaking` | `RULE-PATH-REMOVED` |
| `DELETE /api/v1/products/{product_id}` | Direct deletion method removed | `breaking` | `RULE-METHOD-REMOVED` |
| `GET /api/v1/products` | Required query parameter `store_id` added | `breaking` | `RULE-REQUIRED-PARAM-ADDED` |
| `POST /api/v1/payments` | Required body field `currency` added | `breaking` | `RULE-REQUIRED-FIELD-ADDED` |
| `POST /api/v1/payments` | Value `crypto` removed from `PaymentMethod` enum | `breaking` | `RULE-ENUM-VALUE-REMOVED` |
| `GET & POST /api/v1/payments` | Field `amount` type changed from `number` to `string` | `breaking` | `RULE-FIELD-TYPE-CHANGED` |
| `GET, POST, PUT /api/v1/products` | Inventory field `stock` removed from response schema | `breaking` | `RULE-RESPONSE-FIELD-REMOVED` |
| `GET /api/v1/users` | Optional query parameter `search` added | `non_breaking` | `RULE-FIELD-ADDED-OPTIONAL` |
| `GET, POST, PUT /api/v1/users` | Optional field `notes` added to `UserResponse` | `non_breaking` | `RULE-FIELD-ADDED-OPTIONAL` |
| `GET, POST, PUT /api/v1/products` | Optional field `sku` added to `ProductResponse` | `non_breaking` | `RULE-FIELD-ADDED-OPTIONAL` |
| `GET, POST, PATCH /api/v1/orders` | Optional field `discount_amount` added to `OrderResponse` | `non_breaking` | `RULE-FIELD-ADDED-OPTIONAL` |

---

## 3. Quick Start & Execution

### One-Command Full Demo (Kali Linux / POSIX)

From the repository root:

```bash
./demo/sample-api/run_demo.sh
```

This single command executes the entire 9-step workflow:
1. Performs AI provider diagnostic check (`--check-ai --provider ollama`).
2. Runs all 10 runtime tests for v1 and v2.
3. Generates genuine OpenAPI 3.1 specifications dynamically from the FastAPI apps.
4. Compares v1 against v2 in **Mode A (Algorithmic)**.
5. Runs **Mode B (Pure AI)** with local Ollama inference.
6. Runs **Mode C (Hybrid)** with Ollama reasoning enrichment and exports AI risk insights.
7. Runs **Mode D (Step 1)** generating candidate regression tests into `demo/sample-api/generated-tests`.
8. Runs **Mode D (Step 2)** reviewing and approving candidate tests (`--approve-tests`).
9. Runs **Mode D (Step 3)** safely executing approved regression tests against v2 (`--execute-tests`).
10. Runs automated assertion tests verifying rule IDs and schema locations.

---

### Step-by-Step CLI Commands

#### 1. Setup Environment

**Kali Linux / Bash:**
```bash
export PYTHONPATH="agents/detection:demo/sample-api:${PYTHONPATH:-}"
```

**Windows PowerShell:**
```powershell
$env:PYTHONPATH = "agents\detection;demo\sample-api;$env:PYTHONPATH"
```

#### 2. Verify Local Ollama Diagnostic Status

```bash
python3 -m dependency_guardian.cli --check-ai --provider ollama
```

#### 3. Run Algorithmic Detection (Deterministic)

```bash
# Output human-readable summary
python3 -m dependency_guardian.cli \
  demo/sample-api/contracts/openapi-v1.json \
  demo/sample-api/contracts/openapi-v2.json \
  --mode algorithmic \
  --format summary

# Output JSON report
python3 -m dependency_guardian.cli \
  demo/sample-api/contracts/openapi-v1.json \
  demo/sample-api/contracts/openapi-v2.json \
  --mode algorithmic \
  --format json \
  --output demo/sample-api/reports/findings.json
```

#### 4. Run Hybrid Detection with Local Ollama AI & Risk Insights

```bash
python3 -m dependency_guardian.cli \
  demo/sample-api/contracts/openapi-v1.json \
  demo/sample-api/contracts/openapi-v2.json \
  --mode hybrid \
  --provider ollama \
  --timeout 90 \
  --format summary \
  --insights-output demo/sample-api/reports/insights-hybrid.txt
```

#### 5. Generate Candidate Regression Tests (Dry-Run Preview)

```bash
python3 -m dependency_guardian.cli \
  demo/sample-api/contracts/openapi-v1.json \
  demo/sample-api/contracts/openapi-v2.json \
  --mode algorithmic \
  --preview-tests
```

#### 6. Generate, Approve, and Execute Regression Tests

```bash
# Step 1: Synthesize candidate tests
python3 -m dependency_guardian.cli \
  demo/sample-api/contracts/openapi-v1.json \
  demo/sample-api/contracts/openapi-v2.json \
  --mode algorithmic \
  --generate-tests demo/sample-api/generated-tests \
  --test-target v2

# Step 2: Explicit approval gate
python3 -m dependency_guardian.cli \
  --approve-tests demo/sample-api/generated-tests \
  --test-target v2

# Step 3: Safe execution
python3 -m dependency_guardian.cli \
  --execute-tests demo/sample-api/generated-tests \
  --test-target v2
```

---

## 4. AI Insights & Risk Report Structure

The generated risk report (`reports/insights-hybrid.txt`) provides executive-level decision support:

1. **Executive Summary**: High-level synthesis of contract evolutions and consumer risk profile.
2. **Quantitative Breakdown**: Total findings by compatibility (breaking, non-breaking) and severity.
3. **Consumer Impact Analysis**: Concrete explanation of which client workflows fail and why.
4. **Top Breaking Changes**: Prioritized list of the most critical breaking changes.
5. **Recommended Remediation & Migration**: Actionable step-by-step migration guide for client libraries.
6. **Recommended Regression Tests**: Scenarios to verify client resilience and error handling.
7. **Suggested Order of Resolution**: Recommended sequence for addressing contract differences.
8. **Grounding (Facts vs. AI Hypotheses)**: Authoritative contract changes versus inferred operational hypotheses.
9. **Assumptions & Uncertainty**: Explicit boundaries of OpenAPI contract analysis.

---

## 5. Security & Test Sandboxing

- **AST Safety Validation**: Generated Python code is parsed into an Abstract Syntax Tree (AST) before file creation. Any use of forbidden modules (`os`, `subprocess`, `sys`, `socket`) or functions (`eval`, `exec`, `open`) triggers immediate rejection.
- **Path Confinement**: Test artifacts are strictly confined to designated test directories (e.g. `demo/sample-api/generated-tests`).
- **Approval Gate**: Candidate tests cannot be executed without explicit review and approval.
- **Execution Sandboxing**: Tests run via `pytest` with a configurable execution timeout (default: 30s) capturing stdout, stderr, and exit codes.
