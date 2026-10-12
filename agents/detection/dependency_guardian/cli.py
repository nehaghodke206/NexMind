import argparse
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
import yaml

from .config import AIFallbackPolicy, DetectionConfig, load_configuration
from .contracts.findings import (
    CompatibilityClassification,
    DetectionMode,
    Finding,
    SeverityLevel,
)
from .contracts.models import DetectionRequest, DetectionResult, DiffSummary
from .orchestrator import DetectionOrchestrator
from .client.backend import BackendClient
from .insights import format_insights_text
from .test_generator import RegressionTestGenerator, TestCaseModel, TestExecutionSummary
from .repo_intelligence import (
    DocumentationGenerator,
    RepositoryIntelligenceScanner,
    RepositoryInventory,
)
import asyncio
from .api_intelligence import (
    LiveApiValidator,
    LiveProbeEndpoint,
    LiveValidationOptions,
    LiveValidationReport,
    ProbeStatus,
)

logger = logging.getLogger("dependency_guardian.cli")


def _load_spec_file(path_str: str) -> Dict[str, Any]:
    """Load and parse an OpenAPI specification from JSON or YAML file."""
    path = Path(path_str)
    if not path.is_file():
        raise FileNotFoundError(f"Specification file not found: {path_str}")
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        return {}
    try:
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError(f"Specification in {path_str} did not parse into an object dictionary.")
        return data
    except Exception as exc:
        raise ValueError(f"Failed to parse specification file '{path_str}': {exc}") from exc


def _format_summary_table(result: DetectionResult) -> str:
    """Format detection outcome into a human-readable text table."""
    lines = [
        "=" * 72,
        f" Dependency Guardian Detection Summary",
        f" Mode: {result.mode.value.upper()} | Execution Time: {result.execution_time_ms:.1f}ms",
        "=" * 72,
        f" Total Findings: {result.summary.total_findings}",
        f"   - Breaking:             {result.summary.breaking_count}",
        f"   - Potentially Breaking: {result.summary.potentially_breaking_count}",
        f"   - Non-Breaking:         {result.summary.non_breaking_count}",
        f"   - Unknown:              {result.summary.unknown_count}",
        "-" * 72,
        f" Severity Breakdown: Critical={result.summary.by_severity.get('critical', 0)}, "
        f"High={result.summary.by_severity.get('high', 0)}, "
        f"Medium={result.summary.by_severity.get('medium', 0)}, "
        f"Low={result.summary.by_severity.get('low', 0)}",
    ]

    if result.ai_status and result.ai_status != "skipped":
        lines.append(f" AI Provider: {result.ai_provider or 'none'} | AI Model: {result.ai_model or 'none'}")
        lines.append(f" AI Status: {result.ai_status}" + (f" (Error: {result.ai_error})" if result.ai_error else ""))

    if result.findings:
        lines.append("-" * 72)
        lines.append(f" {'RULE ID':<28} {'METHOD':<8} {'COMPATIBILITY':<16} {'PATH'}")
        lines.append("-" * 72)
        for f in result.findings:
            m = f.method or "*"
            lines.append(f" {f.rule_id:<28} {m:<8} {f.compatibility.value:<16} {f.path}")
            lines.append(f"   Message: {f.message}")
            if f.ai_reasoning:
                lines.append(f"   AI Reasoning: {f.ai_reasoning}")
    lines.append("=" * 72)
    return "\n".join(lines)


def _preview_candidate_tests(tests: List[TestCaseModel]) -> None:
    """Print dry-run candidate test previews to stdout."""
    print("=" * 72)
    print(" DEPENDENCY GUARDIAN — CANDIDATE REGRESSION TESTS PREVIEW (DRY-RUN)")
    print(f" Total Candidate Tests: {len(tests)}")
    print("=" * 72)
    for idx, t in enumerate(tests, 1):
        print(f"\n--- [Test #{idx}] {t.test_id} ---")
        print(f" Target Endpoint: {t.target_method} {t.target_endpoint}")
        print(f" Related Rule ID: {t.related_rule_id}")
        print(f" Purpose:         {t.test_purpose}")
        print(f" Expected:        {t.expected_outcome}")
        print(f" Code Preview:\n{t.test_code.strip()}")
    print("=" * 72)


