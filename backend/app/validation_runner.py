"""Validation runner executing configured test commands to verify repairs before application."""

import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from typing import Tuple
from .models import ValidationResult, RepairProposal, RepairStatus
from .config import GuardianConfig


def run_validation(
    repair: RepairProposal,
    config: GuardianConfig,
    workspace_root: str,
) -> ValidationResult:
    """Executes configured validation command in a controlled temporary patch context."""
    val_id = f"val_{uuid.uuid4().hex[:8]}"
    started_at = datetime.now(timezone.utc).isoformat()
    command = config.project.validation_command

    target_abs = os.path.join(workspace_root, repair.target_file) if repair.target_file else None
    original_content = None

    start_time = time.perf_counter()

    try:
        # If repair has a target file and code to patch, apply temporarily for testing
        if target_abs and os.path.exists(target_abs) and repair.proposed_code_snippet:
            with open(target_abs, "r", encoding="utf-8") as f:
                original_content = f.read()

            # Apply candidate replacement temporarily
            patched_content = original_content.replace(
                repair.original_code_snippet,
                repair.proposed_code_snippet,
            )
            with open(target_abs, "w", encoding="utf-8") as f:
                f.write(patched_content)

        # Run configured command
        proc = subprocess.run(
            command,
            shell=True,
            cwd=workspace_root,
            capture_output=True,
            text=True,
            timeout=30.0,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        exit_code = proc.returncode
        output = proc.stdout + "\n" + proc.stderr

        status = "passed" if exit_code == 0 else "failed"

    except subprocess.TimeoutExpired:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        exit_code = -1
        output = "Validation command timed out after 30 seconds."
        status = "failed"
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        exit_code = -1
        output = f"Execution error running validation: {str(exc)}"
        status = "failed"
    finally:
        # RESTORE original content immediately so nothing is permanently changed until approval
        if target_abs and original_content is not None:
            with open(target_abs, "w", encoding="utf-8") as f:
                f.write(original_content)

    return ValidationResult(
        id=val_id,
        repair_id=repair.id,
        command=command,
        exit_code=exit_code,
        output_summary=output.strip(),
        duration_ms=round(duration_ms, 2),
        status=status,
        started_at=started_at,
    )
