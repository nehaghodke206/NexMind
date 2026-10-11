import json
import pytest
import httpx

from repair_agent.models import (
    RepairResult,
    RepairStatus,
    ValidationDetails,
    ValidationStatus,
)
from repair_agent.backend_client import (
    RepairBackendClient,
    BackendCommunicationError,
    BackendNotFoundError,
    BackendValidationError,
)


@pytest.fixture
def sample_validated_result() -> RepairResult:
    return RepairResult(
        repair_id="rep_test_001",
        finding_id="find_test_001",
        status=RepairStatus.VALIDATED,
        target_file="/path/to/user_service.py",
        proposal_generated=True,
        diff="--- a/user_service.py\n+++ b/user_service.py\n@@ -1 +1 @@\n-x\n+y\n",
        proposed_content="def get_user(): pass",
        strategy="deterministic",
        explanation="Field rename compatibility adapter added.",
        rationale="Chose chained getter to preserve backwards compatibility.",
        assumptions=["Upstream will transition from 'name' to 'display_name'."],
        risks=["Calling code must handle None."],
        alternatives_considered=["Direct key swap", "Chained get"],
        validation=ValidationDetails(
            status=ValidationStatus.SUCCESS,
            ast_valid=True,
            test_executed=True,
            test_passed=True,
            test_output="1 passed in 0.05s",
            validation_time_ms=12.5,
        ),
        requires_human_review=True,
        human_approved=False,
        approval_status="pending",
    )


@pytest.fixture
def sample_needs_review_result() -> RepairResult:
    return RepairResult(
        repair_id="rep_test_002",
        finding_id="find_uncertain_002",
        status=RepairStatus.NEEDS_REVIEW,
        target_file="/path/to/payment_service.py",
        proposal_generated=False,
        diff="",
        proposed_content=None,
        strategy="engineering_reasoning",
        explanation="Semantic uncertainty in domain logic; automated repair prohibited.",
        rationale="Blocked repair due to uncertain state machine semantics.",
        assumptions=["Alters domain logic."],
        risks=["Financial transaction corruption."],
        alternatives_considered=["Block automatic repair", "Speculative status mapping"],
        validation=ValidationDetails(
            status=ValidationStatus.SKIPPED,
            ast_valid=False,
            test_executed=False,
        ),
        requires_human_review=True,
        human_approved=False,
        approval_status="pending",
    )


# =========================================================================
# 1. Incident ID Handling Tests
# =========================================================================

def test_create_proposal_requires_non_empty_incident_id(sample_validated_result: RepairResult):
    """Verify that an explicit, non-empty incident_id is strictly required."""
    client = RepairBackendClient(base_url="http://127.0.0.1:8000/api/v1")

    for invalid_id in [None, "", "   "]:
        with pytest.raises(ValueError, match="valid, non-empty incident_id is required"):
            client.create_proposal(incident_id=invalid_id, result=sample_validated_result)  # type: ignore


def test_publish_lifecycle_requires_non_empty_incident_id(sample_validated_result: RepairResult):
    """Verify publish_repair_lifecycle refuses to invent or omit incident_id."""
    client = RepairBackendClient(base_url="http://127.0.0.1:8000/api/v1")

    with pytest.raises(ValueError, match="valid, non-empty incident_id is required"):
        client.publish_repair_lifecycle(incident_id="", result=sample_validated_result)


# =========================================================================
# 2. Payload Mapping Tests
# =========================================================================