def _print_test_summary(summary: TestExecutionSummary) -> None:
    """Print regression test execution results to stdout."""
    print("=" * 72)
    print(" DEPENDENCY GUARDIAN — REGRESSION TEST EXECUTION SUMMARY")
    print("=" * 72)
    print(f" Test File:       {summary.test_file}")
    print(f" Target Version:  {summary.target_version}")
    print(f" Duration:        {summary.duration_seconds}s")
    print(f" Total Tests:     {summary.total_tests}")
    print(f" Passed:          {summary.passed}")
    print(f" Failed:          {summary.failed}")
    print(f" Errors:          {summary.errors}")
    print(f" Exit Code:       {summary.exit_code}")
    print("-" * 72)
    if summary.exit_code == 0:
        print(" [+] All regression tests executed and verified successfully.")
    else:
        print(f" [!] Test execution reported failures/errors (exit {summary.exit_code}).")
        if summary.stderr:
            print(f" Stderr: {summary.stderr[:300]}")
    print("=" * 72)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dependency-guardian",
        description="Dependency Guardian Detection Agent CLI for OpenAPI specifications",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
        help="Show program version number and exit",
    )
    parser.add_argument(
        "baseline_pos",
        nargs="?",
        default=None,
        help="Path to baseline OpenAPI specification file (JSON or YAML)",
    )
    parser.add_argument(
        "current_pos",
        nargs="?",
        default=None,
        help="Path to current OpenAPI specification file (JSON or YAML)",
    )
    parser.add_argument(
        "--baseline",
        "-b",
        dest="baseline_opt",
        default=None,
        help="Path to baseline OpenAPI specification file (JSON or YAML)",
    )
    parser.add_argument(
        "--current",
        "-c",
        dest="current_opt",
        default=None,
        help="Path to current OpenAPI specification file (JSON or YAML)",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["algorithmic", "ai", "hybrid"],
        default=None,
        help="Detection mode: algorithmic (default offline), ai, or hybrid",
    )
    parser.add_argument(
        "--provider",
        dest="ai_provider",
        choices=["mock", "ollama", "hosted"],
        default=None,
        help="AI provider identifier",
    )
    parser.add_argument(
        "--model",
        dest="ai_model",
        default=None,
        help="Target model identifier for AI provider",
    )
    parser.add_argument(
        "--base-url",
        dest="ai_base_url",
        default=None,
        help="Custom base URL for AI provider endpoint",
    )
    parser.add_argument(
        "--api-key",
        dest="ai_api_key",
        default=None,
        help="API key for hosted AI provider",
    )
    parser.add_argument(
        "--timeout",
        dest="ai_timeout_seconds",
        type=float,
        default=None,
        help="AI request timeout in seconds",
    )
    parser.add_argument(
        "--fallback-policy",
        dest="ai_fallback_policy",
        choices=["fail", "fallback_to_algorithmic", "none"],
        default=None,
        help="Behavior when AI fails: fail or fallback_to_algorithmic",
    )
    parser.add_argument(
        "--backend-url",
        dest="backend_base_url",
        default=None,
        help="Dependency Guardian backend API URL",
    )
    parser.add_argument(
        "--project-id",
        default=None,
        help="Project identifier for backend synchronization",
    )
    parser.add_argument(
        "--dependency-id",
        default=None,
        help="Dependency identifier for backend synchronization",
    )
    parser.add_argument(
        "--sync-backend",
        action="store_true",
        help="Submit observations and incidents to the backend service",
    )
    parser.add_argument(
        "--propose-repairs",
        action="store_true",
        help="Trigger Repair Agent for detected breaking changes and synchronize proposals to backend",
    )
    parser.add_argument(
        "--test-cmd",
        default=None,
        help="Optional test command to run in sandbox validation for proposed repairs",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output path for detection result JSON",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "summary", "both"],
        default="json",
        help="Output display format (default: json)",
    )
    parser.add_argument(
        "--fail-on-breaking",
        action="store_true",
        help="Exit with non-zero status code (1) if breaking changes are detected",
    )
    parser.add_argument(
        "--workspace-dir",
        "-w",
        default=None,
        help="Directory to resolve workspace-level configuration (.dependency-guardian.json)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging output",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress stderr informational messages",
    )
    parser.add_argument(
        "--check-ai",
        action="store_true",
        help="Run diagnostic connectivity and model check for configured AI provider",
    )
    parser.add_argument(
        "--generate-tests",
        nargs="?",
        const="demo/sample-api/generated-tests",
        default=None,
        metavar="DIR",
        help="Generate candidate regression tests into target directory (default: demo/sample-api/generated-tests)",
    )
    parser.add_argument(
        "--test-target",
        choices=["v1", "v2"],
        default="v2",
        help="Target API version to generate/run regression tests against (default: v2)",
    )
    parser.add_argument(
        "--preview-tests",
        action="store_true",
        help="Preview candidate regression tests in stdout without writing files (dry run)",
    )
    parser.add_argument(
        "--approve-tests",
        nargs="?",
        const="demo/sample-api/generated-tests",
        default=None,
        metavar="DIR",
        help="Approve candidate regression tests in target directory for execution",
    )
    parser.add_argument(
        "--execute-tests",
        nargs="?",
        const="demo/sample-api/generated-tests",
        default=None,
        metavar="DIR",
        help="Execute approved regression tests and display test run summary",
    )
    parser.add_argument(
        "--insights-output",
        default=None,
        metavar="FILE",
        help="Output file path to save AI risk insights report (.txt or .json)",
    )
    return parser


