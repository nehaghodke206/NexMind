import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, Optional

from .models import FindingInput, RepairRequest, RepairResult
from .pipeline import RepairPipeline

logger = logging.getLogger("repair_agent.cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dependency-guardian-repair",
        description="Dependency Guardian Repair Agent: Propose and validate backwards-compatible API repairs.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
        help="Show program version and exit",
    )
    parser.add_argument(
        "--finding",
        "-f",
        default=None,
        help="Path to finding JSON file or JSON string (optional if --incident-id is provided)",
    )
    parser.add_argument(
        "--incident-id",
        "-i",
        default=None,
        help="Backend incident ID to fetch finding details from and link proposals to",
    )
    parser.add_argument(
        "--sync-backend",
        action="store_true",
        help="Synchronize repair proposal and validation evidence with the backend service",
    )
    parser.add_argument(
        "--backend-url",
        default=None,
        help="Dependency Guardian backend API URL (defaults to centralized configuration)",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Record explicit human approval for the proposed repair on the backend",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Record patch application on the backend (requires prior approval)",
    )
    parser.add_argument(
        "--file",
        dest="target_file",
        default=None,
        help="Path to the affected application source file to inspect and repair",
    )
    parser.add_argument(
        "--workspace",
        "-w",
        dest="workspace_dir",
        default=None,
        help="Workspace directory to search for affected files or run validation tests",
    )
    parser.add_argument(
        "--provider",
        "-p",
        choices=["deterministic", "ollama"],
        default="deterministic",
        help="Patch generation strategy provider (default: deterministic)",
    )
    parser.add_argument(
        "--model",
        "-m",
        default=None,
        help="Local Ollama model name (defaults to centralized configuration)",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Local Ollama API base URL (defaults to centralized configuration)",
    )
    parser.add_argument(
        "--test-cmd",
        default=None,
        help="Optional test command to run in the temporary sandbox (e.g. 'pytest tests/test_user.py')",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path to write structured RepairResult JSON",
    )
    parser.add_argument(
        "--format",
        choices=["summary", "json", "diff"],
        default="summary",
        help="Output display format on terminal (default: summary)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def _load_finding(finding_arg: str) -> Dict[str, Any]:
    """Parse finding argument from file path or JSON string."""
    candidate_path = Path(finding_arg)
    if candidate_path.is_file():
        content = candidate_path.read_text(encoding="utf-8")
        return json.loads(content)
    try:
        return json.loads(finding_arg)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Finding argument is neither a valid file path nor valid JSON: {exc}") from exc


def _format_summary(result: RepairResult) -> str:
    """Format repair result into a terminal display summary."""
    lines = [
        "=" * 72,
        " DEPENDENCY GUARDIAN — REPAIR AGENT PROPOSAL SUMMARY",
        "=" * 72,
        f" Repair ID:          {result.repair_id}",
        f" Finding ID:         {result.finding_id}",
        f" Status:             {result.status.value.upper()}",
        f" Proposal Generated: {'Yes' if result.proposal_generated else 'No'}",
        f" Strategy:           {result.strategy}",
        f" Target File:        {result.target_file or 'N/A'}",
        f" Human Review:       {'Required' if result.requires_human_review else 'Optional'} (Approval: {result.approval_status})",
        "-" * 72,
        f" Explanation:        {result.explanation or result.error_message or 'N/A'}",
    ]
    if result.rationale:
        lines.append(f" Rationale:          {result.rationale}")
    if result.assumptions:
        lines.append(" Assumptions:")
        for asm in result.assumptions:
            lines.append(f"   * {asm}")
    if result.risks:
        lines.append(" Risks:")
        for rsk in result.risks:
            lines.append(f"   * {rsk}")
    if result.alternatives_considered:
        lines.append(" Alternatives Considered:")
        for alt in result.alternatives_considered:
            lines.append(f"   * {alt}")
    lines.extend([
        "-" * 72,
        " Validation Details:",
        f"   - AST Valid:      {result.validation.ast_valid}",
        f"   - Syntax Error:   {result.validation.syntax_error or 'None'}",
        f"   - Test Executed:  {result.validation.test_executed}",
        f"   - Test Passed:    {result.validation.test_passed if result.validation.test_passed is not None else 'N/A'}",
        f"   - Sandbox Time:   {result.validation.validation_time_ms}ms",
    ])
    if result.diff:
        lines.append("-" * 72)
        lines.append(" Proposed Reviewable Diff (Original file untouched):")
        lines.append(result.diff.strip())
    lines.append("=" * 72)
    return "\n".join(lines)


def run(argv: Optional[list] = None) -> int:
    from .backend_client import (
        RepairBackendClient,
        BackendCommunicationError,
        BackendNotFoundError,
        BackendValidationError,
        incident_to_finding_input,
    )

    parser = build_parser()
    args = parser.parse_args(argv)

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    if not args.finding and not args.incident_id:
        sys.stderr.write("Error: Either --finding or --incident-id is required.\n")
        return 2

    backend_client: Optional[RepairBackendClient] = None
    if args.incident_id or args.sync_backend or args.approve or args.apply:
        backend_client = RepairBackendClient(base_url=args.backend_url)

    target_file = args.target_file

    # Load finding from file or backend incident
    if args.finding:
        try:
            finding_dict = _load_finding(args.finding)
            finding_input = FindingInput.model_validate(finding_dict)
        except Exception as exc:
            sys.stderr.write(f"Error loading finding: {exc}\n")
            return 2
    else:
        try:
            assert backend_client is not None
            incident_data = backend_client.get_incident(args.incident_id)
            finding_input = incident_to_finding_input(incident_data)
            if not target_file and incident_data.get("affected_files"):
                target_file = incident_data["affected_files"][0]
        except Exception as exc:
            sys.stderr.write(f"Error fetching incident '{args.incident_id}' from backend: {exc}\n")
            return 2

    req_kwargs: Dict[str, Any] = {
        "finding": finding_input,
        "target_file": target_file,
        "workspace_dir": args.workspace_dir,
        "provider": args.provider,
        "test_command": args.test_cmd,
    }
    if args.model:
        req_kwargs["model"] = args.model
    if args.base_url:
        req_kwargs["base_url"] = args.base_url

    request = RepairRequest(**req_kwargs)
    pipeline = RepairPipeline()
    result = pipeline.run(request)

    # Optional backend synchronization
    repair_id = None
    if backend_client and args.incident_id and (args.sync_backend or not args.finding):
        try:
            sync_res = backend_client.publish_repair_lifecycle(
                incident_id=args.incident_id,
                result=result,
                test_command=args.test_cmd,
            )
            repair_id = sync_res["repair_id"]
            sys.stderr.write(f"[+] Persisted repair proposal '{repair_id}' under incident '{args.incident_id}'\n")
            if sync_res.get("validation_run_id"):
                sys.stderr.write(f"[+] Recorded validation run '{sync_res['validation_run_id']}'\n")

            # Verify retrievability
            retrieved = backend_client.get_proposal(repair_id)
            sys.stderr.write(f"[+] Confirmed proposal retrievable from backend (Status: {retrieved.get('status')})\n")

            if args.approve:
                appr = backend_client.approve_proposal(repair_id=repair_id)
                sys.stderr.write(f"[+] Human approval recorded: {appr.get('decision')}\n")

            if args.apply:
                appl = backend_client.record_application(repair_id=repair_id)
                sys.stderr.write(f"[+] Patch application recorded: {appl.get('status')}\n")
        except Exception as exc:
            sys.stderr.write(f"[-] Backend synchronization failed: {exc}\n")

    # Output to file if requested
    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        sys.stderr.write(f"[+] Repair result saved to {args.output}\n")

    # Format display
    if args.format == "json":
        print(result.model_dump_json(indent=2))
    elif args.format == "diff":
        if result.diff:
            print(result.diff)
        else:
            print(f"# No diff generated (Status: {result.status.value})")
    elif args.format == "summary":
        print(_format_summary(result))

    return 0 if result.status in ["validated", "proposed"] else 1


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