def test_payload_mapping_deterministic_to_compatibility_adapter(sample_validated_result: RepairResult):
    """Verify Repair Agent fields map properly to the backend's RepairProposalCreate schema."""
    client = RepairBackendClient()
    payload = client.build_proposal_payload(sample_validated_result)

    # Strategy mapped to backend enum: 'compatibility_adapter'
    assert payload["strategy"] == "compatibility_adapter"
    assert payload["rationale"] == sample_validated_result.rationale
    assert payload["diff_preview"] == sample_validated_result.diff
    assert payload["patch"] == {"format": "unified_diff", "content": sample_validated_result.diff}
    assert payload["created_by"] == "repair-agent"

    # Does not fabricate confidence if not provided
    assert "confidence" not in payload

    # proposed_changes captures reasoning, telemetry, and target file
    changes = payload["proposed_changes"]
    assert changes["target_file"] == "/path/to/user_service.py"
    assert changes["engine_strategy"] == "deterministic"
    assert changes["assumptions"] == sample_validated_result.assumptions
    assert changes["risks"] == sample_validated_result.risks
    assert changes["alternatives_considered"] == sample_validated_result.alternatives_considered
    assert changes["proposed_content"] == sample_validated_result.proposed_content
    assert changes["proposal_generated"] is True


def test_payload_mapping_with_provided_confidence(sample_validated_result: RepairResult):
    """Verify explicit confidence is forwarded accurately without fabrication."""
    client = RepairBackendClient()
    payload = client.build_proposal_payload(sample_validated_result, confidence=0.92)

    assert payload["confidence"] == 0.92


def test_payload_mapping_needs_review_to_manual_review(sample_needs_review_result: RepairResult):
    """Verify unpatched/needs_review findings map strategy to 'manual_review' and avoid false diffs."""
    client = RepairBackendClient()
    payload = client.build_proposal_payload(sample_needs_review_result)

    assert payload["strategy"] == "manual_review"
    assert payload["diff_preview"] is None
    assert "patch" not in payload
    assert payload["proposed_changes"]["proposal_generated"] is False
    assert payload["proposed_changes"]["proposed_content"] is None


# =========================================================================
# 3. Validation Evidence & Human Review Invariants
# =========================================================================

def test_submit_validation_run_passed_only_when_validated(sample_validated_result: RepairResult):
    """Verify client sends status 'passed' strictly when validation succeeded."""
    recorded_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        return httpx.Response(201, json={"id": "val_run_123", "status": "passed"})

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    run_id = client.submit_validation_run(
        repair_id="rep_123",
        validation=sample_validated_result.validation,
        test_command="pytest tests/test_user.py",
    )

    assert run_id == "val_run_123"
    assert len(recorded_requests) == 1
    req_body = json.loads(recorded_requests[0].content)
    assert req_body["status"] == "passed"
    assert req_body["test_command"] == "pytest tests/test_user.py"
    assert req_body["details"]["ast_valid"] is True
    assert req_body["details"]["test_executed"] is True


def test_submit_validation_run_does_not_claim_passed_on_failure():
    """Verify validation failures post status 'failed' to the backend."""
    failed_val = ValidationDetails(
        status=ValidationStatus.FAILED,
        ast_valid=False,
        syntax_error="SyntaxError: invalid syntax",
        test_executed=False,
    )
    recorded_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        return httpx.Response(201, json={"id": "val_run_failed", "status": "failed"})

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    run_id = client.submit_validation_run(repair_id="rep_123", validation=failed_val)

    assert run_id == "val_run_failed"
    req_body = json.loads(recorded_requests[0].content)
    assert req_body["status"] == "failed"
    assert req_body["details"]["ast_valid"] is False


def test_submit_validation_run_does_not_claim_passed_on_skipped():
    """Verify skipped validation posts status 'blocked', never claiming success."""
    skipped_val = ValidationDetails(
        status=ValidationStatus.SKIPPED,
        ast_valid=False,
        test_executed=False,
    )
    recorded_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded_requests.append(request)
        return httpx.Response(201, json={"id": "val_run_blocked", "status": "blocked"})

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    run_id = client.submit_validation_run(repair_id="rep_123", validation=skipped_val)

    assert run_id == "val_run_blocked"
    req_body = json.loads(recorded_requests[0].content)
    assert req_body["status"] == "blocked"


def test_submit_validation_run_requires_repair_id():
    """Verify submit_validation_run validates presence of repair_id."""
    client = RepairBackendClient()
    with pytest.raises(ValueError, match="valid, non-empty repair_id is required"):
        client.submit_validation_run(repair_id="", validation=ValidationDetails())