def build_scan_repo_parser() -> argparse.ArgumentParser:
    """Build argument parser for repository intelligence scanning."""
    parser = argparse.ArgumentParser(
        prog="dependency-guardian scan-repo",
        description="Dependency Guardian Repository Intelligence & API Documentation Agent",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
        help="Show program version number and exit",
    )
    parser.add_argument(
        "repository_path",
        help="Path to repository directory to scan",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="reports/repository-inventory",
        help="Output directory or file path for inventory and documentation (default: reports/repository-inventory)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["summary", "json", "both"],
        default="summary",
        help="Console output format: summary (default), json, or both",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["algorithmic", "ai", "hybrid"],
        default="algorithmic",
        help="Scanning mode: algorithmic (default offline AST/manifest), ai, or hybrid",
    )
    parser.add_argument(
        "--provider",
        dest="ai_provider",
        choices=["mock", "ollama", "hosted"],
        default=None,
        help="AI provider identifier for hybrid/ai explanation",
    )
    parser.add_argument(
        "--model",
        dest="ai_model",
        default=None,
        help="Target model identifier for AI provider",
    )
    parser.add_argument(
        "--base-url",
        dest="ai_base_url",
        default=None,
        help="Custom base URL for AI provider endpoint",
    )
    parser.add_argument(
        "--api-key",
        dest="ai_api_key",
        default=None,
        help="API key for hosted AI provider",
    )
    parser.add_argument(
        "--timeout",
        dest="ai_timeout_seconds",
        type=float,
        default=None,
        help="AI request timeout in seconds",
    )
    parser.add_argument(
        "--no-enrichment",
        dest="enrich_openapi",
        action="store_false",
        default=True,
        help="Disable OpenAPI specification enrichment",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging output",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress informational console output",
    )
    return parser


def _format_scan_repo_summary(inventory: RepositoryInventory, written_files: Dict[str, Path]) -> str:
    """Format repository inventory summary table for terminal display."""
    meta = inventory.metadata
    cov = inventory.test_coverage
    deps = inventory.dependencies
    used_deps = sum(1 for d in deps if d.is_used)

    lines = [
        "=" * 76,
        " DEPENDENCY GUARDIAN — REPOSITORY INTELLIGENCE & API INVENTORY SUMMARY",
        "=" * 76,
        f" Repository Path:       {meta.scanned_path}",
        f" Languages Detected:   {', '.join(meta.languages_detected) if meta.languages_detected else 'None'}",
        f" Frameworks Detected:  {', '.join(meta.frameworks_detected) if meta.frameworks_detected else 'None'}",
        f" Source Files Scanned: {meta.total_files_scanned}",
        "-" * 76,
        f" Dependencies:         {len(deps)} total ({used_deps} used in code, {len(inventory.unused_dependencies)} declared but unused)",
        f" External Integrations: {len(inventory.integrations)} (Databases, Queues, HTTP calls, Cloud SDKs)",
        f" Discovered Endpoints: {len(inventory.endpoints)}",
        f"   - Framework AST:     {sum(1 for e in inventory.endpoints if e.discovery_method == 'framework_ast')}",
        f"   - OpenAPI Spec:      {sum(1 for e in inventory.endpoints if e.discovery_method == 'openapi_spec')}",
        f"   - Hybrid (Both):     {sum(1 for e in inventory.endpoints if e.discovery_method == 'hybrid')}",
        f" Spec Discrepancies:   {len(inventory.discrepancies)} ({sum(1 for d in inventory.discrepancies if d.discrepancy_type == 'undocumented_endpoint')} undocumented, {sum(1 for d in inventory.discrepancies if d.discrepancy_type == 'ghost_endpoint')} ghost)",
        f" API Test Coverage:    {cov.coverage_percentage}% ({cov.tested_endpoints}/{cov.total_endpoints} endpoints tested, {cov.untested_endpoints} gaps)",
        "-" * 76,
        " Generated Documentation Deliverables:",
    ]
    for key, path in written_files.items():
        lines.append(f"   [+] {path.name:<25} -> {path}")
    lines.append("=" * 76)
    return "\n".join(lines)


