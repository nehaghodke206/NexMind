import ast
from dataclasses import dataclass, field
import logging
from pathlib import Path
import re
from typing import List, Optional, Set

from .models import FindingInput

logger = logging.getLogger("repair_agent.inspector")

EXCLUDED_DIR_NAMES: Set[str] = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".tox",
    "build",
    "dist",
    ".mypy_cache",
}


@dataclass
class InspectionResult:
    """Outcome of inspecting target source code for a finding."""

    file_path: Path
    content: str
    target_symbol: Optional[str] = None
    line_number: Optional[int] = None
    snippet: Optional[str] = None
    enclosing_symbol: Optional[str] = None
    enclosing_type: Optional[str] = None
    affected_symbols: List[str] = field(default_factory=list)
    related_files: List[Path] = field(default_factory=list)


class CodeInspector:
    """Inspects affected application code without modifying any files."""

    def __init__(self, workspace_dir: Optional[Path] = None):
        self.workspace_dir = workspace_dir.resolve() if workspace_dir else None

    def _validate_workspace_path(self, path: Path) -> Path:
        """Enforce workspace boundary and prevent path traversal."""
        resolved = path.resolve()
        if self.workspace_dir:
            try:
                resolved.relative_to(self.workspace_dir)
            except ValueError:
                raise PermissionError(
                    f"Target path '{path}' escapes workspace boundary '{self.workspace_dir}'"
                )
        return resolved

    def inspect(self, finding: FindingInput, target_file: Optional[str] = None) -> InspectionResult:
        """Locate and read the source code affected by a detection finding."""
        if target_file:
            path = Path(target_file)
            if not path.is_file() and self.workspace_dir:
                path = self.workspace_dir / target_file
            if not path.is_file():
                raise FileNotFoundError(f"Target file does not exist: {target_file}")
            resolved_path = self._validate_workspace_path(path)
            return self._inspect_file(resolved_path, finding)

        # If no explicit file provided, search workspace for references
        if not self.workspace_dir or not self.workspace_dir.is_dir():
            raise ValueError(
                "Neither target_file nor a valid workspace_dir was provided to inspect affected code."
            )

        found_path = self._search_workspace_for_finding(finding)
        if not found_path:
            raise FileNotFoundError(
                f"Could not automatically locate source file affected by finding for path '{finding.path}' in {self.workspace_dir}"
            )

        resolved_path = self._validate_workspace_path(found_path)
        return self._inspect_file(resolved_path, finding)

    def find_affected_files(
        self,
        finding: FindingInput,
        target_files: Optional[List[str]] = None,
    ) -> List[Path]:
        """Discover all source files affected by a finding across the workspace."""
        if target_files:
            results: List[Path] = []
            for tf in target_files:
                p = Path(tf)
                if not p.is_file() and self.workspace_dir:
                    p = self.workspace_dir / tf
                if not p.is_file():
                    raise FileNotFoundError(f"Target file does not exist: {tf}")
                results.append(self._validate_workspace_path(p))
            return results

        if not self.workspace_dir or not self.workspace_dir.is_dir():
            return []

        terms = self._extract_search_terms(finding)
        extensions = {".py", ".js", ".ts"}
        matched_paths: List[Path] = []

        for p in self.workspace_dir.rglob("*"):
            if not p.is_file() or p.suffix not in extensions:
                continue
            if any(part in EXCLUDED_DIR_NAMES or part.startswith(".") for part in p.parts):
                continue
            if p.name.startswith("test_") or p.name.endswith("_test.py") or "tests" in p.parts or "test" in p.parts:
                continue

            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                for term in terms:
                    if term and term in text:
                        matched_paths.append(self._validate_workspace_path(p))
                        break
            except Exception:
                continue

        return list(dict.fromkeys(matched_paths))

    def _inspect_file(self, file_path: Path, finding: FindingInput) -> InspectionResult:
        """Inspect specific file content, detect enclosing symbols and context snippet."""
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Identify key terms from finding
        search_terms = self._extract_search_terms(finding)
        matched_line_idx = None
        matched_term = None

        for idx, line in enumerate(lines):
            for term in search_terms:
                if term and term in line:
                    matched_line_idx = idx
                    matched_term = term
                    break
            if matched_line_idx is not None:
                break

        line_num = matched_line_idx + 1 if matched_line_idx is not None else None

        # AST analysis for Python files
        enclosing_symbol = None
        enclosing_type = None
        affected_symbols: List[str] = []

        if file_path.suffix == ".py":
            try:
                tree = ast.parse(content)
                enclosing_symbol, enclosing_type, affected_symbols = self._analyze_python_ast(
                    tree, line_num
                )
            except Exception as e:
                logger.debug(f"AST parsing during inspection skipped: {e}")

        # Focused context snippet (~30 lines centered around matched line)
        snippet = None
        if matched_line_idx is not None:
            start = max(0, matched_line_idx - 15)
            end = min(len(lines), matched_line_idx + 15)
            snippet = "\n".join(lines[start:end])
        elif content:
            snippet = "\n".join(lines[:30])

        # Discover related files in the workspace if workspace is provided
        related_files: List[Path] = []
        if self.workspace_dir and self.workspace_dir.is_dir():
            all_affected = self.find_affected_files(finding)
            related_files = [p for p in all_affected if p.resolve() != file_path.resolve()]

        return InspectionResult(
            file_path=file_path.resolve(),
            content=content,
            target_symbol=matched_term,
            line_number=line_num,
            snippet=snippet or "",
            enclosing_symbol=enclosing_symbol,
            enclosing_type=enclosing_type,
            affected_symbols=affected_symbols,
            related_files=related_files,
        )

    def _analyze_python_ast(
        self, tree: ast.AST, target_line: Optional[int]
    ) -> tuple[Optional[str], Optional[str], List[str]]:
        """Walk AST to find enclosing symbol for target_line and collect symbols."""
        enclosing_symbol = None
        enclosing_type = None
        symbols: List[str] = []

        innermost_node = None
        innermost_span = float("inf")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.append(node.name)
                if target_line is not None:
                    node_start = getattr(node, "lineno", 0)
                    node_end = getattr(node, "end_lineno", node_start)
                    if node_start <= target_line <= node_end:
                        span = node_end - node_start
                        if span < innermost_span:
                            innermost_span = span
                            innermost_node = node

        if innermost_node:
            enclosing_symbol = innermost_node.name
            if isinstance(innermost_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                enclosing_type = "function"
            elif isinstance(innermost_node, ast.ClassDef):
                enclosing_type = "class"

        return enclosing_symbol, enclosing_type, list(dict.fromkeys(symbols))

    def _extract_search_terms(self, finding: FindingInput) -> List[str]:
        """Extract high-relevance search terms from finding."""
        terms: List[str] = []
        # Path term e.g. /users or /products
        if finding.path:
            terms.append(finding.path)
            # Add short path suffix
            parts = [p for p in finding.path.split("/") if p and not p.startswith("{")]
            if parts:
                terms.append(parts[-1])

        # Evidence properties
        ev = finding.evidence or {}
        for key in [
            "removed_property",
            "added_property",
            "parameter_name",
            "renamed_from",
            "renamed_to",
            "field",
            "property",
        ]:
            if key in ev and isinstance(ev[key], str):
                terms.append(ev[key])

        # Schema location property
        if finding.schema_location:
            loc_parts = finding.schema_location.split(".")
            if loc_parts:
                terms.append(loc_parts[-1])

        return list(dict.fromkeys(terms))  # deduplicate preserving order

    def _search_workspace_for_finding(self, finding: FindingInput) -> Optional[Path]:
        """Search workspace source files (.py, .ts, .js) for matching endpoint or fields."""
        files = self.find_affected_files(finding)
        return files[0] if files else None
