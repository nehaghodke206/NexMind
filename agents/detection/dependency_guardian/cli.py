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

    try:
        scanner = RepositoryIntelligenceScanner(repo_path=repo_path, ai_provider=ai_provider)
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


def run(argv: Optional[List[str]] = None) -> int:
    """Execute detection CLI command."""
    effective_argv = list(sys.argv[1:]) if argv is None else list(argv)
    if effective_argv and effective_argv[0] == "scan-repo":
        return run_scan_repo(effective_argv[1:])

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

    # Optional backend synchronization
    if args.sync_backend or (args.backend_base_url and args.project_id and args.dependency_id):
        backend_url = config.backend_base_url or "http://127.0.0.1:8000/api/v1"
        client = BackendClient(base_url=backend_url)
        if args.project_id and args.dependency_id:
            sync_res = client.sync_detection_result(
                project_id=args.project_id,
                dependency_id=args.dependency_id,
                result=result,
            )
            if not args.quiet:
                sys.stderr.write(f"Backend synchronization: {sync_res}\n")

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