def run_scan_repo(scan_args: List[str]) -> int:
    """Execute repository intelligence scanning and documentation generation."""
    parser = build_scan_repo_parser()
    args = parser.parse_args(scan_args)

    log_level = logging.DEBUG if args.verbose else (logging.ERROR if args.quiet else logging.INFO)
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    repo_path = Path(args.repository_path)
    if not repo_path.exists() or not repo_path.is_dir():
        sys.stderr.write(f"Error: Repository path does not exist or is not a directory: {args.repository_path}\n")
        return 2

    # Determine output directory
    raw_output = Path(args.output)
    if raw_output.suffix.lower() == ".json":
        output_dir = raw_output.parent
    else:
        output_dir = raw_output

    # Optional AI provider setup if mode is ai or hybrid
    ai_provider = None
    if args.mode in ["ai", "hybrid"] and args.ai_provider:
        cli_overrides: Dict[str, Any] = {
            "ai_provider": args.ai_provider,
        }
        if args.ai_model:
            cli_overrides["ai_model"] = args.ai_model
        if args.ai_base_url:
            cli_overrides["ai_base_url"] = args.ai_base_url
        if args.ai_api_key:
            cli_overrides["ai_api_key"] = args.ai_api_key
        if args.ai_timeout_seconds is not None:
            cli_overrides["ai_timeout_seconds"] = args.ai_timeout_seconds

        try:
            config = load_configuration(workspace_dir=repo_path, cli_overrides=cli_overrides)
            orchestrator = DetectionOrchestrator(config=config)
            ai_provider = orchestrator.ai_provider
        except Exception as exc:
            logger.warning(f"Failed to initialize AI provider '{args.ai_provider}': {exc}. Proceeding with deterministic scan.")

    def on_progress(event: Dict[str, Any]) -> None:
        progress_payload = {
            "type": "progress",
            "phase": event.get("phase", "scanning"),
            "message": event.get("message", ""),
            "files_discovered": event.get("files_discovered"),
            "files_processed": event.get("files_processed"),
            "total_files": event.get("total_files"),
            "current_file": event.get("current_file"),
            "dependencies_count": event.get("dependencies_count"),
            "integrations_count": event.get("integrations_count"),
            "endpoints_count": event.get("endpoints_count"),
            "discrepancies_count": event.get("discrepancies_count"),
            "coverage_percentage": event.get("coverage_percentage"),
        }
        cleaned = {k: v for k, v in progress_payload.items() if v is not None}
        sys.stderr.write(json.dumps(cleaned) + "\n")
        sys.stderr.flush()

    try:
        scanner = RepositoryIntelligenceScanner(
            repo_path=repo_path,
            ai_provider=ai_provider,
            on_progress=on_progress,
        )
        inventory = scanner.scan(output_dir=output_dir, enrich_openapi=args.enrich_openapi)
    except Exception as exc:
        sys.stderr.write(f"Repository scanning failed: {exc}\n")
        return 1

    written_files = {
        "repository-inventory.json": output_dir / "repository-inventory.json",
        "DEPENDENCY_REPORT.md": output_dir / "DEPENDENCY_REPORT.md",
        "API_REFERENCE.md": output_dir / "API_REFERENCE.md",
        "INTEGRATION_MAP.md": output_dir / "INTEGRATION_MAP.md",
        "TEST_COVERAGE.md": output_dir / "TEST_COVERAGE.md",
        "openapi.enriched.json": output_dir / "openapi.enriched.json",
    }

    if args.format == "json":
        inv_dict = inventory.model_dump(mode="json")
        print(json.dumps(inv_dict, indent=2))
    elif args.format == "summary":
        if not args.quiet:
            print(_format_scan_repo_summary(inventory, written_files))
    elif args.format == "both":
        if not args.quiet:
            print(_format_scan_repo_summary(inventory, written_files))
        inv_dict = inventory.model_dump(mode="json")
        print(json.dumps(inv_dict, indent=2))

    return 0


def build_validate_api_parser() -> argparse.ArgumentParser:
    """Build argument parser for external API intelligence and live validation."""
    parser = argparse.ArgumentParser(
        prog="dependency-guardian validate-api",
        description="Dependency Guardian Safe Live External API Intelligence & Contract Validator",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
        help="Show program version number and exit",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Path to dependency-guardian.yml or configuration file, or endpoint URL",
    )
    parser.add_argument(
        "--config",
        "-c",
        default=None,
        help="Path to dependency-guardian.yml specification file",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Direct target API URL for single read-only probe",
    )
    parser.add_argument(
        "--method",
        default="GET",
        help="HTTP method for single probe (GET, HEAD, OPTIONS only; mutating methods rejected)",
    )
    parser.add_argument(
        "--service-name",
        default="external-service",
        help="Service identifier for target probe",
    )
    parser.add_argument(
        "--auth-env-var",
        default=None,
        help="Environment variable containing authorization token",
    )
    parser.add_argument(
        "--expected-status",
        type=int,
        default=None,
        help="Expected HTTP response status code (e.g. 200)",
    )
    parser.add_argument(
        "--expected-fields",
        nargs="*",
        default=[],
        help="List of expected schema fields in JSON response",
    )
    parser.add_argument(
        "--timeout",
        dest="timeout_seconds",
        type=float,
        default=5.0,
        help="HTTP timeout in seconds per probe (default: 5.0)",
    )
    parser.add_argument(
        "--concurrency",
        dest="max_concurrency",
        type=int,
        default=5,
        help="Maximum concurrent probe requests (default: 5)",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=25,
        help="Maximum total probe requests to execute (safety bound, default: 25)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path for live validation JSON report",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "summary", "both"],
        default="json",
        help="Console output format: json (default), summary, or both",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["algorithmic", "ai", "hybrid"],
        default="algorithmic",
        help="Detection mode: algorithmic (default offline), ai, or hybrid",
    )
    parser.add_argument(
        "--provider",
        dest="ai_provider",
        choices=["mock", "ollama", "hosted"],
        default=None,
        help="AI provider identifier for explanation",
    )
    parser.add_argument(
        "--model",
        dest="ai_model",
        default=None,
        help="Target model identifier for AI provider",
    )
    parser.add_argument(
        "--base-url",
        dest="ai_base_url",
        default=None,
        help="Custom base URL for AI provider endpoint",
    )
    parser.add_argument(
        "--api-key",
        dest="ai_api_key",
        default=None,
        help="API key for hosted AI provider",
    )
    parser.add_argument(
        "--fail-on-breaking",
        action="store_true",
        help="Exit with non-zero status code (1) if contract mismatches or high-severity errors occur",
    )
    parser.add_argument(
        "--workspace-dir",
        "-w",
        default=None,
        help="Directory to resolve workspace-level configuration",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging output",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress informational console output",
    )
    return parser