def test_human_approval_is_preserved_as_pending_never_auto_approved(sample_validated_result: RepairResult):
    """Verify that publish_repair_lifecycle never auto-approves or auto-applies patches."""
    recorded_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        recorded_urls.append(str(request.url))
        if "repair-proposals" in str(request.url) and "validation-runs" not in str(request.url):
            return httpx.Response(201, json={"id": "rep_999"})
        if "validation-runs" in str(request.url):
            return httpx.Response(201, json={"id": "run_999"})
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    res = client.publish_repair_lifecycle(
        incident_id="inc_alpha",
        result=sample_validated_result,
        test_command="pytest",
    )

    # Invariant: Human approval is pending; no /approvals or /applications endpoints were invoked
    assert res["human_approval_pending"] is True
    assert not any("approvals" in url for url in recorded_urls)
    assert not any("applications" in url for url in recorded_urls)


# =========================================================================
# 4. Successful Persistence & Backend Errors
# =========================================================================

def test_publish_repair_lifecycle_success(sample_validated_result: RepairResult):
    """Verify end-to-end proposal creation and validation run synchronization."""
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/repair-proposals"):
            return httpx.Response(201, json={"id": "rep_auto_1", "status": "proposed"})
        if request.url.path.endswith("/validation-runs"):
            return httpx.Response(201, json={"id": "run_auto_1", "status": "passed"})
        return httpx.Response(404, json={"error": "not_found"})

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    result = client.publish_repair_lifecycle(
        incident_id="inc_123",
        result=sample_validated_result,
        test_command="pytest",
    )

    assert result["incident_id"] == "inc_123"
    assert result["repair_id"] == "rep_auto_1"
    assert result["validation_run_id"] == "run_auto_1"
    assert result["proposal_generated"] is True
    assert result["is_validated"] is True
    assert len(requests) == 2


def test_backend_http_404_raises_not_found(sample_validated_result: RepairResult):
    """Verify HTTP 404 from backend raises BackendNotFoundError."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not_found", "message": "Incident not found"})

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    with pytest.raises(BackendNotFoundError, match="Incident 'inc_missing' not found"):
        client.create_proposal(incident_id="inc_missing", result=sample_validated_result)


def test_backend_http_400_raises_validation_error(sample_validated_result: RepairResult):
    """Verify HTTP 400 from backend raises BackendValidationError."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad_request", "message": "Invalid strategy"})

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    with pytest.raises(BackendValidationError, match="HTTP 400"):
        client.create_proposal(incident_id="inc_bad", result=sample_validated_result)


def test_backend_incomplete_response_raises_communication_error(sample_validated_result: RepairResult):
    """Verify missing 'id' in backend JSON response raises BackendCommunicationError."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"status": "created"})  # Missing 'id'!

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    with pytest.raises(BackendCommunicationError, match="missing 'id'"):
        client.create_proposal(incident_id="inc_incomplete", result=sample_validated_result)


def test_backend_network_error_raises_communication_error(sample_validated_result: RepairResult):
    """Verify network connection errors raise BackendCommunicationError."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused by backend")

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    with pytest.raises(BackendCommunicationError, match="Network request to backend failed"):
        client.create_proposal(incident_id="inc_net_err", result=sample_validated_result)


def test_is_available_returns_true_when_healthy():
    """Verify is_available returns True on 200 health check response."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/health"):
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    assert client.is_available() is True


def test_is_available_returns_false_when_unreachable():
    """Verify is_available returns False when backend health check fails."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"status": "error"})

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    assert client.is_available() is False


# =========================================================================
# 5. Retrieval & Contract Schema Verification Tests
# =========================================================================

