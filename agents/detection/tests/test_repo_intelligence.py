"""
Comprehensive test suite for Repository Intelligence and API Documentation Agent.
Asserts accurate discovery of dependencies, lockfile versions, import sites,
external integrations, AST endpoints, request/response fields, auth, error cases,
side effects, test coverage, and documentation generation.
"""
import json
from pathlib import Path
import pytest

from dependency_guardian.cli import run as run_cli
from dependency_guardian.repo_intelligence import (
    DependencyScanner,
    DocumentationGenerator,
    EndpointScanner,
    RepositoryIntelligenceScanner,
    RepositoryInventory,
    TestCoverageScanner,
)

FIXTURE_REPO = Path(__file__).parent / "fixtures" / "fixture_repo"


def test_dependency_scanner_manifests_lockfiles_and_usage():
    """Verify discovery of declared constraints, lockfile resolved versions, and usage in code."""
    scanner = DependencyScanner(FIXTURE_REPO)
    deps, internal_mods, unused_deps, integrations, skipped = scanner.scan()

    dep_map = {d.package_name.lower(): d for d in deps}

    # Pinned / resolved versions from poetry.lock
    assert "fastapi" in dep_map
    assert dep_map["fastapi"].resolved_version == "0.104.1"
    assert dep_map["fastapi"].declared_constraint == ">=0.100.0"
    assert dep_map["fastapi"].is_used is True
    assert len(dep_map["fastapi"].import_locations) > 0
    assert "https://fastapi.tiangolo.com/" in dep_map["fastapi"].official_documentation_url

    assert "pydantic" in dep_map
    assert dep_map["pydantic"].resolved_version == "2.5.2"
    assert dep_map["pydantic"].is_used is True

    assert "redis" in dep_map
    assert dep_map["redis"].resolved_version == "5.0.1"
    assert dep_map["redis"].is_used is True

    assert "stripe" in dep_map
    assert dep_map["stripe"].resolved_version == "5.4.0"
    assert dep_map["stripe"].is_used is True

    # Declared but unused package detection
    assert "unused-lib" in dep_map
    assert dep_map["unused-lib"].resolved_version == "1.2.0"
    assert dep_map["unused-lib"].is_used is False
    assert "unused-lib" in unused_deps

    # Multi-language npm package discovery
    assert "express" in dep_map
    assert dep_map["express"].ecosystem == "npm"
    assert dep_map["express"].resolved_version == "4.18.2"
    assert dep_map["express"].is_used is True

    assert "axios" in dep_map
    assert dep_map["axios"].ecosystem == "npm"
    assert dep_map["axios"].resolved_version == "1.6.2"


def test_external_integrations_and_secret_safety():
    """Verify discovery of databases, HTTP calls, brokers, and strictly sanitized secrets."""
    scanner = DependencyScanner(FIXTURE_REPO)
    _, _, _, integrations, _ = scanner.scan()

    # Outbound HTTP call to Stripe
    http_integrations = [it for it in integrations if it.integration_type == "http_service"]
    assert len(http_integrations) >= 1
    stripe_http = next((it for it in http_integrations if "stripe" in (it.target_url_or_host or "").lower()), None)
    assert stripe_http is not None
    assert "POST" in stripe_http.operations

    # Database client integration
    db_integrations = [it for it in integrations if it.integration_type in ["database", "cache"]]
    assert len(db_integrations) >= 2
    psycopg = next((it for it in db_integrations if "psycopg2" in it.service_name.lower()), None)
    assert psycopg is not None

    redis_int = next((it for it in db_integrations if "redis" in it.service_name.lower()), None)
    assert redis_int is not None

    # Secret safety assertion: raw secret keys must NEVER appear in code snippets or targets
    for it in integrations:
        assert "sk_test_51MzFakeKeyForTesting00000000" not in it.code_snippet
        assert "dummy_password" not in it.code_snippet
        if "Authorization" in it.code_snippet:
            assert "[REDACTED]" in it.code_snippet