def _format_validate_api_summary(report: LiveValidationReport) -> str:
    """Format live API validation summary report for terminal display."""
    lines = [
        "=" * 76,
        " DEPENDENCY GUARDIAN — EXTERNAL API INTELLIGENCE & VALIDATION REPORT",
        "=" * 76,
        f" Total Probes:         {report.total_probes} | Duration: {report.duration_seconds:.2f}s",
        f" Detection Mode:       {report.mode.upper()}",
    ]
    if report.ai_status and report.ai_status != "skipped":
        lines.append(f" AI Model:             {report.ai_model or 'default'} (Status: {report.ai_status})")
        if report.ai_error:
            lines.append(f" AI Notice:            {report.ai_error}")
    lines.extend([
        "-" * 76,
        " Probe Status Breakdown:",
        f"   - Reachable:         {report.reachable_count}",
        f"   - Auth Failure:      {report.auth_failure_count}",
        f"   - Client Error:      {report.client_error_count}",
        f"   - Server Failure:    {report.server_failure_count}",
        f"   - Unreachable:       {report.unreachable_count}",
        f"   - Contract Mismatch: {report.contract_mismatch_count}",
        f"   - Security Blocked:  {report.security_blocked_count}",
        "-" * 76,
        f" Findings Identified:  {len(report.findings)}",
    ])
    if report.results:
        lines.append("-" * 76)
        lines.append(f" {'STATUS':<18} {'METHOD':<6} {'CODE':<6} {'ENDPOINT'}")
        lines.append("-" * 76)
        for r in report.results:
            sc = str(r.status_code) if r.status_code else "-"
            lines.append(f" {r.status.value:<18} {r.method:<6} {sc:<6} {r.url}")
            if r.error_message:
                lines.append(f"   Note: {r.error_message}")
    if report.findings:
        lines.append("-" * 76)
        lines.append(" Findings & Discrepancies:")
        for f in report.findings:
            lines.append(f"   [{f.severity.value.upper()}] {f.rule_id} ({f.path}): {f.message}")
            if f.recommended_action:
                lines.append(f"     Action: {f.recommended_action}")
    lines.append("=" * 76)
    return "\n".join(lines)


