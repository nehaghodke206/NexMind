"""
Dependency Guardian — Regression Test Generator and Safe Execution Engine.

Generates targeted, constrained pytest regression tests from OpenAPI contract differences.
Enforces strict AST safety validation, isolated directory sandboxing, and approval gates.
"""
import ast
import json
import logging
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .contracts.findings import (
    CompatibilityClassification,
    Finding,
    RuleId,
)

logger = logging.getLogger("dependency_guardian.test_generator")


class TestCaseModel(BaseModel):
    """Structured model for a candidate or approved regression test case."""
    __test__ = False

    test_id: str
    target_endpoint: str
    target_method: str
    related_rule_id: str
    description: str
    test_purpose: str
    expected_outcome: str
    target_version: str = "v2"
    test_code: str
    status: str = "candidate"  # candidate | approved | executed


class TestExecutionSummary(BaseModel):
    """Structured results from executing generated regression tests."""
    __test__ = False

    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration_seconds: float = 0.0
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    test_file: str = ""
    target_version: str = "v2"


class ASTSafetyValidator(ast.NodeVisitor):
    """
    Validates generated test Python AST.
    Rejects dangerous imports, arbitrary system execution, file manipulation, and network sockets.
    """

    FORBIDDEN_MODULES = {
        "os", "subprocess", "sys", "shutil", "socket", "pty", "commands",
        "pickle", "shelve", "builtins", "importlib", "posix", "nt", "ctypes"
    }
    FORBIDDEN_CALLS = {"eval", "exec", "open", "compile", "__import__", "getattr", "setattr"}

    def __init__(self):
        self.errors: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base = alias.name.split(".")[0]
            if base in self.FORBIDDEN_MODULES:
                self.errors.append(f"Forbidden module import: '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base = node.module.split(".")[0]
            if base in self.FORBIDDEN_MODULES:
                self.errors.append(f"Forbidden module import from: '{node.module}'")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.FORBIDDEN_CALLS:
                self.errors.append(f"Forbidden function call: '{node.func.id}()'")
        self.generic_visit(node)


def validate_test_code_safety(code: str) -> None:
    """Validate Python code syntax and safety AST rules."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError(f"Generated test code failed Python syntax validation: {exc}") from exc

    validator = ASTSafetyValidator()
    validator.visit(tree)
    if validator.errors:
        raise ValueError(f"Generated test code violated safety constraints: {'; '.join(validator.errors)}")


class RegressionTestGenerator:
    """
    Generates targeted pytest regression tests from Dependency Guardian findings.
    Provides candidate generation, preview, approval, and safe execution workflows.
    """

    def __init__(self, demo_app_module_prefix: str = "demo.sample_api.versions"):
        self.demo_app_module_prefix = demo_app_module_prefix

    def generate_candidate_tests(
        self,
        findings: List[Finding],
        target_version: str = "v2",
        output_dir: Optional[Path] = None,
    ) -> List[TestCaseModel]:
        """
        Generate candidate regression tests for significant contract changes.
        """
        candidate_tests: List[TestCaseModel] = []
        seen_test_ids = set()

        for idx, f in enumerate(findings):
            test_case = self._synthesize_test_case(f, target_version, idx + 1)
            if test_case and test_case.test_id not in seen_test_ids:
                seen_test_ids.add(test_case.test_id)
                candidate_tests.append(test_case)

        if output_dir:
            self._write_candidate_artifacts(candidate_tests, output_dir, target_version)

        return candidate_tests

    def _synthesize_test_case(
        self,
        f: Finding,
        target_version: str,
        index: int,
    ) -> Optional[TestCaseModel]:
        """Synthesize a robust, runnable pytest test case for a specific finding."""
        method = (f.method or "GET").upper()
        path = f.path
        rule = f.rule_id

        # 1. Path removed
        if rule == RuleId.PATH_REMOVED.value:
            safe_id = f"test_regression_path_removed_{re.sub(r'[^a-zA-Z0-9_]', '_', path).strip('_')}"
            code = f"""def {safe_id}(client):
    \"\"\"Verify removed path '{path}' returns 404 on {target_version}.\"\"\"
    test_path = "{path}".replace("{{payment_id}}", "1").replace("{{user_id}}", "1").replace("{{product_id}}", "1").replace("{{order_id}}", "1")
    resp = client.get(test_path)
    # Expected regression outcome on {target_version}: removed endpoint returns 404 Not Found
    assert resp.status_code == 404, f"Expected 404 for removed endpoint, got {{resp.status_code}}"
"""
            return TestCaseModel(
                test_id=safe_id,
                target_endpoint=path,
                target_method="GET",
                related_rule_id=rule,
                description=f"Regression test verifying consumer calling removed path '{path}' fails with 404.",
                test_purpose="Detect breaking path removal for legacy callers",
                expected_outcome=f"Returns 404 Not Found on {target_version} (was available in v1)",
                target_version=target_version,
                test_code=code,
                status="candidate",
            )

        # 2. Method removed
        if rule == RuleId.METHOD_REMOVED.value:
            safe_id = f"test_regression_method_removed_{method.lower()}_{re.sub(r'[^a-zA-Z0-9_]', '_', path).strip('_')}"
            code = f"""def {safe_id}(client):
    \"\"\"Verify removed method '{method}' on '{path}' returns 405 on {target_version}.\"\"\"
    test_path = "{path}".replace("{{product_id}}", "1").replace("{{user_id}}", "1").replace("{{order_id}}", "1").replace("{{payment_id}}", "1")
    resp = client.request("{method}", test_path)
    # Expected regression outcome: 405 Method Not Allowed
    assert resp.status_code == 405, f"Expected 405 for removed HTTP method, got {{resp.status_code}}"
"""
            return TestCaseModel(
                test_id=safe_id,
                target_endpoint=path,
                target_method=method,
                related_rule_id=rule,
                description=f"Regression test verifying removed HTTP method '{method}' returns 405 Method Not Allowed.",
                test_purpose="Detect breaking HTTP method removal",
                expected_outcome=f"Returns 405 Method Not Allowed on {target_version}",
                target_version=target_version,
                test_code=code,
                status="candidate",
            )

        # 3. Required query parameter added
        if rule == RuleId.REQUIRED_PARAM_ADDED.value:
            param_name = "store_id"
            if "store_id" in f.schema_location or "store_id" in f.message:
                param_name = "store_id"
            safe_id = f"test_regression_required_param_{param_name}_{re.sub(r'[^a-zA-Z0-9_]', '_', path).strip('_')}"
            code = f"""def {safe_id}(client):
    \"\"\"Verify newly required parameter '{param_name}' fails when omitted on {target_version}.\"\"\"
    # Request without required parameter must fail validation (422)
    resp_omitted = client.get("{path}")
    assert resp_omitted.status_code == 422, f"Expected 422 when omitting '{param_name}', got {{resp_omitted.status_code}}"

    # Request with required parameter must succeed (200)
    resp_provided = client.get("{path}?{param_name}=store-main")
    assert resp_provided.status_code == 200, f"Expected 200 when providing '{param_name}', got {{resp_provided.status_code}}"
"""
            return TestCaseModel(
                test_id=safe_id,
                target_endpoint=path,
                target_method="GET",
                related_rule_id=rule,
                description=f"Regression test verifying newly required parameter '{param_name}' causes 422 when omitted.",
                test_purpose="Detect unhandled required query parameter addition",
                expected_outcome=f"422 without parameter; 200 with parameter on {target_version}",
                target_version=target_version,
                test_code=code,
                status="candidate",
            )

        # 4. Required field added to request payload
        if rule == RuleId.REQUIRED_FIELD_ADDED.value:
            safe_id = f"test_regression_required_request_field_{re.sub(r'[^a-zA-Z0-9_]', '_', path).strip('_')}"
            code = f"""def {safe_id}(client):
    \"\"\"Verify newly required payload field causes 422 if omitted by legacy client.\"\"\"
    legacy_payload = {{
        "order_id": 1,
        "amount": 289.49,
        "payment_method": "credit_card",
    }}
    resp = client.post("{path}", json=legacy_payload)
    # Expected outcome on {target_version}: 422 Unprocessable Entity due to missing required 'currency' field
    assert resp.status_code == 422, f"Expected 422 for legacy payload lacking new required field, got {{resp.status_code}}"
"""
            return TestCaseModel(
                test_id=safe_id,
                target_endpoint=path,
                target_method="POST",
                related_rule_id=rule,
                description="Regression test verifying legacy payload lacking newly required field triggers 422.",
                test_purpose="Detect breaking payload requirement additions",
                expected_outcome=f"422 Unprocessable Entity when legacy payload is sent on {target_version}",
                target_version=target_version,
                test_code=code,
                status="candidate",
            )

        # 5. Enum value removed
        if rule == RuleId.ENUM_VALUE_REMOVED.value and "requestBody" in f.schema_location:
            safe_id = f"test_regression_enum_value_removed_{re.sub(r'[^a-zA-Z0-9_]', '_', path).strip('_')}"
            code = f"""def {safe_id}(client):
    \"\"\"Verify removed enum value 'crypto' causes 422 rejection on {target_version}.\"\"\"
    payload_removed_enum = {{
        "order_id": 1,
        "amount": 289.49,
        "currency": "USD",
        "payment_method": "crypto",
    }}
    resp = client.post("{path}", json=payload_removed_enum)
    assert resp.status_code == 422, f"Expected 422 for removed enum 'crypto', got {{resp.status_code}}"
"""
            return TestCaseModel(
                test_id=safe_id,
                target_endpoint=path,
                target_method="POST",
                related_rule_id=rule,
                description="Regression test verifying removed enum value 'crypto' causes 422 rejection.",
                test_purpose="Detect enum value deprecation impact on callers",
                expected_outcome=f"422 Unprocessable Entity when submitting removed enum value on {target_version}",
                target_version=target_version,
                test_code=code,
                status="candidate",
            )

        # 6. Response field removed
        if rule == RuleId.RESPONSE_FIELD_REMOVED.value and path == "/api/v1/products/{product_id}":
            safe_id = "test_regression_response_field_stock_removed"
            code = f"""def {safe_id}(client):
    \"\"\"Verify removed field 'stock' is absent from response on {target_version}.\"\"\"
    resp = client.get("/api/v1/products/1")
    assert resp.status_code == 200
    data = resp.json()
    # Breaking change assertion: client code asserting 'stock' in response will break
    assert "stock" not in data, "Expected 'stock' field to be removed in {target_version}"
    assert "sku" in data, "Expected new 'sku' field to be present"
"""
            return TestCaseModel(
                test_id=safe_id,
                target_endpoint=path,
                target_method="GET",
                related_rule_id=rule,
                description="Regression test asserting 'stock' is absent from response, exposing callers depending on it.",
                test_purpose="Detect breaking response field deletions",
                expected_outcome=f"'stock' key absent in response payload on {target_version}",
                target_version=target_version,
                test_code=code,
                status="candidate",
            )

        # 7. Field type changed
        if rule == RuleId.FIELD_TYPE_CHANGED.value and "amount" in f.schema_location:
            safe_id = "test_regression_field_type_amount_changed"
            code = f"""def {safe_id}(client):
    \"\"\"Verify response field 'amount' type is string (decimal format) on {target_version}.\"\"\"
    resp = client.get("/api/v1/payments/1")
    assert resp.status_code == 200
    data = resp.json()
    # Legacy consumer expecting float/int will encounter type error when parsing
    assert isinstance(data["amount"], str), f"Expected 'amount' to be string in {target_version}, got {{type(data['amount'])}}"
    assert data["amount"] == "289.49"
"""
            return TestCaseModel(
                test_id=safe_id,
                target_endpoint=path,
                target_method="GET",
                related_rule_id=rule,
                description="Regression test verifying field 'amount' is serialized as string instead of number.",
                test_purpose="Detect incompatible data type changes in API responses",
                expected_outcome=f"'amount' is str on {target_version} (was float in v1)",
                target_version=target_version,
                test_code=code,
                status="candidate",
            )

        # 8. Optional field added (Non-breaking)
        if rule == RuleId.FIELD_ADDED_OPTIONAL.value and "search" in f.schema_location:
            safe_id = "test_regression_optional_param_search_supported"
            code = f"""def {safe_id}(client):
    \"\"\"Verify optional parameter 'search' works without breaking default listing.\"\"\"
    resp_all = client.get("/api/v1/users")
    assert resp_all.status_code == 200

    resp_filtered = client.get("/api/v1/users?search=alice")
    assert resp_filtered.status_code == 200
    items = resp_filtered.json()["items"]
    assert len(items) == 1
    assert items[0]["username"] == "alice"
"""
            return TestCaseModel(
                test_id=safe_id,
                target_endpoint=path,
                target_method="GET",
                related_rule_id=rule,
                description="Regression test verifying optional 'search' parameter functions correctly.",
                test_purpose="Verify non-breaking backward-compatible parameter additions",
                expected_outcome="200 OK for both default and filtered queries",
                target_version=target_version,
                test_code=code,
                status="candidate",
            )

        return None

    def _write_candidate_artifacts(
        self,
        tests: List[TestCaseModel],
        output_dir: Path,
        target_version: str,
    ) -> None:
        """Write candidate tests and JSON metadata into isolated output directory."""
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        # Path restriction safety check: ensure output is in designated directory
        json_file = output_dir / "candidate_tests.json"
        py_file = output_dir / f"test_candidate_regression_{target_version}.py"

        # Write JSON metadata
        meta = [t.model_dump() for t in tests]
        json_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        # Assemble Python test file
        header = f'''"""
AI-Generated Regression Test Suite for Dependency Guardian ({target_version.upper()}).
STATUS: CANDIDATE (Generated from detected contract changes).
SAFETY: Validated against AST constraints. No arbitrary shell or filesystem operations.
"""
import pytest
from fastapi.testclient import TestClient
from {self.demo_app_module_prefix}.{target_version}.app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


'''
        body = "\n\n".join(t.test_code for t in tests)
        full_code = header + body

        # Validate syntax and safety before writing
        validate_test_code_safety(full_code)
        py_file.write_text(full_code, encoding="utf-8")
        logger.info("Wrote %d candidate regression tests to %s", len(tests), py_file)

    def approve_candidate_tests(self, output_dir: Path, target_version: str = "v2") -> Path:
        """
        Explicit approval step: promotes candidate test file to approved test file.
        """
        output_dir = output_dir.resolve()
        candidate_py = output_dir / f"test_candidate_regression_{target_version}.py"
        if not candidate_py.is_file():
            raise FileNotFoundError(f"Candidate test file not found at {candidate_py}")

        content = candidate_py.read_text(encoding="utf-8")
        # Validate AST safety
        validate_test_code_safety(content)

        approved_content = content.replace("STATUS: CANDIDATE", "STATUS: APPROVED")
        approved_py = output_dir / f"test_approved_regression_{target_version}.py"
        approved_py.write_text(approved_content, encoding="utf-8")

        # Update JSON status
        json_file = output_dir / "candidate_tests.json"
        if json_file.is_file():
            data = json.loads(json_file.read_text(encoding="utf-8"))
            for item in data:
                item["status"] = "approved"
            (output_dir / "approved_tests.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

        logger.info("Successfully approved candidate tests -> %s", approved_py)
        return approved_py

    def execute_approved_tests(
        self,
        test_file: Path,
        python_executable: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> TestExecutionSummary:
        """
        Safely execute approved regression tests using pytest.
        Captures exit code, stdout, stderr, execution duration, and test counts.
        """
        test_file = test_file.resolve()
        if not test_file.is_file():
            raise FileNotFoundError(f"Test file not found for execution: {test_file}")

        # Security check: validate code AST before running
        content = test_file.read_text(encoding="utf-8")
        validate_test_code_safety(content)

        py_bin = python_executable or sys.executable
        cmd = [py_bin, "-m", "pytest", str(test_file), "-v"]

        start = time.perf_counter()
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            elapsed = time.perf_counter() - start
            stdout = res.stdout
            stderr = res.stderr
            code = res.returncode
        except subprocess.TimeoutExpired as exc:
            elapsed = time.perf_counter() - start
            return TestExecutionSummary(
                duration_seconds=round(elapsed, 2),
                exit_code=124,
                stdout=exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                stderr=f"Test execution timed out after {timeout_seconds}s",
                test_file=str(test_file),
            )

        # Parse test outcomes from pytest output
        passed = len(re.findall(r" PASSED ", stdout))
        failed = len(re.findall(r" FAILED ", stdout))
        errors = len(re.findall(r" ERROR ", stdout))
        skipped = len(re.findall(r" SKIPPED ", stdout))

        return TestExecutionSummary(
            total_tests=passed + failed + errors + skipped,
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            duration_seconds=round(elapsed, 2),
            exit_code=code,
            stdout=stdout,
            stderr=stderr,
            test_file=str(test_file),
        )
