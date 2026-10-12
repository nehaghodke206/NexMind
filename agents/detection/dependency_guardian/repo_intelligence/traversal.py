"""
Repository Traversal and Path Filtering Utilities.
Provides directory pruning and efficient file discovery, ensuring that virtual environments,
package directories, caches, and generated report output directories are excluded from
recursive scanning.
"""
import os
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Set, Tuple

# Comprehensive set of directories that should never be descended into
DEFAULT_IGNORE_DIRS: Set[str] = {
    # Version control
    ".git", ".hg", ".svn",
    # Python virtual environments & packages
    ".venv", "venv", "env", ".env", "virtualenv", ".tox", "site-packages",
    # Node / JavaScript
    "node_modules", "bower_components", ".next", ".nuxt",
    # Caches and temporary outputs
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    # IDEs and editors
    ".idea", ".vscode",
    # Build artifacts
    "dist", "build", "target", "out",
    # Report directories and test coverage
    "reports", "coverage", ".coverage", "htmlcov",
}

# Source code extensions relevant for AST and dependency scanning
RELEVANT_EXTENSIONS: Set[str] = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".java", ".rb", ".php"
}

# Known manifest filenames
MANIFEST_FILENAMES: Set[str] = {
    "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "Pipfile.lock", "poetry.lock",
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "go.mod", "go.sum",
    "Cargo.toml", "Cargo.lock",
}

# Known OpenAPI / Swagger spec candidates
SPEC_FILENAMES: Set[str] = {
    "openapi.json", "openapi.yaml", "openapi.yml",
    "swagger.json", "swagger.yaml", "swagger.yml",
}


def get_effective_ignore_dirs(
    repo_root: Path,
    output_dir: Optional[Path] = None,
    extra_ignores: Optional[Set[str]] = None,
) -> Set[str]:
    """
    Computes effective set of directory names to ignore during traversal.
    Automatically includes output_dir if located within repo_root.
    """
    ignored = set(DEFAULT_IGNORE_DIRS)
    if extra_ignores:
        ignored.update(extra_ignores)

    if output_dir:
        try:
            out_resolved = output_dir.resolve()
            repo_resolved = repo_root.resolve()
            if out_resolved != repo_resolved and out_resolved.is_relative_to(repo_resolved):
                rel = out_resolved.relative_to(repo_resolved)
                if rel.parts:
                    # Ignore the top-level folder within repo_root containing output_dir
                    ignored.add(rel.parts[0])
        except Exception:
            pass

    return ignored


def safe_walk(
    repo_root: Path,
    output_dir: Optional[Path] = None,
    extra_ignores: Optional[Set[str]] = None,
) -> Iterator[Tuple[Path, List[str], List[str]]]:
    """
    Safe repository walker using os.walk with in-place directory pruning.
    Prevents descending into virtualenvs, node_modules, reports, and hidden directories.
    Yields (Path(root), dirs, files).
    """
    ignore_dirs = get_effective_ignore_dirs(repo_root, output_dir, extra_ignores)

    for root, dirs, files in os.walk(repo_root):
        # In-place directory pruning: os.walk will not descend into pruned directories
        dirs[:] = [
            d for d in dirs
            if d not in ignore_dirs and not d.startswith(".")
        ]
        yield Path(root), dirs, files


def find_spec_files(repo_root: Path, output_dir: Optional[Path] = None) -> List[Path]:
    """
    Finds OpenAPI and Swagger specification files using pruned safe_walk.
    Excludes generated reports and enriched specifications in output_dir.
    """
    specs: List[Path] = []
    out_resolved = output_dir.resolve() if output_dir else None

    for root, _, files in safe_walk(repo_root, output_dir=output_dir):
        root_path = Path(root)
        rel_root = root_path.relative_to(repo_root)

        for f in files:
            f_lower = f.lower()
            file_path = root_path / f

            # Skip generated output files
            if f_lower in {"openapi.enriched.json", "repository-inventory.json"}:
                continue
            if out_resolved and file_path.resolve().is_relative_to(out_resolved):
                continue

            # Check known candidate names
            if f_lower in SPEC_FILENAMES:
                if file_path not in specs:
                    specs.append(file_path)
                continue

            # Check files in contracts/ or docs/ directories
            is_contract_dir = any(part in ["contracts", "docs", "spec", "specs", "api"] for part in rel_root.parts)
            if is_contract_dir and (f_lower.endswith(".json") or f_lower.endswith(".yaml") or f_lower.endswith(".yml")):
                if any(kw in f_lower for kw in ["api", "spec", "openapi", "swagger"]):
                    if file_path not in specs:
                        specs.append(file_path)

    return specs


def discover_repo_inventory_files(
    repo_root: Path,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Performs an efficient initial scan pass to discover source files, manifests, and specs.
    Returns categorized inventory metadata without expensive AST parsing.
    """
    source_files: List[Path] = []
    manifest_files: List[Path] = []
    test_files: List[Path] = []
    spec_files: List[Path] = []
    languages: Set[str] = set()

    for root, _, files in safe_walk(repo_root, output_dir=output_dir):
        root_path = Path(root)
        rel_root = root_path.relative_to(repo_root)

        for f in files:
            file_path = root_path / f
            f_lower = f.lower()
            ext = file_path.suffix.lower()

            if ext in RELEVANT_EXTENSIONS:
                source_files.append(file_path)

                if ext == ".py":
                    languages.add("Python")
                elif ext in {".js", ".jsx", ".mjs", ".cjs"}:
                    languages.add("JavaScript")
                elif ext in {".ts", ".tsx"}:
                    languages.add("TypeScript")
                elif ext == ".go":
                    languages.add("Go")
                elif ext == ".rs":
                    languages.add("Rust")
                elif ext == ".java":
                    languages.add("Java")
                elif ext == ".rb":
                    languages.add("Ruby")
                elif ext == ".php":
                    languages.add("PHP")

                is_test_dir = any(part in ["tests", "test", "__tests__"] for part in rel_root.parts)
                is_test_file = (
                    f_lower.startswith("test_") or
                    f_lower.endswith("_test.py") or
                    f_lower.endswith(".test.js") or
                    f_lower.endswith(".test.ts") or
                    f_lower.endswith(".spec.js") or
                    f_lower.endswith(".spec.ts")
                )
                if is_test_dir or is_test_file:
                    test_files.append(file_path)

            if f_lower in MANIFEST_FILENAMES or f_lower.startswith("requirements"):
                manifest_files.append(file_path)

            if f_lower in SPEC_FILENAMES and f_lower not in {"openapi.enriched.json", "repository-inventory.json"}:
                spec_files.append(file_path)

    all_eligible = set(source_files + manifest_files + spec_files)
    return {
        "source_files": source_files,
        "manifest_files": manifest_files,
        "test_files": test_files,
        "spec_files": spec_files,
        "languages": sorted(list(languages)),
        "total_files": len(all_eligible),
    }
