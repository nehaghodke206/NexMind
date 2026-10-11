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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dependency-guardian",
        description="Dependency Guardian Detection Agent CLI for OpenAPI specifications",
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
    return parser


def run(argv: Optional[List[str]] = None) -> int:
    """Execute detection CLI command."""
    parser = build_parser()
    args = parser.parse_args(argv)

    log_level = logging.DEBUG if args.verbose else (logging.ERROR if args.quiet else logging.INFO)
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

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

    if args.fail_on_breaking and result.summary.breaking_count > 0:
        return 1

    return 0 if result.success else 1


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()