def test_get_proposal_success():
    """Verify get_proposal retrieves and parses a RepairProposalResponse."""
    expected_proposal = {
        "id": "rep_get_123",
        "incident_id": "inc_abc",
        "status": "proposed",
        "rationale": "Field rename compatibility adapter added.",
        "strategy": "compatibility_adapter",
        "diff_preview": "--- a/file.py\n+++ b/file.py\n",
        "proposed_changes": {"target_file": "/path/to/file.py"},
        "confidence": 0.85,
        "created_by": "repair-agent",
        "created_at": "2026-10-11T12:00:00Z",
        "updated_at": "2026-10-11T12:00:00Z",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path.endswith("/repair-proposals/rep_get_123")
        return httpx.Response(200, json=expected_proposal)

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    proposal = client.get_proposal("rep_get_123")
    assert proposal["id"] == "rep_get_123"
    assert proposal["incident_id"] == "inc_abc"
    assert proposal["strategy"] == "compatibility_adapter"


def test_get_proposal_404_raises_not_found():
    """Verify get_proposal raises BackendNotFoundError on HTTP 404."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Not found"})

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    with pytest.raises(BackendNotFoundError, match="Repair proposal 'rep_missing' not found"):
        client.get_proposal("rep_missing")


def test_get_proposal_requires_repair_id():
    """Verify get_proposal rejects empty repair_id."""
    client = RepairBackendClient()
    with pytest.raises(ValueError, match="valid, non-empty repair_id is required"):
        client.get_proposal("")


def test_list_validation_runs_success():
    """Verify list_validation_runs retrieves runs matching ValidationRunResponse schema."""
    expected_runs = [
        {
            "id": "run_001",
            "repair_id": "rep_123",
            "status": "passed",
            "test_command": "pytest",
            "output": "1 passed",
            "details": {"ast_valid": True},
            "created_at": "2026-10-11T12:01:00Z",
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path.endswith("/repair-proposals/rep_123/validation-runs")
        return httpx.Response(200, json=expected_runs)

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    runs = client.list_validation_runs("rep_123")
    assert len(runs) == 1
    assert runs[0]["id"] == "run_001"
    assert runs[0]["status"] == "passed"


def test_list_validation_runs_requires_repair_id():
    """Verify list_validation_runs rejects empty repair_id."""
    client = RepairBackendClient()
    with pytest.raises(ValueError, match="valid, non-empty repair_id is required"):
        client.list_validation_runs("  ")


def test_list_proposals_success():
    """Verify list_proposals retrieves proposals for an incident."""
    expected_proposals = [
        {
            "id": "rep_inc_1",
            "incident_id": "inc_456",
            "status": "proposed",
            "rationale": "Fix broken imports",
            "strategy": "callsite_update",
            "diff_preview": None,
            "proposed_changes": {},
            "created_at": "2026-10-11T12:00:00Z",
            "updated_at": "2026-10-11T12:00:00Z",
        }
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path.endswith("/incidents/inc_456/repair-proposals")
        return httpx.Response(200, json=expected_proposals)

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    proposals = client.list_proposals("inc_456")
    assert len(proposals) == 1
    assert proposals[0]["id"] == "rep_inc_1"
    assert proposals[0]["strategy"] == "callsite_update"


def test_backend_http_422_raises_validation_error(sample_validated_result: RepairResult):
    """Verify HTTP 422 Unprocessable Entity raises BackendValidationError."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": [{"loc": ["body", "strategy"], "msg": "value does not match pattern"}]})

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    with pytest.raises(BackendValidationError, match="HTTP 422"):
        client.create_proposal(incident_id="inc_val_err", result=sample_validated_result)


def test_submit_validation_run_http_422_raises_validation_error(sample_validated_result: RepairResult):
    """Verify HTTP 422 in submit_validation_run raises BackendValidationError."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": [{"loc": ["body", "status"], "msg": "invalid status"}]})

    transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=transport)
    client = RepairBackendClient(client=mock_http)

    with pytest.raises(BackendValidationError, match="HTTP 422"):
        client.submit_validation_run(repair_id="rep_err", validation=sample_validated_result.validation)