def run_validate_api(validate_args: List[str]) -> int:
    """Execute external API intelligence and live validation."""
    parser = build_validate_api_parser()
    args = parser.parse_args(validate_args)

    log_level = logging.DEBUG if args.verbose else (logging.ERROR if args.quiet else logging.INFO)
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    endpoints: List[LiveProbeEndpoint] = []
    config_source: Optional[str] = None

    if args.url:
        endpoints.append(
            LiveProbeEndpoint(
                id=f"direct:{args.service_name}",
                service_name=args.service_name,
                base_url=args.url,
                path="",
                method=args.method or "GET",
                auth_env_var=args.auth_env_var,
                expected_status_code=args.expected_status or 200,
                expected_fields=args.expected_fields or [],
            )
        )
        config_source = f"direct-url:{args.url}"
    else:
        cfg_candidates = []
        if args.config:
            cfg_candidates.append(args.config)
        if args.target and (args.target.endswith(".yml") or args.target.endswith(".yaml") or args.target.endswith(".json")):
            cfg_candidates.append(args.target)
        if args.target and Path(args.target).is_dir():
            target_p = Path(args.target).resolve()
            cfg_candidates.append(str(target_p / "dependency-guardian.yml"))
            cfg_candidates.append(str(target_p / ".dependency-guardian.yml"))
        if args.workspace_dir:
            ws_p = Path(args.workspace_dir).resolve()
            cfg_candidates.append(str(ws_p / "dependency-guardian.yml"))
            cfg_candidates.append(str(ws_p / ".dependency-guardian.yml"))
            cfg_candidates.append(str(ws_p / "demo/sample-api/dependency-guardian.yml"))
            cfg_candidates.append(str(ws_p / "demo-app/dependency-guardian.yml"))
            for parent in ws_p.parents:
                cfg_candidates.append(str(parent / "dependency-guardian.yml"))
                if (parent / ".git").exists():
                    break
        cfg_candidates.extend([
            "dependency-guardian.yml",
            ".dependency-guardian.yml",
            "demo/sample-api/dependency-guardian.yml",
            "demo-app/dependency-guardian.yml",
        ])
        for parent in Path.cwd().resolve().parents:
            cfg_candidates.append(str(parent / "dependency-guardian.yml"))
            if (parent / ".git").exists():
                break

        resolved_cfg = None
        for cand in cfg_candidates:
            if cand and Path(cand).is_file():
                resolved_cfg = cand
                break

        if resolved_cfg:
            try:
                endpoints = LiveApiValidator.load_endpoints_from_yaml(resolved_cfg)
                config_source = str(Path(resolved_cfg).resolve())
            except Exception as exc:
                sys.stderr.write(f"Failed to load probe configuration from '{resolved_cfg}': {exc}\n")
                return 1
        elif args.target and args.target.startswith(("http://", "https://")):
            endpoints.append(
                LiveProbeEndpoint(
                    id=f"direct:{args.service_name}",
                    service_name=args.service_name,
                    base_url=args.target,
                    path="",
                    method=args.method or "GET",
                    auth_env_var=args.auth_env_var,
                    expected_status_code=args.expected_status or 200,
                    expected_fields=args.expected_fields or [],
                )
            )
            config_source = f"direct-target:{args.target}"
        else:
            sys.stderr.write("No external API probe targets configured. Specify a URL or dependency-guardian.yml config.\n")
            return 1

    ai_status = "skipped"
    ai_error = None
    ai_provider_name = args.ai_provider or "ollama"
    ai_model_name = args.ai_model or "qwen2.5-coder:7b"

    if args.mode in ("ai", "hybrid"):
        cli_overrides: Dict[str, Any] = {}
        if args.ai_provider:
            cli_overrides["ai_provider"] = args.ai_provider
        if args.ai_model:
            cli_overrides["ai_model"] = args.ai_model
        if args.ai_base_url:
            cli_overrides["ai_base_url"] = args.ai_base_url

        workspace_dir = Path(args.workspace_dir) if args.workspace_dir else Path.cwd()
        detection_config = load_configuration(workspace_dir=workspace_dir, cli_overrides=cli_overrides)
        if not detection_config.ai_provider:
            detection_config.ai_provider = "ollama"

        orchestrator = DetectionOrchestrator(detection_config)
        provider = orchestrator._resolve_ai_provider()
        ai_provider_name = detection_config.ai_provider
        ai_model_name = detection_config.ai_model

        try:
            health = provider.check_health()
            if health.is_available:
                ai_status = "active"
            else:
                ai_status = "fallback" if args.mode == "hybrid" else "unavailable"
                ai_error = health.message or "AI model endpoint unavailable."
                if args.mode == "ai":
                    sys.stderr.write(f"AI Detection Mode failed: {ai_error}\n")
                    return 1
        except Exception as exc:
            ai_status = "fallback" if args.mode == "hybrid" else "failed"
            ai_error = str(exc)
            if args.mode == "ai":
                sys.stderr.write(f"AI Detection Mode failed: {exc}\n")
                return 1

    options = LiveValidationOptions(
        timeout_seconds=args.timeout_seconds,
        max_concurrency=args.max_concurrency,
        max_requests=args.max_requests,
    )
    validator = LiveApiValidator(options=options)

    def on_progress(p: Dict[str, Any]) -> None:
        if not args.quiet:
            sys.stderr.write(f"[External API Validation] {p.get('message', '')}\n")
            sys.stderr.flush()

    try:
        report = asyncio.run(validator.validate_endpoints(endpoints, on_progress=on_progress))
        report.config_source = config_source
        report.mode = args.mode
        report.ai_status = ai_status
        report.ai_provider = ai_provider_name if args.mode != "algorithmic" else None
        report.ai_model = ai_model_name if args.mode != "algorithmic" else None
        report.ai_error = ai_error
    except Exception as exc:
        sys.stderr.write(f"Validation execution failed: {exc}\n")
        return 1

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(report.model_dump(mode="json"), indent=2))
    elif args.format == "summary":
        if not args.quiet:
            print(_format_validate_api_summary(report))
    elif args.format == "both":
        if not args.quiet:
            print(_format_validate_api_summary(report))
        print(json.dumps(report.model_dump(mode="json"), indent=2))

    if args.fail_on_breaking:
        has_breaking = (
            report.contract_mismatch_count > 0
            or any(f.severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH) for f in report.findings)
        )
        if has_breaking:
            return 1

    return 0