def test_endpoint_scanner_ast_parameters_and_schemas():
    """Verify framework AST extraction of routes, params, request body, responses, and auth."""
    scanner = EndpointScanner(FIXTURE_REPO)
    endpoints, discrepancies, unsupported_fw, unresolved_routes, openapi_files = scanner.scan()

    ep_map = {(e.http_method, e.route_path): e for e in endpoints}

    # 1. GET /api/v1/users (Hybrid)
    assert ("GET", "/api/v1/users") in ep_map
    get_users = ep_map[("GET", "/api/v1/users")]
    assert get_users.discovery_method == "hybrid"
    param_names = {p.name for p in get_users.parameters}
    assert "limit" in param_names
    assert "role" in param_names

    # 2. POST /api/v1/users (Hybrid with body model, auth dependency, side effects, error cases)
    assert ("POST", "/api/v1/users") in ep_map
    post_users = ep_map[("POST", "/api/v1/users")]
    assert post_users.discovery_method == "hybrid"
    assert post_users.auth_and_authz is not None
    assert "Depends(get_current_user)" in post_users.auth_and_authz or "Security" in post_users.auth_and_authz

    # Request body schema fields
    assert post_users.request_body is not None
    rb_field_names = {f.name for f in post_users.request_body.fields}
    assert "username" in rb_field_names
    assert "email" in rb_field_names
    assert "age" in rb_field_names

    # Error cases
    assert len(post_users.error_cases) >= 1
    assert any(ec.status_code == 400 for ec in post_users.error_cases)

    # Side effects (DB write, HTTP call, queue publish)
    effect_types = {se.effect_type for se in post_users.side_effects}
    assert "database_write" in effect_types
    assert "external_http" in effect_types
    assert "message_publish" in effect_types

    # 3. GET /api/v1/users/{user_id} (AST with path param & 404 error)
    assert ("GET", "/api/v1/users/{user_id}") in ep_map
    get_user_id = ep_map[("GET", "/api/v1/users/{user_id}")]
    path_param = next((p for p in get_user_id.parameters if p.name == "user_id"), None)
    assert path_param is not None
    assert path_param.in_location == "path"
    assert any(ec.status_code == 404 for ec in get_user_id.error_cases)

    # 4. Express endpoint GET /api/v1/health
    assert ("GET", "/api/v1/health") in ep_map


def test_discrepancy_tracking_undocumented_and_ghost_endpoints():
    """Verify tracking of undocumented endpoints in code and ghost endpoints in OpenAPI."""
    scanner = EndpointScanner(FIXTURE_REPO)
    _, discrepancies, _, _, _ = scanner.scan()

    disc_types = {d.discrepancy_type: d for d in discrepancies}

    # Undocumented endpoint: POST /api/v1/orders (in code, not in OpenAPI)
    undoc = [d for d in discrepancies if d.discrepancy_type == "undocumented_endpoint"]
    assert len(undoc) >= 1
    assert any("/api/v1/orders" in d.endpoint_path for d in undoc)

    # Ghost endpoint: GET /api/v1/legacy-analytics (in OpenAPI, not in code)
    ghost = [d for d in discrepancies if d.discrepancy_type == "ghost_endpoint"]
    assert len(ghost) >= 1
    assert any("/api/v1/legacy-analytics" in d.endpoint_path for d in ghost)


def test_test_coverage_scanner_and_gaps():
    """Verify correlation of test functions with endpoints and identification of gaps."""
    ep_scanner = EndpointScanner(FIXTURE_REPO)
    endpoints, _, _, _, _ = ep_scanner.scan()

    dep_scanner = DependencyScanner(FIXTURE_REPO)
    _, _, _, integrations, _ = dep_scanner.scan()

    cov_scanner = TestCoverageScanner(FIXTURE_REPO)
    summary = cov_scanner.scan(endpoints, integrations)

    assert summary.total_endpoints == len(endpoints)
    assert summary.tested_endpoints >= 2  # /api/v1/users GET and POST have tests
    assert summary.untested_endpoints >= 2  # /api/v1/orders and /api/v1/users/{user_id} are gaps
    assert 0.0 < summary.coverage_percentage < 100.0


