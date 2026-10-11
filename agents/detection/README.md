# Dependency Guardian — Detection & Repository Intelligence Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
<!-- [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) -->
[![Tests: 70 Passed](https://img.shields.io/badge/tests-70%20passed-brightgreen.svg)]()
[![Offline Safe](https://img.shields.io/badge/privacy-100%25%20offline%20ready-success.svg)]()

> **Proactive API contract drift detection, automated repository intelligence, evidence-backed API documentation, and AST-guarded regression test generation powered by deterministic analysis and local Ollama AI.**

---

## Table of Contents

1. [Project Overview & Core Use Cases](#1-project-overview--core-use-cases)
2. [Architecture & System Design](#2-architecture--system-design)
3. [Prerequisites & Supported Environments](#3-prerequisites--supported-environments)
4. [Installation & Setup](#4-installation--setup)
   - [Kali / Linux / macOS](#kali--linux--macos)
   - [Windows (PowerShell)](#windows-powershell)
   - [Verifying CLI Installation](#verifying-cli-installation)
5. [Configuration & Precedence Hierarchy](#5-configuration--precedence-hierarchy)
6. [Complete Command Reference](#6-complete-command-reference)
   - [Global Options & Version](#global-options--version)
   - [`scan-repo`: Repository Intelligence & Documentation](#scan-repo-repository-intelligence--documentation)
   - [Contract Comparison (Algorithmic, AI, Hybrid)](#contract-comparison-algorithmic-ai-hybrid)
   - [`--check-ai`: Diagnostic Provider Check](#--check-ai-diagnostic-provider-check)
   - [Regression Testing Workflow (`preview`, `generate`, `approve`, `execute`)](#regression-testing-workflow-preview-generate-approve-execute)
7. [Repository Scanning & Generated Deliverables](#7-repository-scanning--generated-deliverables)
   - [Deliverable Matrix](#deliverable-matrix)
   - [Multi-Language & Lockfile Scanning](#multi-language--lockfile-scanning)
   - [Framework AST Parsers](#framework-ast-parsers)
   - [Contract Discrepancy Classification](#contract-discrepancy-classification)
   - [Confidence Scoring & Static Analysis Boundaries](#confidence-scoring--static-analysis-boundaries)
8. [Local Ollama AI Integration](#8-local-ollama-ai-integration)
   - [Ollama Setup & Daemon Management](#ollama-setup--daemon-management)
   - [Model Configuration & Diagnostics](#model-configuration--diagnostics)
   - [Hybrid Mode Reasoning & Risk Insights](#hybrid-mode-reasoning--risk-insights)
9. [Regression Testing & AST Safety Sandboxing](#9-regression-testing--ast-safety-sandboxing)
10. [Report Interpretation, Rule Taxonomy & Severity](#10-report-interpretation-rule-taxonomy--severity)
11. [Security Guidance & Secret Redaction](#11-security-guidance--secret-redaction)
12. [Troubleshooting & Frequently Asked Questions](#12-troubleshooting--frequently-asked-questions)
13. [Testing & Developer Guide](#13-testing--developer-guide)

---

## 1. Project Overview & Core Use Cases

Modern distributed systems and microservices depend heavily on external and internal HTTP/JSON APIs. When external APIs change without warning, or when repositories evolve without updated documentation, downstream consumers break silently in production.

**Dependency Guardian** solves these challenges through two primary operational capabilities:

1. **Automated Repository Intelligence & Documentation Agent (`scan-repo`)**:
   Deeply scans codebase directories across multiple programming languages (Python, JavaScript/TypeScript, Go, Rust), discovers manifests and lockfiles, resolves dependency versions, inspects Abstract Syntax Trees (AST) to verify whether declared packages are actively imported, tracks outbound integrations (databases, queues, third-party HTTP calls, cloud SDKs) while strictly redacting secrets, extracts framework routes (FastAPI, Flask, Express), reconciles them against OpenAPI specs to detect ghost or undocumented endpoints, evaluates test coverage, and auto-generates 6 evidence-backed deliverables.

2. **API Contract Drift Detection & Regression Safeguard**:
   Compares baseline and current OpenAPI/Swagger specifications using a deterministic rule engine, an air-gapped local Ollama AI model, or a hybrid combination. Evaluates semantic evolutions, rejects AI hallucinations, synthesizes AST-validated pytest regression suites, and enforces a mandatory human approval gate before test execution.

### Key Use Cases

- **CI/CD Breaking Change Prevention**: Fail deployment pipelines automatically (`--fail-on-breaking`) if third-party or internal API updates introduce breaking changes (removed paths, changed field types, newly required parameters).
- **Automated Repository Reverse-Engineering**: Produce an exhaustive, audit-ready inventory and interactive API reference for legacy repositories lacking up-to-date documentation.
- **Contract-to-Code Reconciliation**: Identify "undocumented endpoints" (routes active in code but omitted from OpenAPI specs) and "ghost endpoints" (routes defined in OpenAPI docs that have no corresponding handler in source code).
- **Safe Regression Test Generation**: Auto-synthesize targeted integration tests asserting breaking change contracts, sandboxed through an AST safety validator that blocks dangerous system calls.
- **Air-Gapped / Privacy-Preserving AI**: Run semantic risk evaluation entirely on local hardware using Ollama (`qwen2.5-coder:3b`, etc.) without streaming proprietary schemas to cloud providers.

---

## 2. Architecture & System Design

```
                          ┌────────────────────────────────────────────────────────┐
                          │            dependency-guardian CLI Engine              │
                          └──────────────────────────┬─────────────────────────────┘
                                                     │
                     ┌───────────────────────────────┴───────────────────────────────┐
                     ▼                                                               ▼
  ┌─────────────────────────────────────┐                         ┌─────────────────────────────────────┐
  │         scan-repo Subcommand        │                         │     Contract Drift Subcommand       │
  └──────────────────┬──────────────────┘                         └──────────────────┬──────────────────┘
                     │                                                               │
     ┌───────────────┼───────────────┐                               ┌───────────────┼───────────────┐
     ▼               ▼               ▼                               ▼               ▼               ▼
┌──────────┐   ┌───────────┐   ┌───────────┐                   ┌───────────┐   ┌───────────┐   ┌───────────┐
│Manifest &│   │ Framework │   │   Test    │                   │Algorithmic│   │Pure AI    │   │Hybrid Mode│
│ Lockfile │   │    AST    │   │ Coverage  │                   │Comparator │   │ (Ollama)  │   │(Rule + AI)│
│ Scanner  │   │  Scanner  │   │  Tracer   │                   └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
└────┬─────┘   └─────┬─────┘   └─────┬─────┘                         │               │               │
     │               │               │                               └───────────────┼───────────────┘
     └───────────────┼───────────────┘                                               ▼
                     ▼                                                ┌─────────────────────────────┐
  ┌─────────────────────────────────────┐                             │   Regression Test Engine    │
  │     Documentation Generator         │                             │  - Preview / Generate       │
  │  - repository-inventory.json        │                             │  - AST Safety Validator     │
  │  - DEPENDENCY_REPORT.md             │                             │  - Approval Gate            │
  │  - API_REFERENCE.md                 │                             │  - Sandboxed Runner         │
  │  - INTEGRATION_MAP.md               │                             └─────────────────────────────┘
  │  - TEST_COVERAGE.md                 │
  │  - openapi.enriched.json            │
  └─────────────────────────────────────┘
```

---

## 3. Prerequisites & Supported Environments

### System Requirements

- **Operating Systems**:
  - Linux: Debian, Ubuntu, Kali Linux, Fedora, Arch Linux
  - macOS: 12.0+ (Apple Silicon or Intel)
  - Windows: Windows 10/11 (PowerShell or WSL2)
- **Python**: 3.10, 3.11, 3.12, 3.13, or 3.14 (Verified on Python 3.14.7)
- **Local AI (Optional)**: [Ollama](https://ollama.com/) (v0.1.28+) with `qwen2.5-coder:3b` or equivalent code model for AI/hybrid modes. Offline algorithmic scanning requires **no external dependencies**.

---

## 4. Installation & Setup

### Kali / Linux / macOS

```bash
# 1. Clone repository and navigate to the detection agent directory
cd agents/detection

# 2. Create and activate an isolated Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Upgrade pip and install the package in editable mode with development tools
pip install --upgrade pip
pip install -e ".[dev]"

# 4. Verify CLI availability
dependency-guardian --version
```

### Windows (PowerShell)

```powershell
# 1. Navigate to detection agent directory
cd agents\detection

# 2. Create and activate Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Upgrade pip and install package
python -m pip install --upgrade pip
pip install -e ".[dev]"

# 4. Verify CLI availability
dependency-guardian --version
```

### Verifying CLI Installation

Run both help commands to verify that entrypoints are registered correctly in your environment:

```bash
# Verify base CLI
dependency-guardian --help

# Verify repository intelligence subcommand
dependency-guardian scan-repo --help
```

Expected output includes the usage banner:
```text
usage: dependency-guardian [-h] [--version] [--baseline BASELINE_OPT] ...
usage: dependency-guardian scan-repo [-h] [--version] [--output OUTPUT] ...
```

---

## 5. Configuration & Precedence Hierarchy

Dependency Guardian uses a strict **5-level hierarchical configuration loader**. Higher levels override lower levels without exception:

```
Level 1: CLI Flags (--mode, --base-url, --model, --timeout, etc.)  [HIGHEST]
   │
Level 2: Environment Variables (DEPENDENCY_GUARDIAN_*)
   │
Level 3: Workspace File (.dependency-guardian.json or .dependency-guardian.yaml)
   │
Level 4: User Global Config (~/.dependency-guardian/config.json)
   │
Level 5: Built-in Defaults                                         [LOWEST]
```

### Environment Variables

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `DEPENDENCY_GUARDIAN_DETECTION_MODE` | `string` | `algorithmic` | Default mode: `algorithmic`, `ai`, or `hybrid` |
| `DEPENDENCY_GUARDIAN_AI_PROVIDER` | `string` | `mock` | AI engine: `mock`, `ollama`, or `hosted` |
| `DEPENDENCY_GUARDIAN_AI_MODEL` | `string` | `qwen2.5-coder:3b` | Target LLM model name |
| `DEPENDENCY_GUARDIAN_AI_BASE_URL` | `string` | `http://localhost:11434` | Ollama daemon or OpenAI-compatible endpoint |
| `DEPENDENCY_GUARDIAN_AI_TIMEOUT_SECONDS` | `float` | `60.0` | Request timeout for AI inference |
| `DEPENDENCY_GUARDIAN_AI_FALLBACK_POLICY` | `string` | `fallback_to_algorithmic` | Behavior on AI failure: `fail` or `fallback_to_algorithmic` |
| `DEPENDENCY_GUARDIAN_AI_API_KEY` | `string` | `None` | Authentication key (redacted from logs) |
| `DEPENDENCY_GUARDIAN_BACKEND_BASE_URL` | `string` | `http://127.0.0.1:8000/api/v1` | Dependency Guardian backend URL |

### Sample Workspace Configuration (`.dependency-guardian.json`)

Create `.dependency-guardian.json` in your project root to standardize settings across teams:

```json
{
  "detection_mode": "hybrid",
  "ai_provider": "ollama",
  "ai_model": "qwen2.5-coder:3b",
  "ai_base_url": "http://localhost:11434",
  "ai_timeout_seconds": 90.0,
  "ai_fallback_policy": "fallback_to_algorithmic",
  "logging_level": "INFO"
}
```

---

## 6. Complete Command Reference

Every command and flag documented below has been verified against the CLI parser and test suite.

### Global Options & Version

```bash
# Print installed version
dependency-guardian --version
# Output: dependency-guardian 0.1.0

# Print scan-repo subcommand version
dependency-guardian scan-repo --version
# Output: dependency-guardian scan-repo 0.1.0

# Global help
dependency-guardian --help
```

---

### `scan-repo`: Repository Intelligence & Documentation

Scans an entire codebase repository to produce a machine-readable inventory, dependency audit, integration topology, test coverage report, and enriched OpenAPI spec.

#### Syntax
```bash
dependency-guardian scan-repo <repository_path> [options]
```

#### Arguments & Options

| Parameter | Type / Choices | Default | Description |
| :--- | :--- | :--- | :--- |
| `repository_path` | Positional path | **Required** | Path to repository root directory to scan. |
| `--output`, `-o` | Path | `reports/repository-inventory` | Target output directory (or JSON path whose parent is used). |
| `--format`, `-f` | `summary` \| `json` \| `both` | `summary` | Terminal output format. |
| `--mode`, `-m` | `algorithmic` \| `ai` \| `hybrid` | `algorithmic` | Scanning mode: `algorithmic` (offline AST), `ai`, `hybrid`. |
| `--provider` | `mock` \| `ollama` \| `hosted` | `None` | AI provider for hybrid semantic enrichment. |
| `--model` | String | `None` | AI model override (e.g. `qwen2.5-coder:3b`). |
| `--base-url` | URL string | `None` | Custom base URL for Ollama / AI endpoint. |
| `--api-key` | String | `None` | API key if hosted AI is used (redacted from logs). |
| `--timeout` | Float | `None` | Inference timeout in seconds. |
| `--no-enrichment` | Flag | `False` | Disables generation of `openapi.enriched.json`. |
| `--verbose`, `-v` | Flag | `False` | Enable debug logging. |
| `--quiet`, `-q` | Flag | `False` | Suppress non-error console output. |

#### Realistic Examples

```bash
# 1. Standard offline scan with human-readable terminal summary
dependency-guardian scan-repo agents/detection/tests/fixtures/fixture_repo \
  --output reports/repository-inventory \
  --format summary

# 2. Machine-readable JSON output piped to jq
dependency-guardian scan-repo /path/to/my-backend \
  --format json > my-repo-inventory.json

# 3. Hybrid scan with local Ollama semantic documentation enrichment
dependency-guardian scan-repo /path/to/my-backend \
  --mode hybrid \
  --provider ollama \
  --model qwen2.5-coder:3b \
  --output reports/full-audit

# 4. Fast scan disabling OpenAPI enrichment
dependency-guardian scan-repo /path/to/my-backend --no-enrichment
```

#### Expected Terminal Summary Output
```text
============================================================================
 DEPENDENCY GUARDIAN — REPOSITORY INTELLIGENCE & API INVENTORY SUMMARY
============================================================================
 Repository Path:       /home/last-hope/Dnyaneshwar/HackWave/agents/detection/tests/fixtures/fixture_repo
 Languages Detected:   JavaScript, Python
 Frameworks Detected:  Express, FastAPI
 Source Files Scanned: 3
----------------------------------------------------------------------------
 Dependencies:         9 total (8 used in code, 1 declared but unused)
 External Integrations: 4 (Databases, Queues, HTTP calls, Cloud SDKs)
 Discovered Endpoints: 6
   - Framework AST:     3
   - OpenAPI Spec:      1
   - Hybrid (Both):     2
 Spec Discrepancies:   4 (3 undocumented, 1 ghost)
 API Test Coverage:    50.0% (3/6 endpoints tested, 3 gaps)
----------------------------------------------------------------------------
 Generated Documentation Deliverables:
   [+] repository-inventory.json -> reports/repository-inventory/repository-inventory.json
   [+] DEPENDENCY_REPORT.md      -> reports/repository-inventory/DEPENDENCY_REPORT.md
   [+] API_REFERENCE.md          -> reports/repository-inventory/API_REFERENCE.md
   [+] INTEGRATION_MAP.md        -> reports/repository-inventory/INTEGRATION_MAP.md
   [+] TEST_COVERAGE.md          -> reports/repository-inventory/TEST_COVERAGE.md
   [+] openapi.enriched.json     -> reports/repository-inventory/openapi.enriched.json
============================================================================
```

#### Exit Codes & Remedies
- **Exit Code 0**: Scan completed successfully; deliverables written.
- **Exit Code 1**: Scanner encountered an unhandled exception or parsing failure.
  - *Remedy*: Check terminal stack trace or run with `-v` to inspect syntax parsing issues.
- **Exit Code 2**: Invalid repository path or directory does not exist.
  - *Remedy*: Verify directory path exists (`ls -d <path>`).

---

### Contract Comparison (Algorithmic, AI, Hybrid)

Compares a baseline OpenAPI contract against an updated contract to detect breaking changes.

#### Syntax
```bash
dependency-guardian <baseline_spec> <current_spec> [options]
# Or using explicit flags:
dependency-guardian -b <baseline_spec> -c <current_spec> [options]
```

#### Options Reference

| Option | Choices | Default | Description |
| :--- | :--- | :--- | :--- |
| `--mode`, `-m` | `algorithmic` \| `ai` \| `hybrid` | `algorithmic` | Detection engine mode. |
| `--format`, `-f` | `json` \| `summary` \| `both` | `json` | Display format on stdout. |
| `--output`, `-o` | Path | `None` | Write detection results JSON to file. |
| `--fail-on-breaking` | Flag | `False` | Exit with status code `1` if breaking changes exist (ideal for CI). |
| `--insights-output` | Path | `None` | Save AI risk analysis report (`.txt` or `.json`). |
| `--provider` | `mock` \| `ollama` \| `hosted` | `None` | AI provider for `ai` or `hybrid` mode. |
| `--model` | String | `None` | Model identifier (e.g., `qwen2.5-coder:3b`). |
| `--base-url` | URL string | `None` | Custom endpoint for Ollama / hosted model. |
| `--timeout` | Float | `60.0` | Request timeout in seconds. |
| `--fallback-policy` | `fail` \| `fallback_to_algorithmic` | `fallback_to_algorithmic` | Action taken if AI request fails. |

#### Realistic Examples

```bash
# 1. Deterministic offline diff with summary table (CI check)
dependency-guardian demo/sample-api/contracts/openapi-v1.json \
  demo/sample-api/contracts/openapi-v2.json \
  --mode algorithmic \
  --format summary \
  --fail-on-breaking

# 2. Output detailed JSON to disk and display summary
dependency-guardian demo/sample-api/contracts/openapi-v1.json \
  demo/sample-api/contracts/openapi-v2.json \
  --mode algorithmic \
  --format both \
  --output reports/contract-diff.json

# 3. Hybrid detection using local Ollama and saving human-readable AI risk insights
dependency-guardian demo/sample-api/contracts/openapi-v1.json \
  demo/sample-api/contracts/openapi-v2.json \
  --mode hybrid \
  --provider ollama \
  --model qwen2.5-coder:3b \
  --format summary \
  --insights-output reports/risk-insights.txt
```

#### Exit Codes
- **Exit Code 0**: Detection completed cleanly (or non-breaking changes found when `--fail-on-breaking` is used).
- **Exit Code 1**: Breaking changes detected when `--fail-on-breaking` is set, or detection engine failed.
- **Exit Code 2**: Specification file not found or invalid JSON/YAML syntax.

---

### `--check-ai`: Diagnostic Provider Check

Proactively tests network reachability, daemon health, and model availability before running analyses.

#### Syntax
```bash
dependency-guardian --check-ai [--provider {mock,ollama,hosted}] [--model MODEL] [--base-url URL]
```

#### Example & Output
```bash
dependency-guardian --check-ai --provider ollama --model qwen2.5-coder:3b
```
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

#### Exit Codes
- **Exit Code 0**: AI provider is reachable and target model is ready.
- **Exit Code 1**: Daemon is unreachable, endpoint timed out, or requested model is not installed.

---

### Regression Testing Workflow (`preview`, `generate`, `approve`, `execute`)

Synthesizes pytest regression tests targeting breaking contract changes, enforced with AST safety checks and explicit human review gates.

```
[Contract Diff] ──> Step 1: --preview-tests (Dry-Run Stdout)
       │
       └──> Step 2: --generate-tests <DIR>
                   (Writes candidate_tests.json & test_candidate_regression_v2.py)
                         │
                         ▼
             Step 3: --approve-tests <DIR>
                   (AST validation + Promotes to test_approved_regression_v2.py)
                         │
                         ▼
             Step 4: --execute-tests <DIR>
                   (Executes approved tests inside isolated pytest sandbox)
```

#### Step 1: Preview Candidate Tests (Dry-Run)
Inspect synthesized test code in stdout without writing any files to disk:
```bash
dependency-guardian demo/sample-api/contracts/openapi-v1.json \
  demo/sample-api/contracts/openapi-v2.json \
  --mode algorithmic \
  --preview-tests
```

#### Step 2: Generate Candidate Tests
Synthesize targeted tests into an isolated candidate directory:
```bash
dependency-guardian demo/sample-api/contracts/openapi-v1.json \
  demo/sample-api/contracts/openapi-v2.json \
  --mode algorithmic \
  --generate-tests demo/sample-api/generated-tests \
  --test-target v2
```
*Generated files:*
- `demo/sample-api/generated-tests/candidate_tests.json`
- `demo/sample-api/generated-tests/test_candidate_regression_v2.py`

#### Step 3: Review & Explicit Approval
Before unreviewed test code can ever execute, a developer or CI gate must explicitly approve it:
```bash
dependency-guardian --approve-tests demo/sample-api/generated-tests --test-target v2
```
*Promoted files:*
- `demo/sample-api/generated-tests/approved_tests.json`
- `demo/sample-api/generated-tests/test_approved_regression_v2.py`

#### Step 4: Safe Execution
Safely executes the approved regression suite against the targeted service version:
```bash
dependency-guardian --execute-tests demo/sample-api/generated-tests --test-target v2
```
```text
========================================================================
 DEPENDENCY GUARDIAN — REGRESSION TEST EXECUTION SUMMARY
========================================================================
 Test File:       demo/sample-api/generated-tests/test_approved_regression_v2.py
 Target Version:  v2
 Duration:        0.84s
 Total Tests:     7
 Passed:          7
 Failed:          0
 Errors:          0
 Exit Code:       0
------------------------------------------------------------------------
 [+] All regression tests executed and verified successfully.
========================================================================
```

> [!IMPORTANT]
> If candidate tests exist but have not been approved, `--execute-tests` refuses to run and exits with code `1`, preventing unauthorized arbitrary code execution.

---

## 7. Repository Scanning & Generated Deliverables

The `scan-repo` command performs multi-language AST inspection and outputs 6 complementary deliverables:

### Deliverable Matrix

| Deliverable File | Format | Purpose | Key Contents |
| :--- | :--- | :--- | :--- |
| **`repository-inventory.json`** | JSON | Machine-readable single-source-of-truth inventory | Scanned languages, frameworks, dependencies, external integrations, endpoints, discrepancies, test coverage metrics. |
| **`DEPENDENCY_REPORT.md`** | Markdown | Complete dependency & external integration audit | Declared constraint vs resolved lockfile version, import/usage tracking, purpose, doc URLs, CVE advisories, and isolated external service table. |
| **`API_REFERENCE.md`** | Markdown | Complete endpoint-by-endpoint reference manual | HTTP methods, route paths, query/header/cookie parameters, request bodies, response schemas, types, required flags, defaults, constraints, enums, auth, handlers, line numbers, error cases, side effects, and confidence. |
| **`INTEGRATION_MAP.md`** | Markdown | Architecture & integration topology | Cross-reference table mapping routes to handlers, imported dependencies, external HTTP calls, databases, message brokers, and cloud SDKs. |
| **`TEST_COVERAGE.md`** | Markdown | API verification & test coverage analysis | Discovered endpoints mapped to test files, coverage percentage, untested endpoint gaps, tested integrations, and verification recommendations. |
| **`openapi.enriched.json`** | OpenAPI 3.1.0 | Enriched OpenAPI specification | Synthesized OpenAPI document incorporating discovered AST fields without mutating original specification files. |

---

### Multi-Language & Lockfile Scanning

The dependency scanner parses manifests and lockfiles across 4 major programming ecosystems:

| Ecosystem | Manifest Files | Lockfiles | What Is Extracted |
| :--- | :--- | :--- | :--- |
| **Python** | `requirements.txt`, `pyproject.toml`, `Pipfile` | `Pipfile.lock`, `poetry.lock` | Declared constraints, resolved pinned versions, AST import locations, purpose, documentation URLs, known CVEs. |
| **Node.js** | `package.json` | `package-lock.json` | Dependencies, devDependencies, resolved lockfile versions, AST `require`/`import` verification. |
| **Go** | `go.mod` | `go.sum` | Modules, minimum versions, cryptographic checksum presence. |
| **Rust** | `Cargo.toml` | `Cargo.lock` | Crates, feature flags, pinned package versions. |

#### Usage Tracking: Declared vs. Used
Unlike traditional SCA tools that only read manifest files, Dependency Guardian cross-references declared packages with the Abstract Syntax Tree (AST) of the repository's source code:
- **`is_used: true`**: Package is declared in manifest and actively imported in source code (`import requests`, `const express = require('express')`).
- **`is_used: false`**: Package is declared in manifest but **never imported** anywhere in the scanned repository (classified as unused bloat).

---

### Framework AST Parsers

Dependency Guardian implements framework-specific AST parsers that extract route structures directly from code:

1. **FastAPI (Python AST)**:
   - Decorators: `@app.get(...)`, `@app.post(...)`, `@router.put(...)`, etc.
   - Pydantic models: Resolves type annotations (`UserCreate`, `OrderResponse`), extracting field names, types, defaults, required flags, and docstrings.
   - Parameters: Detects `Query(...)`, `Path(...)`, `Header(...)`, and `Cookie(...)`.
   - Error cases: Inspects `raise HTTPException(status_code=404, detail="...")` to document expected error status codes.
2. **Flask (Python AST)**:
   - Decorators: `@app.route('/path', methods=['GET', 'POST'])`.
   - Parameters: Extracts `<int:user_id>`, `<string:item_id>` from URL path variables.
   - Responses & errors: Detects `jsonify(...)`, `abort(400)`.
3. **Express.js (JavaScript AST)**:
   - Methods: `app.get('/path', handler)`, `router.post('/path', handler)`.
   - Parameters: Extracts `:id`, query usage (`req.query.foo`), header usage (`req.headers['x-api-key']`).
   - Responses: Inspects `res.status(201).json(...)`.

---

### Contract Discrepancy Classification

When an existing OpenAPI or Swagger file is present in the repository, Dependency Guardian reconciles the code against the specification:

```
Source Code Routes (AST)                  OpenAPI Spec Paths
      ┌─────────────┐                          ┌─────────────┐
      │ GET /items  ├──────────────────────────┤ GET /items  │  ==> Verified Match (Confidence: 1.0)
      └─────────────┘                          └─────────────┘
      ┌─────────────┐
      │ POST /orders├──────────────────────────  [MISSING]      ==> undocumented_endpoint (Confidence: 0.85)
      └─────────────┘
                                               ┌─────────────┐
        [MISSING]   ───────────────────────────┤ DELETE /logs│  ==> ghost_endpoint (Confidence: 0.90)
                                               └─────────────┘
```

- **`undocumented_endpoint`**: The route exists and is active in source code, but is completely missing from the OpenAPI documentation.
- **`ghost_endpoint`**: The route is documented in the OpenAPI specification, but does **not exist** in application code (often leftover from deprecated endpoints).

---

### Confidence Scoring & Static Analysis Boundaries

Every discovered endpoint and integration includes an explicit `confidence` score and `evidence_source`:

- **Confidence `1.0` (Explicit Fact)**: Backed by both OpenAPI specification and direct AST handler mapping.
- **Confidence `0.9` (Direct AST)**: Parsed directly from statically declared framework routing decorators (`@app.get(...)`).
- **Confidence `0.7` (Heuristic / Inferred)**: Inferred from surrounding patterns (e.g., dynamic helper functions, generic request wrappers).

#### What Static Analysis Cannot Infer
Static AST analysis has inherent physical boundaries. Dependency Guardian explicitly classifies and reports these limitations rather than guessing:
- **Runtime Dynamic Routes**: Routes constructed at runtime via variables or string concatenation (`app[method]('/api/' + prefix)`) are reported under `unresolved_dynamic_routes`.
- **Unsupported Frameworks**: Proprietary or unhandled routing libraries are logged under `unsupported_frameworks`.
- **Dynamic Dependency Injection**: Dependencies resolved strictly at runtime via dynamic reflection containers without static type annotations.

---

## 8. Local Ollama AI Integration

Dependency Guardian supports **air-gapped semantic AI analysis** via local Ollama inference. Spec files and source code never leave your machine.

### Ollama Setup & Daemon Management

#### Linux / Kali Setup
```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Start daemon (if not run via systemd)
systemctl start ollama || ollama serve

# 3. Pull recommended code model
ollama pull qwen2.5-coder:3b
```

#### Windows PowerShell Setup
```powershell
# 1. Download installer from https://ollama.com/download/windows
# 2. Verify daemon is running
Get-Service ollama
curl.exe http://localhost:11434/api/tags

# 3. Pull model
ollama pull qwen2.5-coder:3b
```

### Model Configuration & Diagnostics

Run the built-in diagnostic command to confirm that Ollama is ready:
```bash
dependency-guardian --check-ai --provider ollama --model qwen2.5-coder:3b
```

If Ollama is running and the model is present, the command exits with code `0`.

### Hybrid Mode Reasoning & Risk Insights

In **Hybrid Mode** (`--mode hybrid`), Dependency Guardian runs the deterministic algorithmic comparator first. Deterministic classifications (`breaking`, `non_breaking`) serve as immutable ground truth. The findings are then sent to Ollama to generate:
- **Architectural Reasoning**: Why the change impacts downstream clients.
- **Consumer Impact Assessment**: Which client workflows will fail.
- **Actionable Remediation**: Specific code patterns to adapt to the change.
- **Test Scenarios**: Concrete edge cases to test.

Save insights to disk with `--insights-output`:
```bash
dependency-guardian demo/sample-api/contracts/openapi-v1.json \
  demo/sample-api/contracts/openapi-v2.json \
  --mode hybrid \
  --provider ollama \
  --model qwen2.5-coder:3b \
  --insights-output reports/risk-insights.txt
```

---

## 9. Regression Testing & AST Safety Sandboxing

Executing AI-synthesized code carries inherent risks of prompt injection or arbitrary code execution. Dependency Guardian mitigates this through a multi-tiered security sandbox:

```
[Candidate Code]
       │
       ▼
┌────────────────────────────────────────────────────────┐
│             AST Safety Validator Engine                │
├────────────────────────────────────────────────────────┤
│  [X] Rejects forbidden modules (os, sys, subprocess,   │
│      shutil, socket, pty, ctypes, importlib, pickle)   │
│  [X] Rejects dangerous builtins (eval, exec, compile,  │
│      __import__, open with write mode)                 │
│  [X] Allows only authorized test runners (pytest,      │
│      httpx, requests, unittest)                        │
└──────────────────────────┬─────────────────────────────┘
                           │ Passed AST Check
                           ▼
┌────────────────────────────────────────────────────────┐
│            Manual / CI Approval Gate                   │
│   (Requires explicit 'dependency-guardian               │
│    --approve-tests' command)                           │
└──────────────────────────┬─────────────────────────────┘
                           │ Approved
                           ▼
┌────────────────────────────────────────────────────────┐
│         Isolated Temporary Sandbox Runner              │
│   (Executes approved tests with bounded timeout)       │
└────────────────────────────────────────────────────────┘
```

1. **AST Safety Validator**: Every synthesized test file is parsed into a Python AST before writing or execution. Any reference to `os.system`, `subprocess.Popen`, `eval()`, or unapproved modules raises an immediate validation rejection.
2. **Mandatory Approval Gate**: Candidate tests are written to `test_candidate_regression_*.py`. They cannot be executed until `dependency-guardian --approve-tests` is called to promote them to `test_approved_regression_*.py`.
3. **Sandbox Execution**: Tests are run in a subprocess sandbox with bounded timeouts, capturing stdout/stderr and returning structured execution summaries.

---

## 10. Report Interpretation, Rule Taxonomy & Severity

### Canonical Rule IDs

| Rule Identifier | Compatibility | Default Severity | Description |
| :--- | :--- | :--- | :--- |
| `RULE-PATH-REMOVED` | `breaking` | `high` | API route was deleted from specification. |
| `RULE-METHOD-REMOVED` | `breaking` | `high` | HTTP verb was removed from an existing route. |
| `RULE-FIELD-TYPE-CHANGED` | `breaking` | `high` | Payload field schema type changed incompatibly (e.g. `number` $\to$ `string`). |
| `RULE-REQUIRED-PARAM-ADDED` | `breaking` | `high` | A new required query, path, or header parameter was added. |
| `RULE-REQUIRED-FIELD-ADDED` | `breaking` | `high` | A new required field was added to a request body schema. |
| `RULE-RESPONSE-FIELD-REMOVED` | `breaking` | `high` | Field was deleted from a response schema. |
| `RULE-STATUS-CODE-REMOVED` | `breaking` | `medium` | Expected HTTP response status code was removed. |
| `RULE-ENUM-VALUE-REMOVED` | `breaking` | `high` (req) / `potentially_breaking` (res) | Allowed enum value was removed from request or response. |
| `RULE-FIELD-ADDED-OPTIONAL` | `non_breaking` | `low` | Optional property was added to a schema. |
| `RULE-OPTIONAL-PARAM-ADDED` | `non_breaking` | `low` | New optional query/header parameter added. |

### Finding Schema

Every finding emitted in `reports/*.json` adheres to the Pydantic canonical finding schema:

```json
{
  "id": "find_16972e38-89c0-449e-b8d9-ba5441ecb4c7",
  "rule_id": "RULE-FIELD-TYPE-CHANGED",
  "fingerprint": "dg:rule-field-type-changed:a61a0ebc905391c4",
  "compatibility": "breaking",
  "severity": "high",
  "path": "/api/v1/payments",
  "method": "POST",
  "schema_location": "paths./api/v1/payments.post.responses.201.content.application/json.schema.properties.amount",
  "previous_value": "number",
  "current_value": "string",
  "message": "Schema type changed incompatibly from 'number' to 'string' at ...",
  "evidence": {
    "previous_type": "number",
    "current_type": "string"
  },
  "confidence": 1.0,
  "source": "algorithmic",
  "review_required": false,
  "ai_reasoning": null,
  "created_at": "2026-10-11T07:54:33.295484Z"
}
```

---

## 11. Security Guidance & Secret Redaction

### Automatic Secret Sanitization
Dependency Guardian automatically inspects environment files (`.env`), configuration files, and code strings during scanning. When outbound integrations (database connection strings, third-party APIs, webhooks) are extracted, credentials are sanitized:

- Basic authentication URLs: `https://user:password@service.com` $\to$ `https://[REDACTED]@service.com`
- API keys: `sk_live_...`, `ghp_...`, `Bearer ...` $\to$ `[REDACTED]`
- Database URLs: `postgresql://admin:secret123@db:5432/app` $\to$ `postgresql://[REDACTED]@db:5432/app`
- Manifest secrets: Private token headers or query parameters are systematically redacted before emission into `repository-inventory.json` or markdown reports.

### Air-Gapped Compliance
All algorithmic rules, AST parsing, and local Ollama interactions operate strictly within localhost (`127.0.0.1`). No specification contracts, source files, or vulnerability data are ever transmitted to external servers without explicit user configuration.

---

## 12. Troubleshooting & Frequently Asked Questions

### Common Issues & Solutions

| Symptom / Error | Cause | Remediation |
| :--- | :--- | :--- |
| `Connection refused to http://localhost:11434` | Ollama daemon is not running. | Run `ollama serve` or `systemctl start ollama`. Confirm with `curl http://localhost:11434/api/tags`. |
| `Model 'qwen2.5-coder:3b' not found in Ollama` | Model has not been pulled locally. | Run `ollama pull qwen2.5-coder:3b`. |
| `Ollama inference timed out after 60s` | Inference is slow on CPU hardware. | Pass `--timeout 120.0` or set `DEPENDENCY_GUARDIAN_AI_TIMEOUT_SECONDS=120.0`. |
| `Candidate tests exist ... but have not been approved` | `--execute-tests` was run before approval. | Run `dependency-guardian --approve-tests <DIR>` to approve tests before execution. |
| `Specification file not found: ...` (Exit 2) | File path is incorrect or file does not exist. | Verify file paths relative to current working directory (`ls <path>`). |
| `Repository path does not exist or is not a directory` (Exit 2) | Target repository folder missing. | Provide a valid existing directory path to `scan-repo`. |
| `AI output was not valid JSON` | Model generated conversational text. | Ensure you are using a code-specialized model like `qwen2.5-coder:3b`. The Ollama provider automatically requests `format: "json"`. |

---

## 13. Testing & Developer Guide

### Running the Test Suite (100% Offline)

All 70 unit and integration tests run offline without external network connections or live Ollama daemons:

```bash
# Run full test suite with verbose output
pytest agents/detection/tests -v

# Run repository intelligence tests only
pytest agents/detection/tests/test_repo_intelligence.py -v

# Run CLI command tests
pytest agents/detection/tests/test_cli.py -v
```

### Running the Integration Demo

```bash
# Execute the complete 9-stage verification demo
bash demo/sample-api/run_demo.sh
```

---

*Dependency Guardian Detection Agent & Repository Intelligence Engine — Built for robust, evidence-backed API reliability.*