def run(argv: Optional[List[str]] = None) -> int:
    """Execute detection CLI command."""
    effective_argv = list(sys.argv[1:]) if argv is None else list(argv)
    if effective_argv and effective_argv[0] == "scan-repo":
        return run_scan_repo(effective_argv[1:])
    if effective_argv and effective_argv[0] == "validate-api":
        return run_validate_api(effective_argv[1:])

    parser = build_parser()
    args = parser.parse_args(argv)

    log_level = logging.DEBUG if args.verbose else (logging.ERROR if args.quiet else logging.INFO)
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    # Diagnostic mode: --check-ai
    if args.check_ai:
        cli_overrides: Dict[str, Any] = {}
        if args.ai_provider:
            cli_overrides["ai_provider"] = args.ai_provider
        if args.ai_model:
            cli_overrides["ai_model"] = args.ai_model
        if args.ai_base_url:
            cli_overrides["ai_base_url"] = args.ai_base_url
        if args.ai_timeout_seconds is not None:
            cli_overrides["ai_timeout_seconds"] = args.ai_timeout_seconds

        workspace_dir = Path(args.workspace_dir) if args.workspace_dir else Path.cwd()
        config = load_configuration(workspace_dir=workspace_dir, cli_overrides=cli_overrides)
        if not config.ai_provider:
            config.ai_provider = "ollama"

        orchestrator = DetectionOrchestrator(config=config)
        health = orchestrator.get_provider_health()

        print("=" * 72)
        print(" Dependency Guardian AI Provider Diagnostic")
        print("=" * 72)
        print(f" Provider:         {config.ai_provider}")
        print(f" Endpoint:         {health.get('base_url', 'unknown')}")
        print(f" Reachable:        {health.get('reachable', False)}")
        print(f" Installed Models: {health.get('installed_models', [])}")
        print(f" Selected Model:   {health.get('selected_model', 'none')}")
        print(f" Model Ready:      {health.get('model_available', False)}")
        if health.get("error"):
            print(f" Error:            {health.get('error')}")
        print("=" * 72)
        return 0 if (health.get("reachable") and health.get("model_available")) else 1

    # Standalone approval workflow: --approve-tests
    if args.approve_tests and not (args.baseline_opt or args.baseline_pos):
        target_dir = Path(args.approve_tests)
        generator = RegressionTestGenerator()
        try:
            approved_file = generator.approve_candidate_tests(target_dir, target_version=args.test_target)
            print(f"[+] Approved candidate tests successfully -> {approved_file}")
            return 0
        except Exception as exc:
            sys.stderr.write(f"Approval failed: {exc}\n")
            return 1

    # Standalone execution workflow: --execute-tests
    if args.execute_tests and not (args.baseline_opt or args.baseline_pos):
        target_dir = Path(args.execute_tests)
        approved_file = target_dir / f"test_approved_regression_{args.test_target}.py"
        if not approved_file.is_file():
            cand_file = target_dir / f"test_candidate_regression_{args.test_target}.py"
            if cand_file.is_file():
                sys.stderr.write(
                    f"Error: Candidate tests exist at {cand_file} but have not been approved.\n"
                    f"Run with '--approve-tests {target_dir}' before execution.\n"
                )
            else:
                sys.stderr.write(f"Error: No approved test file found at {approved_file}\n")
            return 1

        generator = RegressionTestGenerator()
        summary = generator.execute_approved_tests(approved_file)
        _print_test_summary(summary)
        return summary.exit_code

    # Resolve baseline and current file paths
    baseline_path = args.baseline_opt or args.baseline_pos
    current_path = args.current_opt or args.current_pos

    if not baseline_path or not current_path:
        parser.print_help(sys.stderr)
        sys.stderr.write("\nError: Both baseline and current specification paths are required.\n")
        return 2

    # Build CLI overrides dictionary (excluding None values)
    cli_overrides: Dict[str, Any] = {}
    if args.mode:
        cli_overrides["detection_mode"] = DetectionMode(args.mode)
    if args.ai_provider:
        cli_overrides["ai_provider"] = args.ai_provider
    if args.ai_model:
        cli_overrides["ai_model"] = args.ai_model
    if args.ai_base_url:
        cli_overrides["ai_base_url"] = args.ai_base_url
    if args.ai_api_key:
        cli_overrides["ai_api_key"] = args.ai_api_key
    if args.ai_timeout_seconds is not None:
        cli_overrides["ai_timeout_seconds"] = args.ai_timeout_seconds
    if args.ai_fallback_policy:
        cli_overrides["ai_fallback_policy"] = AIFallbackPolicy(args.ai_fallback_policy)
    if args.backend_base_url:
        cli_overrides["backend_base_url"] = args.backend_base_url

    workspace_dir = Path(args.workspace_dir) if args.workspace_dir else Path.cwd()

    try:
        config = load_configuration(
            workspace_dir=workspace_dir,
            cli_overrides=cli_overrides,
        )
    except Exception as exc:
        sys.stderr.write(f"Configuration error: {exc}\n")
        return 2

    # Load specification files
    try:
        baseline_spec = _load_spec_file(baseline_path)
    except Exception as exc:
        sys.stderr.write(f"Error loading baseline specification: {exc}\n")
        return 2

    try:
        current_spec = _load_spec_file(current_path)
    except Exception as exc:
        sys.stderr.write(f"Error loading current specification: {exc}\n")
        return 2

    # Instantiate orchestrator and execute detection
    try:
        orchestrator = DetectionOrchestrator(config=config)
        request = DetectionRequest(
            baseline_spec=baseline_spec,
            current_spec=current_spec,
            dependency_id=args.dependency_id,
            project_id=args.project_id,
            mode=config.detection_mode,
        )
        result = orchestrator.execute(request)
    except Exception as exc:
        sys.stderr.write(f"Detection execution failed: {exc}\n")
        return 1

    # Backend synchronization and repair proposals
    effective_project_id = args.project_id or os.getenv("DEPENDENCY_GUARDIAN_PROJECT_ID") or os.getenv("PROJECT_ID")
    effective_dependency_id = args.dependency_id or os.getenv("DEPENDENCY_GUARDIAN_DEPENDENCY_ID") or os.getenv("DEPENDENCY_ID")

    if args.sync_backend or args.propose_repairs or (args.backend_base_url and effective_project_id and effective_dependency_id):
        if not effective_project_id or not effective_dependency_id:
            sys.stderr.write("Error: Both --project-id and --dependency-id are required for backend synchronization or repair proposals.\n")
            return 2

        backend_url = args.backend_base_url or config.backend_base_url
        client = BackendClient(base_url=backend_url)
        sync_res = client.sync_detection_result(
            project_id=effective_project_id,
            dependency_id=effective_dependency_id,
            result=result,
        )

        if not sync_res.get("synced"):
            sys.stderr.write(f"[-] Backend synchronization failed: {sync_res.get('reason', 'Unknown error')}\n")
            if sync_res.get("errors"):
                for err in sync_res["errors"]:
                    sys.stderr.write(f"    * {err}\n")
        else:
            if not args.quiet:
                sys.stderr.write(
                    f"[+] Backend synchronization successful:\n"
                    f"    * Scan ID: {sync_res.get('scan_id')}\n"
                    f"    * Observations recorded: {sync_res.get('observations_count')}\n"
                    f"    * Incidents created/linked: {sync_res.get('incidents_created')}\n"
                )

        if args.propose_repairs:
            if not sync_res.get("synced"):
                sys.stderr.write("[-] Skipping repair proposal generation: backend synchronization failed.\n")
            elif not sync_res.get("incident_records"):
                if not args.quiet:
                    sys.stderr.write("[*] No breaking-change incidents were recorded; no repair proposals generated.\n")
            else:
                try:
                    from repair_agent import RepairPipeline, RepairRequest, FindingInput, RepairBackendClient

                    repair_client = RepairBackendClient(base_url=backend_url)
                    repair_pipeline = RepairPipeline()

                    for rec in sync_res["incident_records"]:
                        inc_id = rec["incident_id"]
                        finding_obj = rec["finding"]
                        target_file = None
                        if rec.get("payload", {}).get("affected_files"):
                            target_file = rec["payload"]["affected_files"][0]
                        elif finding_obj.evidence.get("file"):
                            target_file = str(finding_obj.evidence["file"])

                        finding_input = FindingInput(
                            id=str(finding_obj.id),
                            rule_id=str(finding_obj.rule_id),
                            path=finding_obj.path or "/",
                            method=finding_obj.method,
                            schema_location=finding_obj.schema_location or "",
                            previous_value=finding_obj.previous_value,
                            current_value=finding_obj.current_value,
                            message=finding_obj.message,
                            evidence=finding_obj.evidence,
                            compatibility=finding_obj.compatibility.value,
                            severity=finding_obj.severity.value,
                        )
                        rep_req = RepairRequest(
                            finding=finding_input,
                            target_file=target_file,
                            workspace_dir=str(workspace_dir),
                            test_command=args.test_cmd,
                        )
                        rep_res = repair_pipeline.run(rep_req)
                        published = repair_client.publish_repair_lifecycle(
                            incident_id=inc_id,
                            result=rep_res,
                            test_command=args.test_cmd,
                        )
                        if not args.quiet:
                            sys.stderr.write(
                                f"[+] Generated repair proposal '{published['repair_id']}' for incident '{inc_id}' "
                                f"(Strategy: {rep_res.strategy}, Status: {rep_res.status.value}, Validated: {rep_res.is_validated})\n"
                            )
                except Exception as exc:
                    logger.warning("Automated repair proposal generation failed: %s", exc)
                    sys.stderr.write(f"[-] Repair generation failed: {exc}\n")

    # Output formatting
    result_dict = result.model_dump(mode="json")
    json_output = json.dumps(result_dict, indent=2)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_output, encoding="utf-8")
        if not args.quiet:
            sys.stderr.write(f"Detection result saved to {args.output}\n")

    if args.format == "json":
        if not args.output:
            print(json_output)
    elif args.format == "summary":
        print(_format_summary_table(result))
    elif args.format == "both":
        print(_format_summary_table(result))
        print(json_output)

    # Save AI risk insights report if requested
    if args.insights_output and result.ai_insights:
        insights_p = Path(args.insights_output)
        insights_p.parent.mkdir(parents=True, exist_ok=True)
        if insights_p.suffix.lower() == ".json":
            insights_p.write_text(json.dumps(result.ai_insights, indent=2), encoding="utf-8")
        else:
            txt_report = format_insights_text(result.ai_insights, result.summary.model_dump())
            insights_p.write_text(txt_report, encoding="utf-8")
        if not args.quiet:
            sys.stderr.write(f"AI Risk Insights report saved to {args.insights_output}\n")

    # Test generation and preview
    generator = RegressionTestGenerator()
    if args.preview_tests:
        candidate_tests = generator.generate_candidate_tests(
            result.findings, target_version=args.test_target
        )
        _preview_candidate_tests(candidate_tests)

    if args.generate_tests:
        gen_dir = Path(args.generate_tests)
        candidate_tests = generator.generate_candidate_tests(
            result.findings,
            target_version=args.test_target,
            output_dir=gen_dir,
        )
        if not args.quiet:
            sys.stderr.write(f"[+] Generated {len(candidate_tests)} candidate regression tests into {gen_dir}\n")

    if args.execute_tests:
        exec_dir = Path(args.execute_tests)
        appr_file = exec_dir / f"test_approved_regression_{args.test_target}.py"
        if not appr_file.is_file():
            sys.stderr.write(
                f"[!] Notice: Candidate tests in {exec_dir} have not been approved for execution.\n"
                f"    Run 'dependency-guardian --approve-tests {exec_dir}' to approve.\n"
            )
        else:
            test_summary = generator.execute_approved_tests(appr_file)
            _print_test_summary(test_summary)

    if args.fail_on_breaking and result.summary.breaking_count > 0:
        return 1

    return 0 if result.success else 1


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