def test_full_repository_scan_and_documentation_generation(tmp_path):
    """Verify complete end-to-end scanner execution and generation of all 6 deliverables."""
    out_dir = tmp_path / "reports" / "repository-inventory"
    scanner = RepositoryIntelligenceScanner(repo_path=FIXTURE_REPO)
    inventory = scanner.scan(output_dir=out_dir, enrich_openapi=True)

    # Deliverables verification
    inv_file = out_dir / "repository-inventory.json"
    dep_file = out_dir / "DEPENDENCY_REPORT.md"
    api_file = out_dir / "API_REFERENCE.md"
    map_file = out_dir / "INTEGRATION_MAP.md"
    cov_file = out_dir / "TEST_COVERAGE.md"
    enriched_file = out_dir / "openapi.enriched.json"

    assert inv_file.is_file()
    assert dep_file.is_file()
    assert api_file.is_file()
    assert map_file.is_file()
    assert cov_file.is_file()
    assert enriched_file.is_file()

    # Verify repository-inventory.json structure
    data = json.loads(inv_file.read_text(encoding="utf-8"))
    assert data["metadata"]["scanner_name"] == "Dependency Guardian Repository Intelligence"
    assert len(data["dependencies"]) > 0
    assert len(data["endpoints"]) > 0
    assert len(data["discrepancies"]) > 0

    # Verify DEPENDENCY_REPORT.md contents
    dep_content = dep_file.read_text(encoding="utf-8")
    assert "## 2. External Dependencies Inventory" in dep_content
    assert "## 3. Declared but Unused Dependencies" in dep_content
    assert "## 5. External Services and Integrations" in dep_content
    assert "sk_test_51MzFakeKeyForTesting00000000" not in dep_content  # Redacted!

    # Verify API_REFERENCE.md contents
    api_content = api_file.read_text(encoding="utf-8")
    assert "POST /api/v1/users" in api_content
    assert "POST /api/v1/orders" in api_content
    assert "UserCreate" in api_content
    assert "Parameters" in api_content

    # Verify INTEGRATION_MAP.md contents
    map_content = map_file.read_text(encoding="utf-8")
    assert "flowchart TD" in map_content
    assert "End-to-End Relationship Matrix" in map_content

    # Verify TEST_COVERAGE.md contents
    cov_content = cov_file.read_text(encoding="utf-8")
    assert "Executive Coverage Metrics" in cov_content
    assert "Endpoint Test Coverage Matrix" in cov_content

    # Verify enriched OpenAPI spec
    enriched_data = json.loads(enriched_file.read_text(encoding="utf-8"))
    assert "/api/v1/orders" in enriched_data["paths"]
    assert "x-source-file" in enriched_data["paths"]["/api/v1/orders"]["post"]


def test_cli_scan_repo_command_execution(tmp_path, capsys):
    """Verify execution via CLI scan-repo command."""
    out_dir = tmp_path / "cli_reports"
    ret = run_cli([
        "scan-repo",
        str(FIXTURE_REPO),
        "--output", str(out_dir),
        "--format", "summary",
    ])
    assert ret == 0
    captured = capsys.readouterr()
    assert "REPOSITORY INTELLIGENCE & API INVENTORY SUMMARY" in captured.out
    assert "Discovered Endpoints:" in captured.out
    assert "Generated Documentation Deliverables:" in captured.out

    # JSON format output test
    ret_json = run_cli([
        "scan-repo",
        str(FIXTURE_REPO),
        "--output", str(out_dir),
        "--format", "json",
    ])
    assert ret_json == 0
    captured_json = capsys.readouterr()
    parsed = json.loads(captured_json.out)
    assert "metadata" in parsed
    assert "dependencies" in parsed


def test_cli_scan_repo_invalid_dir(capsys):
    """Verify error reporting for nonexistent repository path."""
    ret = run_cli(["scan-repo", "nonexistent_repo_dir_12345"])
    assert ret == 2
    captured = capsys.readouterr()
    assert "Repository path does not exist" in captured.err
