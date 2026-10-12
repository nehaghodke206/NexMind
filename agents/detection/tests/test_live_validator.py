import asyncio
import json
from pathlib import Path
from unittest.mock import patch
import httpx
import pytest

from dependency_guardian.api_intelligence.models import (
    LiveProbeEndpoint,
    LiveProbeResult,
    LiveValidationOptions,
    LiveValidationReport,
    ProbeStatus,
)
from dependency_guardian.api_intelligence.validator import (
    LiveApiValidator,
    extract_structural_schema,
    sanitize_headers,
    sanitize_url,
)
from dependency_guardian.cli import run
from dependency_guardian.contracts.findings import DetectionProvenance


def test_is_method_safe():
    validator = LiveApiValidator()
    assert validator.is_method_safe("GET") is True
    assert validator.is_method_safe("HEAD") is True
    assert validator.is_method_safe("OPTIONS") is True
    assert validator.is_method_safe("get") is True

    # Mutating / dangerous methods must be rejected
    assert validator.is_method_safe("POST") is False
    assert validator.is_method_safe("PUT") is False
    assert validator.is_method_safe("DELETE") is False
    assert validator.is_method_safe("PATCH") is False
    assert validator.is_method_safe("CONNECT") is False


def test_is_host_allowed():
    validator = LiveApiValidator()
    allowed, _ = validator.is_host_allowed("http://localhost:8000/api")
    assert allowed is True

    allowed, _ = validator.is_host_allowed("http://127.0.0.1:8000/api")
    assert allowed is True

    # Cloud metadata endpoints must be blocked
    allowed, reason = validator.is_host_allowed("http://169.254.169.254/latest/meta-data")
    assert allowed is False
    assert "explicitly blocked" in (reason or "")

    allowed, reason = validator.is_host_allowed("http://metadata.google.internal/computeMetadata/v1")
    assert allowed is False


def test_sanitize_url():
    raw_url = "https://api.example.com/v1/users?token=secret123&api_key=xyz987&page=2"
    sanitized = sanitize_url(raw_url)
    assert "token=%5BREDACTED%5D" in sanitized or "token=[REDACTED]" in sanitized
    assert "api_key=%5BREDACTED%5D" in sanitized or "api_key=[REDACTED]" in sanitized
    assert "page=2" in sanitized


def test_sanitize_headers():
    raw_headers = {
        "Authorization": "Bearer super-secret-jwt",
        "X-API-Key": "my-secret-key",
        "Cookie": "session=abc",
        "Accept": "application/json",
    }
    sanitized = sanitize_headers(raw_headers)
    assert sanitized["Authorization"] == "[REDACTED]"
    assert sanitized["X-API-Key"] == "[REDACTED]"
    assert sanitized["Cookie"] == "[REDACTED]"
    assert sanitized["Accept"] == "application/json"


def test_security_blocked_on_mutating_method():
    endpoint = LiveProbeEndpoint(
        id="ep_order",
        service_name="OrderService",
        base_url="http://127.0.0.1:8000",
        path="/orders",
        method="POST",
    )
    validator = LiveApiValidator(options=LiveValidationOptions(mode="algorithmic"))
    report = asyncio.run(validator.validate_endpoints([endpoint]))

    assert report.total_probes == 1
    assert report.security_blocked_count == 1
    assert report.results[0].status == ProbeStatus.SECURITY_BLOCKED
    assert "Mutating HTTP method 'POST' rejected" in (report.results[0].error_message or "")


def test_security_blocked_on_cloud_metadata():
    endpoint = LiveProbeEndpoint(
        id="ep_meta",
        service_name="MetadataService",
        base_url="http://169.254.169.254",
        path="/latest/meta-data",
        method="GET",
    )
    validator = LiveApiValidator(options=LiveValidationOptions(mode="algorithmic"))
    report = asyncio.run(validator.validate_endpoints([endpoint]))

    assert report.total_probes == 1
    assert report.security_blocked_count == 1
    assert report.results[0].status == ProbeStatus.SECURITY_BLOCKED
    assert "explicitly blocked" in (report.results[0].error_message or "")


