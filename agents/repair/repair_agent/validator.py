import ast
import logging
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import List, Optional, Set

from .models import FileChange, ValidationDetails, ValidationStatus

logger = logging.getLogger("repair_agent.validator")

FORBIDDEN_CALLS: Set[str] = {"eval", "exec", "compile", "__import__"}
FORBIDDEN_MODULES: Set[str] = {"pty", "ctypes"}


class PatchValidator:
    """Validates candidate patches inside an isolated temporary directory."""

    def validate(
        self,
        target_file: Path,
        proposed_content: str,
        workspace_dir: Optional[Path] = None,
        test_command: Optional[str] = None,
        file_changes: Optional[List[FileChange]] = None,
    ) -> ValidationDetails:
        """Execute AST syntax and sandbox validation without touching original files."""
        start_time = time.perf_counter()
        target_resolved = target_file.resolve()
        workspace_resolved = workspace_dir.resolve() if workspace_dir else None

        # Step 1: AST Syntax and safety check for all changed Python files
        if file_changes:
            for fc in file_changes:
                fc_path = Path(fc.file_path)
                if fc_path.suffix == ".py":
                    ast_ok, syntax_err = self._check_python_ast(fc.proposed_content)
                    fc.ast_valid = ast_ok
                    fc.syntax_error = syntax_err
                    if not ast_ok:
                        elapsed = (time.perf_counter() - start_time) * 1000
                        return ValidationDetails(
                            status=ValidationStatus.FAILED,
                            ast_valid=False,
                            syntax_error=f"{fc_path.name}: {syntax_err}",
                            validation_time_ms=round(elapsed, 2),
                        )
        else:
            if target_resolved.suffix == ".py":
                ast_ok, syntax_err = self._check_python_ast(proposed_content)
                if not ast_ok:
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return ValidationDetails(
                        status=ValidationStatus.FAILED,
                        ast_valid=False,
                        syntax_error=syntax_err,
                        validation_time_ms=round(elapsed, 2),
                    )

        # Step 2: Sandbox copy validation
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            temp_dir_resolved = temp_dir.resolve()

            # If workspace is provided, copy it over for test execution
            if workspace_resolved and workspace_resolved.is_dir():
                for item in workspace_resolved.iterdir():
                    if item.name in {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules"}:
                        continue
                    dest = temp_dir / item.name
                    if item.is_dir():
                        shutil.copytree(
                            item,
                            dest,
                            symlinks=True,
                            ignore_dangling_symlinks=True,
                            ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", "*.sock"),
                        )
                    elif item.is_file():
                        shutil.copy2(item, dest)

                # Apply proposed file changes into temp copy
                changes_to_apply = file_changes if file_changes else [
                    FileChange(
                        file_path=str(target_resolved),
                        proposed_content=proposed_content,
                    )
                ]

                for fc in changes_to_apply:
                    fc_p = Path(fc.file_path)
                    try:
                        if fc_p.is_absolute():
                            rel = fc_p.resolve().relative_to(workspace_resolved)
                        else:
                            rel = fc_p
                    except ValueError:
                        rel = Path(fc_p.name)

                    dest_sandbox_file = (temp_dir / rel).resolve()
                    # Security check: ensure file path cannot escape sandbox directory
                    try:
                        dest_sandbox_file.relative_to(temp_dir_resolved)
                    except ValueError:
                        elapsed = (time.perf_counter() - start_time) * 1000
                        return ValidationDetails(
                            status=ValidationStatus.FAILED,
                            ast_valid=False,
                            syntax_error=f"Sandbox security violation: path traversal detected for '{fc.file_path}'",
                            validation_time_ms=round(elapsed, 2),
                        )

                    dest_sandbox_file.parent.mkdir(parents=True, exist_ok=True)
                    dest_sandbox_file.write_text(fc.proposed_content, encoding="utf-8")
            else:
                # No workspace directory, write primary target file directly in temp sandbox
                temp_target = temp_dir / target_resolved.name
                temp_target.write_text(proposed_content, encoding="utf-8")

            # Step 3: Run test command if provided
            test_passed = None
            test_out = None
            test_executed = False
            if test_command:
                test_executed = True
                sandbox_env = os.environ.copy()
                existing_pythonpath = sandbox_env.get("PYTHONPATH", "")
                sandbox_env["PYTHONPATH"] = (
                    f"{temp_dir_str}:{existing_pythonpath}".rstrip(":")
                    if existing_pythonpath
                    else temp_dir_str
                )
                sandbox_env["PYTHONDONTWRITEBYTECODE"] = "1"
                try:
                    proc = subprocess.run(
                        test_command,
                        shell=True,
                        cwd=temp_dir,
                        env=sandbox_env,
                        capture_output=True,
                        text=True,
                        timeout=15.0,
                    )
                    test_passed = proc.returncode == 0
                    test_out = (proc.stdout + "\n" + proc.stderr).strip()
                    if not test_passed:
                        elapsed = (time.perf_counter() - start_time) * 1000
                        return ValidationDetails(
                            status=ValidationStatus.FAILED,
                            ast_valid=True,
                            test_executed=True,
                            test_passed=False,
                            test_output=test_out,
                            validation_time_ms=round(elapsed, 2),
                        )
                except subprocess.TimeoutExpired:
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return ValidationDetails(
                        status=ValidationStatus.FAILED,
                        ast_valid=True,
                        test_executed=True,
                        test_passed=False,
                        test_output="Validation test timed out after 15.0s.",
                        validation_time_ms=round(elapsed, 2),
                    )
                except Exception as exc:
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return ValidationDetails(
                        status=ValidationStatus.FAILED,
                        ast_valid=True,
                        test_executed=True,
                        test_passed=False,
                        test_output=f"Validation test execution error: {exc}",
                        validation_time_ms=round(elapsed, 2),
                    )

        elapsed = (time.perf_counter() - start_time) * 1000
        return ValidationDetails(
            status=ValidationStatus.SUCCESS,
            ast_valid=True,
            test_executed=test_executed,
            test_passed=test_passed,
            test_output=test_out,
            validation_time_ms=round(elapsed, 2),
        )

    def _check_python_ast(self, content: str) -> tuple[bool, Optional[str]]:
        """Parse AST and verify syntax and safety."""
        try:
            tree = ast.parse(content)
        except SyntaxError as exc:
            return False, f"SyntaxError at line {exc.lineno}: {exc.msg}"
        except Exception as exc:
            return False, f"Failed to parse AST: {exc}"

        # Safety inspection: forbid dangerous builtins and modules
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                    return False, f"AST Safety violation: forbidden builtin call '{node.func.id}'"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_MODULES:
                        return False, f"AST Safety violation: forbidden module import '{alias.name}'"
            elif isinstance(node, ast.ImportFrom):
                if node.module in FORBIDDEN_MODULES:
                    return False, f"AST Safety violation: forbidden module import '{node.module}'"

        return True, None
