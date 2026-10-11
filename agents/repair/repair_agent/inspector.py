from dataclasses import dataclass
import logging
from pathlib import Path
from typing import List, Optional
import re

from .models import FindingInput

logger = logging.getLogger("repair_agent.inspector")


@dataclass
class InspectionResult:
    """Outcome of inspecting target source code for a finding."""

    file_path: Path
    content: str
    target_symbol: Optional[str] = None
    line_number: Optional[int] = None
    snippet: Optional[str] = None


class CodeInspector:
    """Inspects affected application code without modifying any files."""

    def __init__(self, workspace_dir: Optional[Path] = None):
        self.workspace_dir = workspace_dir

    def inspect(self, finding: FindingInput, target_file: Optional[str] = None) -> InspectionResult:
        """Locate and read the source code affected by a detection finding."""
        if target_file:
            path = Path(target_file)
            if not path.is_file() and self.workspace_dir:
                path = self.workspace_dir / target_file
            if not path.is_file():
                raise FileNotFoundError(f"Target file does not exist: {target_file}")
            return self._inspect_file(path, finding)

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

        return self._inspect_file(found_path, finding)

    def _inspect_file(self, file_path: Path, finding: FindingInput) -> InspectionResult:
        """Inspect specific file content and find relevant line numbers."""
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

        snippet = None
        line_num = None
        if matched_line_idx is not None:
            line_num = matched_line_idx + 1
            start = max(0, matched_line_idx - 5)
            end = min(len(lines), matched_line_idx + 6)
            snippet = "\n".join(lines[start:end])

        return InspectionResult(
            file_path=file_path.resolve(),
            content=content,
            target_symbol=matched_term,
            line_number=line_num,
            snippet=snippet or (content[:400] if content else ""),
        )

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
        for key in ["removed_property", "added_property", "parameter_name", "renamed_from", "renamed_to", "field"]:
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
        if not self.workspace_dir:
            return None

        terms = self._extract_search_terms(finding)
        extensions = {".py", ".js", ".ts"}

        for p in self.workspace_dir.rglob("*"):
            if not p.is_file() or p.suffix not in extensions:
                continue
            # Skip hidden, virtual environments, node_modules
            if any(part.startswith(".") or part in {"node_modules", "venv", ".venv", "__pycache__"} for part in p.parts):
                continue

            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                for term in terms:
                    if term and term in text:
                        return p
            except Exception:
                continue

        return None
