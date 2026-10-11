import json
from pathlib import Path
import pytest

from repair_agent.models import (
    FindingInput,
    RepairRequest,
    RepairResult,
    RepairStatus,
    ValidationStatus,
)
from repair_agent.pipeline import RepairPipeline
from repair_agent.validator import PatchValidator
from repair_agent.cli import run as cli_run


@pytest.fixture
def sample_user_service(tmp_path: Path) -> Path:
    """Fixture providing a mock service file accessing user properties."""
    code = (
        "def get_user_profile(user_data: dict) -> dict:\n"
        "    user_name = user_data['name']\n"
        "    return {'display': user_name}\n"
    )
    file_path = tmp_path / "user_service.py"
    file_path.write_text(code, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_product_service(tmp_path: Path) -> Path:
    """Fixture providing a mock service file accessing stock property."""
    code = (
        "def calculate_inventory(item: dict) -> int:\n"
        "    stock = item['stock']\n"
        "    return stock * 2\n"
    )
    file_path = tmp_path / "product_service.py"
    file_path.write_text(code, encoding="utf-8")
    return file_path


@pytest.fixture
def sample_payment_service(tmp_path: Path) -> Path:
    """Fixture providing a mock service file expecting numeric payment amounts."""
    code = (
        "def process_payment(payload: dict) -> float:\n"
        "    amount = payload['amount']\n"
        "    return amount + 1.50\n"
    )
    file_path = tmp_path / "payment_service.py"
    file_path.write_text(code, encoding="utf-8")
    return file_path


# =========================================================================
# 1. Successful Repair Proposals
# =========================================================================

def test_successful_repair_proposal_field_rename(sample_user_service: Path):
    """Verify field rename finding produces a valid adapter diff and leaves original file untouched."""
    original_content = sample_user_service.read_text(encoding="utf-8")
    original_mtime = sample_user_service.stat().st_mtime_ns

    finding = FindingInput(
        id="find_test_rename_001",
        rule_id="RULE-FIELD-RENAME-CANDIDATE",
        path="/api/v1/users/{id}",
        evidence={"renamed_from": "name", "renamed_to": "display_name"},
        message="Property 'name' was renamed to 'display_name'.",
    )

    pipeline = RepairPipeline()
    req = RepairRequest(finding=finding, target_file=str(sample_user_service))
    result = pipeline.run(req)

    # 1. Status and strategy assertions
    assert result.status == RepairStatus.VALIDATED
    assert result.finding_id == "find_test_rename_001"
    assert result.requires_human_review is True
    assert "display_name" in result.diff
    assert "user_data.get(\"display_name\", user_data.get(\"name\"))" in result.proposed_content

    # 2. Validation sandbox assertions
    assert result.validation.status == ValidationStatus.SUCCESS
    assert result.validation.ast_valid is True
    assert result.validation.syntax_error is None

    # 3. CRITICAL: Original file was never modified!
    assert sample_user_service.read_text(encoding="utf-8") == original_content
    assert sample_user_service.stat().st_mtime_ns == original_mtime


def test_successful_repair_proposal_removed_response_property(sample_product_service: Path):
    """Verify removed response field gets safe default dictionary access."""
    original_content = sample_product_service.read_text(encoding="utf-8")

    finding = FindingInput(
        id="find_test_remove_002",
        rule_id="RULE-RESPONSE-FIELD-REMOVED",
        path="/api/v1/products/{id}",
        evidence={"removed_property": "stock"},
        message="Property 'stock' was removed from response schema.",
    )

    pipeline = RepairPipeline()
    result = pipeline.run(finding=finding, target_file=str(sample_product_service))

    assert result.status == RepairStatus.VALIDATED
    assert "item.get(\"stock\", 0)" in result.proposed_content
    assert result.validation.ast_valid is True

    # Original file unmodified
    assert sample_product_service.read_text(encoding="utf-8") == original_content


def test_successful_repair_proposal_field_type_coercion(sample_payment_service: Path):
    """Verify type change from number to string introduces float coercion adapter."""
    finding = FindingInput(
        id="find_test_type_003",
        rule_id="RULE-FIELD-TYPE-CHANGED",
        path="/api/v1/payments",
        evidence={"property": "amount", "previous_type": "number", "current_type": "string"},
        previous_value="number",
        current_value="string",
        message="Property 'amount' changed from number to string.",
    )

    pipeline = RepairPipeline()
    result = pipeline.run(finding=finding, target_file=str(sample_payment_service))

    assert result.status == RepairStatus.VALIDATED
    assert "float(payload.get(\"amount\", 0))" in result.proposed_content
    assert result.validation.ast_valid is True


def test_successful_repair_with_passing_sandbox_test(tmp_path: Path):
    """Verify temporary sandbox validation executes and passes external test command."""
    service_file = tmp_path / "calc.py"
    service_file.write_text("def get_data(d): return d['name']\n", encoding="utf-8")

    test_file = tmp_path / "test_calc.py"
    test_file.write_text(
        "import calc\n"
        "def test_calc():\n"
        "    assert calc.get_data({'display_name': 'Alice'}) == 'Alice'\n",
        encoding="utf-8",
    )

    finding = FindingInput(
        id="find_test_sandbox_004",
        rule_id="RULE-FIELD-RENAME",
        path="/api/calc",
        evidence={"renamed_from": "name", "renamed_to": "display_name"},
    )

    req = RepairRequest(
        finding=finding,
        target_file=str(service_file),
        workspace_dir=str(tmp_path),
        test_command="python -m pytest test_calc.py",
    )

    pipeline = RepairPipeline()
    result = pipeline.run(req)

    assert result.status == RepairStatus.VALIDATED
    assert result.validation.test_passed is True
    assert result.validation.status == ValidationStatus.SUCCESS


# =========================================================================
# 2. Invalid Findings & Edge Cases
# =========================================================================

def test_invalid_finding_missing_required_fields():
    """Verify pipeline rejects malformed findings missing required fields."""
    pipeline = RepairPipeline()
    raw_invalid = {"id": "f1", "path": ""}  # missing rule_id and valid path

    result = pipeline.run(raw_invalid)
    assert result.status == RepairStatus.ERROR
    assert "Invalid finding" in (result.error_message or "")


def test_invalid_finding_nonexistent_target_file():
    """Verify pipeline reports error when target source file cannot be found."""
    finding = FindingInput(
        id="find_missing_file",
        rule_id="RULE-PATH-REMOVED",
        path="/api/v1/missing",
    )

    pipeline = RepairPipeline()
    result = pipeline.run(finding=finding, target_file="/nonexistent/path/service.py")

    assert result.status == RepairStatus.ERROR
    assert "Target file does not exist" in (result.error_message or "")


def test_invalid_finding_malformed_json_type():
    """Verify non-dictionary, non-model input yields an actionable error."""
    pipeline = RepairPipeline()
    result = pipeline.run(12345)  # type: ignore

    assert result.status == RepairStatus.ERROR
    assert "Unsupported input type" in (result.error_message or "")


# =========================================================================
# 3. Failed Validation Scenarios
# =========================================================================

def test_failed_validation_syntax_error(tmp_path: Path):
    """Verify validator catches syntax errors and prevents patch validation."""
    target_file = tmp_path / "broken.py"
    target_file.write_text("x = 10\n", encoding="utf-8")

    unparseable_content = "def invalid_syntax(: return 99\n"

    validator = PatchValidator()
    val_details = validator.validate(
        target_file=target_file,
        proposed_content=unparseable_content,
    )

    assert val_details.status == ValidationStatus.FAILED
    assert val_details.ast_valid is False
    assert val_details.syntax_error is not None
    assert "SyntaxError" in val_details.syntax_error

    # Ensure original file is untouched
    assert target_file.read_text(encoding="utf-8") == "x = 10\n"


def test_failed_validation_ast_safety_violation(tmp_path: Path):
    """Verify validator catches dangerous calls like eval() in proposed code."""
    target_file = tmp_path / "unsafe.py"
    target_file.write_text("x = 10\n", encoding="utf-8")

    unsafe_content = "def eval_data(user_input):\n    return eval(user_input)\n"

    validator = PatchValidator()
    val_details = validator.validate(
        target_file=target_file,
        proposed_content=unsafe_content,
    )

    assert val_details.status == ValidationStatus.FAILED
    assert val_details.ast_valid is False
    assert "forbidden builtin call 'eval'" in (val_details.syntax_error or "")


def test_failed_validation_sandbox_test_failure(tmp_path: Path):
    """Verify validator marks validation failed when sandbox tests fail."""
    service_file = tmp_path / "failing.py"
    service_file.write_text("def run(): return 1\n", encoding="utf-8")

    validator = PatchValidator()
    val_details = validator.validate(
        target_file=service_file,
        proposed_content="def run(): return 2\n",
        workspace_dir=tmp_path,
        test_command="python -c 'import failing; assert failing.run() == 999'",
    )

    assert val_details.status == ValidationStatus.FAILED
    assert val_details.test_passed is False


# =========================================================================
# 4. CLI Execution
# =========================================================================

def test_cli_execution_with_finding_file(sample_user_service: Path, tmp_path: Path):
    """Verify running the repair CLI with a finding file produces JSON output."""
    finding_data = {
        "id": "find_cli_test",
        "rule_id": "RULE-FIELD-RENAME",
        "path": "/api/users",
        "evidence": {"renamed_from": "name", "renamed_to": "display_name"},
        "message": "Field renamed",
    }
    finding_file = tmp_path / "finding.json"
    finding_file.write_text(json.dumps(finding_data), encoding="utf-8")

    out_file = tmp_path / "repair_output.json"

    exit_code = cli_run([
        "--finding", str(finding_file),
        "--file", str(sample_user_service),
        "--output", str(out_file),
        "--format", "json",
    ])

    assert exit_code == 0
    assert out_file.is_file()

    saved_data = json.loads(out_file.read_text(encoding="utf-8"))
    assert saved_data["status"] == "validated"
    assert saved_data["finding_id"] == "find_cli_test"
    assert "display_name" in saved_data["diff"]


def test_workspace_auto_discovery_of_affected_file(tmp_path: Path):
    """Verify inspector searches workspace to discover affected file when target_file is omitted."""
    src_dir = tmp_path / "src" / "services"
    src_dir.mkdir(parents=True)
    service_file = src_dir / "user_service.py"
    service_file.write_text(
        "def fetch():\n"
        "    return {'path': '/api/v1/orders', 'discount': 0}\n",
        encoding="utf-8",
    )

    finding = FindingInput(
        id="find_auto_discover",
        rule_id="RULE-FIELD-ADDED-OPTIONAL",
        path="/api/v1/orders",
        evidence={"added_property": "discount"},
    )

    pipeline = RepairPipeline()
    req = RepairRequest(
        finding=finding,
        workspace_dir=str(tmp_path),
        target_file=None,  # Not provided, should auto-discover!
    )
    result = pipeline.run(req)

    assert result.status in [RepairStatus.VALIDATED, RepairStatus.PROPOSED]
    assert result.target_file == str(service_file.resolve())


def test_ollama_fallback_to_deterministic_when_offline(sample_user_service: Path):
    """Verify requesting ollama provider falls back cleanly to deterministic engine when offline."""
    finding = FindingInput(
        id="find_ollama_fallback",
        rule_id="RULE-FIELD-RENAME",
        path="/api/users",
        evidence={"renamed_from": "name", "renamed_to": "display_name"},
    )

    # Point to nonexistent port to ensure it triggers fallback
    req = RepairRequest(
        finding=finding,
        target_file=str(sample_user_service),
        provider="ollama",
        base_url="http://127.0.0.1:59999",
    )

    pipeline = RepairPipeline()
    result = pipeline.run(req)

    assert result.status == RepairStatus.VALIDATED
    assert result.strategy == "fallback"
    assert "display_name" in result.diff
    assert result.validation.ast_valid is True


# =========================================================================
# 5. Engineering Reasoning Layer Tests
# =========================================================================

def test_convention_aware_repair(tmp_path: Path):
    """Verify reasoning layer detects and adopts nearby file conventions (.get(key, None))."""
    code = (
        "def get_account_profile(account: dict) -> dict:\n"
        "    user_id = account.get('user_id', None)\n"
        "    status = account.get('status', None)\n"
        "    name = account['name']\n"
        "    return {'user_id': user_id, 'status': status, 'name': name}\n"
    )
    service_file = tmp_path / "account_service.py"
    service_file.write_text(code, encoding="utf-8")
    original_mtime = service_file.stat().st_mtime_ns

    finding = FindingInput(
        id="find_account_rename",
        rule_id="RULE-FIELD-RENAME-CANDIDATE",
        path="/api/accounts/{id}",
        evidence={"renamed_from": "name", "renamed_to": "display_name"},
        message="Property 'name' was renamed to 'display_name'.",
    )

    pipeline = RepairPipeline()
    result = pipeline.run(finding=finding, target_file=str(service_file))

    assert result.status == RepairStatus.VALIDATED
    # Confirms adapter adopted the nearby .get(key, None) convention!
    assert "account.get(\"display_name\", account.get(\"name\", None))" in result.proposed_content
    assert result.rationale is not None
    assert len(result.assumptions) > 0
    assert result.validation.status == ValidationStatus.SUCCESS
    assert result.validation.ast_valid is True

    # Source file remains strictly untouched
    assert service_file.read_text(encoding="utf-8") == code
    assert service_file.stat().st_mtime_ns == original_mtime


def test_competing_repair_approaches_evaluation(sample_user_service: Path):
    """Verify reasoning layer compares alternative repair strategies and selects smallest maintainable fix."""
    finding = FindingInput(
        id="find_competing_approaches",
        rule_id="RULE-FIELD-RENAME-CANDIDATE",
        path="/api/v1/users/{id}",
        evidence={"renamed_from": "name", "renamed_to": "display_name"},
        message="Property 'name' was renamed to 'display_name'.",
    )

    pipeline = RepairPipeline()
    result = pipeline.run(finding=finding, target_file=str(sample_user_service))

    assert result.status == RepairStatus.VALIDATED

    # 1. Multiple plausible alternatives evaluated
    assert len(result.alternatives_considered) >= 3
    assert any("Direct" in alt for alt in result.alternatives_considered)
    assert any("Branching" in alt for alt in result.alternatives_considered)
    assert any("Chained" in alt or "Backwards-Compatible" in alt for alt in result.alternatives_considered)

    # 2. Chosen approach rationale and safety documentation
    assert result.rationale is not None
    assert "smallest maintainable fix" in result.rationale.lower()
    assert len(result.assumptions) >= 2
    assert len(result.risks) >= 1

    # 3. Validation evidence present
    assert result.validation.ast_valid is True
    assert result.validation.status == ValidationStatus.SUCCESS


def test_insufficient_evidence_semantic_uncertainty_returns_needs_review(sample_payment_service: Path):
    """Verify uncertain business logic (e.g. payment status) blocks repair and returns needs_review."""
    original_content = sample_payment_service.read_text(encoding="utf-8")

    finding = FindingInput(
        id="find_uncertain_payment",
        rule_id="RULE-SEMANTIC-UNCERTAINTY",
        path="/api/v1/payments",
        evidence={
            "semantic_uncertainty": True,
            "field": "payment_status",
            "from_value": "settled",
            "to_value": "processing_escrow",
        },
        severity="blocked",
        message="Payment state transition altered from 'settled' to 'processing_escrow'.",
    )

    pipeline = RepairPipeline()
    result = pipeline.run(finding=finding, target_file=str(sample_payment_service))

    # Never invent business logic or fallback values
    assert result.status == RepairStatus.NEEDS_REVIEW
    assert result.diff == ""
    assert result.requires_human_review is True
    assert "semantic uncertainty" in result.explanation.lower()
    assert "prohibited" in result.explanation.lower() or "blocked" in result.explanation.lower()
    assert result.rationale is not None
    assert len(result.risks) > 0
    assert result.validation.status == ValidationStatus.SKIPPED

    # Ensure source file untouched
    assert sample_payment_service.read_text(encoding="utf-8") == original_content


def test_insufficient_evidence_missing_rename_target_returns_needs_review(sample_user_service: Path):
    """Verify rename finding without target field name returns needs_review without guessing."""
    finding = FindingInput(
        id="find_missing_rename_target",
        rule_id="RULE-FIELD-RENAME-CANDIDATE",
        path="/api/v1/users/{id}",
        evidence={"renamed_from": "name"},  # missing 'renamed_to'
        message="Field was renamed but new attribute name was omitted.",
    )

    pipeline = RepairPipeline()
    result = pipeline.run(finding=finding, target_file=str(sample_user_service))

    assert result.status == RepairStatus.NEEDS_REVIEW
    assert result.diff == ""
    assert "renamed_to" in result.explanation
    assert result.requires_human_review is True


def test_insufficient_evidence_missing_type_definition_returns_needs_review(sample_payment_service: Path):
    """Verify type change finding without source/destination types returns needs_review."""
    finding = FindingInput(
        id="find_missing_type_def",
        rule_id="RULE-FIELD-TYPE-CHANGED",
        path="/api/v1/payments",
        evidence={"property": "amount"},  # missing previous_type and current_type
        message="Type change detected without type definitions.",
    )

    pipeline = RepairPipeline()
    result = pipeline.run(finding=finding, target_file=str(sample_payment_service))

    assert result.status == RepairStatus.NEEDS_REVIEW
    assert result.diff == ""
    assert "missing" in result.explanation.lower()
    assert result.requires_human_review is True


# =========================================================================
# 6. Pre-Integration Audit Tests
# =========================================================================

def test_audit_needs_review_cannot_be_mistaken_for_validated(sample_payment_service: Path):
    """Verify needs_review state produces an unambiguous non-validated result."""
    finding = FindingInput(
        id="find_audit_uncertain",
        rule_id="RULE-SEMANTIC-UNCERTAINTY",
        path="/api/v1/payments",
        evidence={"semantic_uncertainty": True, "field": "status"},
        severity="blocked",
    )
    pipeline = RepairPipeline()
    result = pipeline.run(finding=finding, target_file=str(sample_payment_service))

    # Core audit assertions: cannot be mistaken for validated
    assert result.status == RepairStatus.NEEDS_REVIEW
    assert result.is_validated is False
    assert result.proposal_generated is False
    assert result.proposed_content is None
    assert result.diff == ""
    assert result.validation.status == ValidationStatus.SKIPPED
    assert result.validation.ast_valid is False
    assert result.validation.test_executed is False
    assert result.validation.test_passed is None
    assert result.human_approved is False
    assert result.approval_status == "pending"
    assert result.requires_human_review is True


def test_audit_test_cmd_executes_strictly_against_temporary_workspace(tmp_path: Path):
    """Verify sandbox validation tests run strictly against the temporary copy and relative workspace."""
    # Build nested workspace hierarchy: <tmp_path>/src/service.py and <tmp_path>/tests/test_run.py
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    test_dir = tmp_path / "tests"
    test_dir.mkdir()

    service_file = src_dir / "service.py"
    service_file.write_text("def get_data(d): return d['name']\n", encoding="utf-8")

    # The test asserts that get_data accepts display_name (the proposed patched code)
    # AND asserts that __file__ is inside a temporary directory (not the original tmp_path!)
    test_file = test_dir / "test_run.py"
    test_file.write_text(
        "import sys\n"
        "from src import service\n"
        "def test_sandbox():\n"
        "    assert service.get_data({'display_name': 'PatchedValue'}) == 'PatchedValue'\n"
        f"    assert str(service.__file__) != '{str(service_file.resolve())}'\n",
        encoding="utf-8",
    )

    finding = FindingInput(
        id="find_audit_sandbox",
        rule_id="RULE-FIELD-RENAME-CANDIDATE",
        path="/api/data",
        evidence={"renamed_from": "name", "renamed_to": "display_name"},
    )

    req = RepairRequest(
        finding=finding,
        target_file=str(service_file),
        workspace_dir=str(tmp_path),
        test_command="python -m pytest tests/test_run.py",
    )

    pipeline = RepairPipeline()
    result = pipeline.run(req)

    assert result.status == RepairStatus.VALIDATED
    assert result.is_validated is True
    assert result.validation.test_executed is True
    assert result.validation.test_passed is True

    # Original file must remain in unpatched state
    assert service_file.read_text(encoding="utf-8") == "def get_data(d): return d['name']\n"


def test_audit_schema_distinguishes_proposal_syntax_test_and_human_approval(tmp_path: Path):
    """Verify RepairResult schema cleanly decouples proposal, AST syntax, test execution, and human approval."""
    service_file = tmp_path / "calc.py"
    service_file.write_text("def run(d): return d['amount']\n", encoding="utf-8")

    test_file = tmp_path / "test_calc.py"
    test_file.write_text("import calc\ndef test(): assert calc.run({'amount': '12.5'}) == 12.5\n", encoding="utf-8")

    finding = FindingInput(
        id="find_audit_schema",
        rule_id="RULE-FIELD-TYPE-CHANGED",
        path="/api/calc",
        evidence={"property": "amount", "previous_type": "number", "current_type": "string"},
        previous_value="number",
        current_value="string",
    )

    req = RepairRequest(
        finding=finding,
        target_file=str(service_file),
        workspace_dir=str(tmp_path),
        test_command="python -m pytest test_calc.py",
    )

    pipeline = RepairPipeline()
    result = pipeline.run(req)

    # 1. Proposal generation distinction
    assert result.proposal_generated is True
    assert result.proposed_content is not None
    assert "float(d.get(\"amount\", 0))" in result.proposed_content
    assert len(result.diff) > 0

    # 2. Syntax validation distinction
    assert result.validation.ast_valid is True
    assert result.validation.syntax_error is None

    # 3. Test results distinction
    assert result.validation.test_executed is True
    assert result.validation.test_passed is True
    assert result.validation.test_output is not None

    # 4. Human approval lifecycle distinction
    assert result.requires_human_review is True
    assert result.human_approved is False
    assert result.approval_status == "pending"

    # Overall validated helper
    assert result.is_validated is True


