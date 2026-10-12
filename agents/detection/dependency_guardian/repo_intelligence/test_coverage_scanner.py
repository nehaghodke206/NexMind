"""
Test Coverage and Verification Scanner.
Analyzes test suites across repository to correlate test files and test functions
with discovered API endpoints and integrations, identifying verified coverage and gaps.
"""
import ast
import logging
import os
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .models import EndpointDoc, ExternalIntegrationDoc, TestCoverageSummary
from .traversal import safe_walk

logger = logging.getLogger("dependency_guardian.repo_intelligence.test_coverage_scanner")


class TestCoverageScanner:
    """Discovers tests and computes endpoint and integration coverage."""
    __test__ = False

    def __init__(
        self,
        repo_root: Path,
        output_dir: Optional[Path] = None,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.repo_root = repo_root.resolve()
        self.output_dir = output_dir.resolve() if output_dir else None
        self.on_progress = on_progress
        self.test_files: List[Path] = []
        self.test_functions_by_file: Dict[str, List[Dict[str, Any]]] = {}

    def scan(self, endpoints: List[EndpointDoc], integrations: List[ExternalIntegrationDoc]) -> TestCoverageSummary:
        """
        Scan test files and map coverage to discovered endpoints and external integrations.
        Updates endpoints in-place with existing_tests and returns TestCoverageSummary.
        """
        self._discover_test_files()
        self._parse_test_functions()

        coverage_map: Dict[str, List[str]] = {}
        tested_count = 0
        integration_tests_found: List[str] = []

        for ep in endpoints:
            ep_key = f"{ep.http_method} {ep.route_path}"
            matching_tests: List[str] = []

            # Check each test function for references to this endpoint
            for test_file_rel, test_funcs in self.test_functions_by_file.items():
                for tf in test_funcs:
                    content_str = tf.get("body_text", "")
                    # Match by normalized path
                    path_tokens = [p for p in ep.route_path.split("/") if p and not p.startswith("{")]
                    
                    # Direct route path match
                    matched = False
                    if ep.route_path in content_str:
                        matched = True
                    # Partial distinctive route match
                    elif path_tokens and all(token in content_str for token in path_tokens[-2:]):
                        matched = True
                    # Handler function match
                    elif ep.handler_function and ep.handler_function in content_str:
                        matched = True

                    if matched:
                        test_ref = f"{test_file_rel}::{tf['name']}"
                        if test_ref not in matching_tests:
                            matching_tests.append(test_ref)

            ep.existing_tests = matching_tests
            if matching_tests:
                tested_count += 1
                coverage_map[ep_key] = matching_tests
                ep.test_results = "Covered by test suite"
            else:
                coverage_map[ep_key] = []
                ep.test_results = "No automated tests found (Coverage Gap)"

        # Check for integration tests touching external services
        for test_file_rel, test_funcs in self.test_functions_by_file.items():
            for tf in test_funcs:
                name_lower = tf["name"].lower()
                body_lower = tf.get("body_text", "").lower()
                if any(kw in name_lower or kw in body_lower for kw in ["integration", "stripe", "postgres", "redis", "database", "external"]):
                    ref = f"{test_file_rel}::{tf['name']}"
                    if ref not in integration_tests_found:
                        integration_tests_found.append(ref)

        total_eps = len(endpoints)
        pct = round((tested_count / total_eps * 100), 1) if total_eps > 0 else 0.0

        return TestCoverageSummary(
            total_endpoints=total_eps,
            tested_endpoints=tested_count,
            untested_endpoints=total_eps - tested_count,
            coverage_percentage=pct,
            endpoint_coverage_map=coverage_map,
            integration_tests_found=integration_tests_found,
        )

    def _discover_test_files(self) -> None:
        """Find test files across Python and JavaScript/TypeScript test directories."""
        for root, dirs, files in safe_walk(self.repo_root, output_dir=self.output_dir):
            rel_root = root.relative_to(self.repo_root)

            for f in files:
                f_path = root / f
                f_lower = f.lower()
                is_test_dir = any(part in ["tests", "test", "__tests__"] for part in rel_root.parts)
                is_test_file = (
                    f_lower.startswith("test_") or
                    f_lower.endswith("_test.py") or
                    f_lower.endswith(".test.js") or
                    f_lower.endswith(".test.ts") or
                    f_lower.endswith(".spec.js") or
                    f_lower.endswith(".spec.ts")
                )

                if (is_test_dir or is_test_file) and f_path.suffix in {".py", ".js", ".ts"}:
                    self.test_files.append(f_path)

    def _parse_test_functions(self) -> None:
        """Extract test function names and body text from test files."""
        total = len(self.test_files)
        for idx, t_file in enumerate(self.test_files, start=1):
            rel_file = str(t_file.relative_to(self.repo_root))
            if self.on_progress:
                self.on_progress({
                    "phase": "evaluating_tests",
                    "message": f"Analyzing test file ({idx}/{total}): {rel_file}",
                    "current_file": rel_file,
                    "files_processed": idx,
                    "total_files": total,
                })
            ext = t_file.suffix.lower()

            try:
                content = t_file.read_text(encoding="utf-8", errors="replace")
                if ext == ".py":
                    self._parse_python_test_file(content, rel_file)
                else:
                    self._parse_js_test_file(content, rel_file)
            except Exception as exc:
                logger.debug(f"Failed parsing test file {rel_file}: {exc}")

    def _parse_python_test_file(self, content: str, rel_file: str) -> None:
        """Extract Python test functions using AST with regex fallback."""
        funcs = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("test_"):
                        # Extract node line range
                        start_line = node.lineno
                        end_line = getattr(node, "end_lineno", start_line + 20)
                        lines = content.splitlines()[start_line - 1:end_line]
                        funcs.append({
                            "name": node.name,
                            "line": start_line,
                            "body_text": "\n".join(lines),
                        })
        except Exception:
            for line_no, line in enumerate(content.splitlines(), 1):
                m = re.match(r"^\s*def\s+(test_[a-zA-Z0-9_]+)", line)
                if m:
                    funcs.append({
                        "name": m.group(1),
                        "line": line_no,
                        "body_text": line,
                    })

        self.test_functions_by_file[rel_file] = funcs

    def _parse_js_test_file(self, content: str, rel_file: str) -> None:
        """Extract JS/TS test blocks using pattern matching."""
        funcs = []
        pattern = re.compile(r"""(?:it|test)\s*\(\s*['"]([^'"]+)['"]""")
        for line_no, line in enumerate(content.splitlines(), 1):
            m = pattern.search(line)
            if m:
                funcs.append({
                    "name": m.group(1),
                    "line": line_no,
                    "body_text": line,
                })
        self.test_functions_by_file[rel_file] = funcs