def test_schema_fingerprint_extraction():
    data = {
        "user_id": 42,
        "username": "tester",
        "roles": ["admin", "viewer"],
        "profile": {"avatar": "url", "active": True},
    }
    fingerprint = extract_structural_schema(data)
    assert fingerprint["user_id"] == "integer"
    assert fingerprint["username"] == "string"
    assert fingerprint["roles"] == ["string"]
    assert fingerprint["profile"]["avatar"] == "string"
    assert fingerprint["profile"]["active"] == "boolean"


def test_successful_probe_and_report_generation():
    endpoint = LiveProbeEndpoint(
        id="ep_users",
        service_name="UserService",
        base_url="http://127.0.0.1:8000",
        path="/api/users",
        method="GET",
        expected_status_code=200,
    )
    validator = LiveApiValidator(options=LiveValidationOptions(mode="algorithmic"))

    mock_resp = httpx.Response(
        status_code=200,
        headers={"Content-Type": "application/json"},
        json={"status": "healthy", "count": 5},
        request=httpx.Request("GET", "http://127.0.0.1:8000/api/users"),
    )

    with patch.object(httpx.AsyncClient, "request", return_value=mock_resp):
        report = asyncio.run(validator.validate_endpoints([endpoint]))

    assert report.total_probes == 1
    assert report.reachable_count == 1
    assert report.results[0].status == ProbeStatus.REACHABLE
    assert report.results[0].status_code == 200
    assert report.results[0].structural_schema == {"status": "string", "count": "integer"}
    assert len(report.findings) == 0


def test_contract_mismatch_findings_and_provenance():
    endpoint = LiveProbeEndpoint(
        id="ep_users_mismatch",
        service_name="UserService",
        base_url="http://127.0.0.1:8000",
        path="/api/users",
        method="GET",
        expected_status_code=200,
        expected_fields=["users"],
    )
    validator = LiveApiValidator(options=LiveValidationOptions(mode="algorithmic"))

    # Missing expected field 'users'
    mock_resp = httpx.Response(
        status_code=200,
        headers={"Content-Type": "application/json"},
        json={"status": "healthy", "count": 5},
        request=httpx.Request("GET", "http://127.0.0.1:8000/api/users"),
    )

    with patch.object(httpx.AsyncClient, "request", return_value=mock_resp):
        report = asyncio.run(validator.validate_endpoints([endpoint]))

    assert report.total_probes == 1
    assert report.contract_mismatch_count == 1
    assert len(report.findings) >= 1
    finding = report.findings[0]
    assert finding.provenance == DetectionProvenance.LIVE_PROBE
    assert finding.rule_id == "RULE-API-FIELD-REMOVED"
    assert "users" in finding.message


def test_cli_validate_api_help(capsys):
    with pytest.raises(SystemExit) as exc:
        run(["validate-api", "--help"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "validate-api" in captured.out
    assert "--mode" in captured.out
    assert "--concurrency" in captured.out


def test_cli_validate_api_single_url_security_block(capsys):
    ret = run([
        "validate-api",
        "--url", "http://127.0.0.1:8000/mutate",
        "--method", "POST",
        "--format", "json",
    ])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_probes"] == 1
    assert data["results"][0]["status"] == "security_blocked"
    assert len(data["findings"]) == 1
    assert data["findings"][0]["provenance"] == "live_probe"


def test_cli_validate_api_config_file(capsys):
    config_path = str(Path(__file__).resolve().parents[3] / "dependency-guardian.yml")
    ret = run([
        "validate-api",
        config_path,
        "--mode", "algorithmic",
        "--format", "json",
    ])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total_probes"] >= 1
    assert data["mode"] == "algorithmic"
    assert data["ai_status"] == "skipped"
