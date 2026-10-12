import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest
import httpx

from repair_agent.backend_client import RepairBackendClient
from repair_agent.inspector import CodeInspector
from repair_agent.models import (
    FileChange,
    FindingInput,
    RepairRequest,
    RepairResult,
    RepairStatus,
    ValidationStatus,
)
from repair_agent.ollama_client import OllamaRepairClient
from repair_agent.patch_generator import PatchGenerator
from repair_agent.pipeline import RepairPipeline
from repair_agent.validator import PatchValidator


# =========================================================================
# 1. Inspector: Boundary Enforcement & AST Symbol Extraction
# =========================================================================

def test_inspector_enforces_workspace_boundary_path_traversal(tmp_path: Path):
    """Verify inspector strictly forbids reading files outside workspace boundary."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    secret_file = outside_dir / "secret.py"
    secret_file.write_text("API_SECRET = 'confidential'\n", encoding="utf-8")

    inspector = CodeInspector(workspace_dir=workspace)
    finding = FindingInput(
        id="find_traversal_01",
        rule_id="RULE-SECRET-LEAK",
        path="/api/secret",
    )

    with pytest.raises(PermissionError) as exc_info:
        inspector.inspect(finding, target_file=str(secret_file))

    assert "escapes workspace boundary" in str(exc_info.value)


def test_inspector_excludes_ignored_directories(tmp_path: Path):
    """Verify workspace search excludes .venv, .git, __pycache__, node_modules."""
    workspace = tmp_path / "project"
    workspace.mkdir()

    # Create ignored folders containing search term
    for ignored_name in [".venv", ".git", "__pycache__", "node_modules"]:
        ignored_folder = workspace / ignored_name
        ignored_folder.mkdir()
        (ignored_folder / "ignored_service.py").write_text(
            "def handle(): return '/api/v1/customers'\n", encoding="utf-8"
        )

    # Real source folder
    src_folder = workspace / "src"
    src_folder.mkdir()
    real_service = src_folder / "customer_service.py"
    real_service.write_text("def handle(): return '/api/v1/customers'\n", encoding="utf-8")

    finding = FindingInput(
        id="find_search_01",
        rule_id="RULE-ENDPOINT-CHANGED",
        path="/api/v1/customers",
    )

    inspector = CodeInspector(workspace_dir=workspace)
    affected_files = inspector.find_affected_files(finding)

    assert len(affected_files) == 1
    assert affected_files[0].resolve() == real_service.resolve()


def test_inspector_detects_ast_enclosing_symbol(tmp_path: Path):
    """Verify AST inspector extracts enclosing function/class names and line context."""
    service_file = tmp_path / "order_handler.py"
    code = (
        "import logging\n\n"
        "class OrderProcessor:\n"
        "    def execute(self, payload: dict):\n"
        "        order_id = payload['order_number']\n"
        "        return order_id\n"
    )
    service_file.write_text(code, encoding="utf-8")

    finding = FindingInput(
        id="find_ast_01",
        rule_id="RULE-FIELD-RENAME-CANDIDATE",
        path="/api/orders",
        evidence={"renamed_from": "order_number", "renamed_to": "id"},
    )

    inspector = CodeInspector()
    result = inspector.inspect(finding, target_file=str(service_file))

    assert result.enclosing_symbol == "execute"
    assert result.enclosing_type == "function"
    assert "OrderProcessor" in result.affected_symbols
    assert "execute" in result.affected_symbols
    assert result.line_number == 5
    assert "order_number" in result.snippet


# =========================================================================
# 2. Concrete Python Repair Patterns
# =========================================================================

def test_pagination_schema_adapter_pattern(tmp_path: Path):
    """Verify deterministic pagination adapter transforms items access to data fallback."""
    service_file = tmp_path / "feed.py"
    service_file.write_text(
        "def parse_feed(response: dict) -> list:\n"
        "    return response['items']\n",
        encoding="utf-8",
    )

    finding = FindingInput(
        id="find_pagination_01",
        rule_id="RULE-PAGINATION-CHANGED",
        path="/api/v1/feed",
        evidence={"removed_property": "items", "renamed_to": "data"},
        message="Pagination response field 'items' renamed to 'data'.",
    )

    pipeline = RepairPipeline()
    result = pipeline.run(finding=finding, target_file=str(service_file))

    assert result.status == RepairStatus.VALIDATED
    assert "response.get(\"data\", response.get(\"items\", []))" in result.proposed_content
    assert result.validation.ast_valid is True
    assert result.proposal_generated is True


def test_no_todo_injected_when_no_pattern_matches(tmp_path: Path):
    """Verify pipeline rejects or requests review without ever injecting fake TODO comments."""
    service_file = tmp_path / "unrelated.py"
    original_code = "def complex_computation(x, y):\n    return x ** 2 + y ** 2\n"
    service_file.write_text(original_code, encoding="utf-8")

    finding = FindingInput(
        id="find_unmatched_01",
        rule_id="RULE-UNKNOWN-SECURITY-POLICY",
        path="/api/custom",
        evidence={},
        message="Upstream changed TLS cipher policy.",
    )

    pipeline = RepairPipeline()
    result = pipeline.run(finding=finding, target_file=str(service_file))

    # Must NOT inject TODO comment into source
    assert result.proposal_generated is False
    assert result.diff == ""
    assert "TODO" not in (result.proposed_content or "")
    assert service_file.read_text(encoding="utf-8") == original_code


# =========================================================================
# 3. Structured AI Generation & Safe Fallbacks
# =========================================================================

def test_ollama_client_rejects_syntactically_invalid_candidate(monkeypatch):
    """Verify OllamaRepairClient runs ast.parse and discards candidate with SyntaxError."""
    client = OllamaRepairClient(base_url="http://mock-ollama:11434")

    # Mock is_available to True
    monkeypatch.setattr(client, "is_available", lambda: True)

    # Mock httpx response with broken Python syntax
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {"content": "```python\ndef broken_func(:\n    return None\n```"}
    }

    mock_http_client = MagicMock()
    mock_http_client.__enter__.return_value.post.return_value = mock_resp
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: mock_http_client)

    finding_dict = {"rule_id": "RULE-TEST", "path": "/test", "message": "test", "evidence": {}}
    result = client.generate_repair(finding_dict, "def broken_func(): pass\n")

    # Broken AST must be rejected cleanly
    assert result is None


def test_ollama_client_rejects_unchanged_code(monkeypatch):
    """Verify OllamaRepairClient rejects output identical to original code."""
    client = OllamaRepairClient(base_url="http://mock-ollama:11434")
    monkeypatch.setattr(client, "is_available", lambda: True)

    original = "def unchanged(): return 1\n"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {"content": f"```python\n{original}\n```"}
    }

    mock_http_client = MagicMock()
    mock_http_client.__enter__.return_value.post.return_value = mock_resp
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: mock_http_client)

    finding_dict = {"rule_id": "RULE-TEST", "path": "/test", "message": "test", "evidence": {}}
    result = client.generate_repair(finding_dict, original)

    assert result is None


def test_ollama_client_handles_timeout_gracefully(monkeypatch):
    """Verify OllamaRepairClient catches timeout without crashing and returns None."""
    client = OllamaRepairClient(base_url="http://mock-ollama:11434")
    monkeypatch.setattr(client, "is_available", lambda: True)

    mock_http_client = MagicMock()
    mock_http_client.__enter__.return_value.post.side_effect = httpx.TimeoutException("Read timed out")
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: mock_http_client)

    finding_dict = {"rule_id": "RULE-TEST", "path": "/test", "message": "test", "evidence": {}}
    result = client.generate_repair(finding_dict, "def func(): pass\n")

    assert result is None


# =========================================================================
# 4. Meaningful Validation & Sandbox Isolation
# =========================================================================

def test_validator_evaluates_all_file_changes_and_fails_on_syntax_error(tmp_path: Path):
    """Verify validator checks AST across all changed files and flags failing file."""
    validator = PatchValidator()
    primary = tmp_path / "valid.py"
    primary.write_text("def ok(): return 1\n", encoding="utf-8")

    file_changes = [
        FileChange(
            file_path=str(primary),
            proposed_content="def ok(): return 2\n",
            ast_valid=True,
        ),
        FileChange(
            file_path=str(tmp_path / "broken.py"),
            proposed_content="def invalid_syntax(:\n",
            ast_valid=False,
        ),
    ]

    val_res = validator.validate(
        target_file=primary,
        proposed_content="def ok(): return 2\n",
        workspace_dir=tmp_path,
        file_changes=file_changes,
    )

    assert val_res.status == ValidationStatus.FAILED
    assert val_res.ast_valid is False
    assert "broken.py" in (val_res.syntax_error or "")


def test_validator_rejects_sandbox_path_traversal(tmp_path: Path):
    """Verify validator rejects attempt to write outside sandbox."""
    validator = PatchValidator()
    primary = tmp_path / "valid.py"
    primary.write_text("def ok(): return 1\n", encoding="utf-8")

    malicious_change = [
        FileChange(
            file_path="../../malicious.py",
            proposed_content="def evil(): pass\n",
        )
    ]

    val_res = validator.validate(
        target_file=primary,
        proposed_content="def ok(): return 1\n",
        workspace_dir=tmp_path,
        file_changes=malicious_change,
    )

    assert val_res.status == ValidationStatus.FAILED
    assert "path traversal" in (val_res.syntax_error or "").lower()


# =========================================================================
# 5. Multi-File Tracking & Backend Integration Mapping
# =========================================================================

def test_multi_file_tracking_in_repair_result_and_backend_payload(tmp_path: Path):
    """Verify multi-file changes and root-cause metadata propagate to backend payload."""
    fc1 = FileChange(
        file_path="src/client.py",
        diff="--- a/src/client.py\n+++ b/src/client.py\n@@ -1 +1 @@\n-old\n+new",
        proposed_content="new client\n",
        ast_valid=True,
    )
    fc2 = FileChange(
        file_path="src/service.py",
        diff="--- a/src/service.py\n+++ b/src/service.py\n@@ -1 +1 @@\n-old\n+new",
        proposed_content="new service\n",
        ast_valid=True,
    )

    repair_result = RepairResult(
        finding_id="find_multi_01",
        status=RepairStatus.VALIDATED,
        target_file="src/client.py",
        likely_root_cause="RULE-FIELD-RENAME-CANDIDATE",
        affected_symbols=["fetch_records", "RecordsClient"],
        file_changes=[fc1, fc2],
        proposal_generated=True,
        diff=fc1.diff + "\n" + fc2.diff,
        strategy="deterministic",
        explanation="Multi-file backward compatibility adapter.",
    )

    backend_client = RepairBackendClient(base_url="http://localhost:8000/api/v1")
    payload = backend_client.build_proposal_payload(repair_result)

    # Backend payload schema check
    assert payload["strategy"] == "compatibility_adapter"
    assert "diff_preview" in payload
    proposed = payload["proposed_changes"]
    assert proposed["likely_root_cause"] == "RULE-FIELD-RENAME-CANDIDATE"
    assert "fetch_records" in proposed["affected_symbols"]
    assert len(proposed["file_changes"]) == 2
    assert proposed["file_changes"][0]["file_path"] == "src/client.py"
    assert proposed["file_changes"][1]["file_path"] == "src/service.py"
