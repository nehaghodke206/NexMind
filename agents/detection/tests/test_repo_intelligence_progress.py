"""
Tests for repository scanning performance, safe traversal, and streaming progress events.
"""
import io
import json
from pathlib import Path
import sys
import tempfile
import pytest

from dependency_guardian.cli import run as run_cli
from dependency_guardian.repo_intelligence.traversal import (
    DEFAULT_IGNORE_DIRS,
    discover_repo_inventory_files,
    find_spec_files,
    get_effective_ignore_dirs,
    safe_walk,
)
from dependency_guardian.repo_intelligence import (
    DependencyScanner,
    EndpointScanner,
    RepositoryIntelligenceScanner,
    TestCoverageScanner,
)

FIXTURE_REPO = Path(__file__).parent / "fixtures" / "fixture_repo"
DEMO_APP = Path(__file__).resolve().parents[3] / "demo-app"


def test_traversal_safe_walk_prunes_ignored_directories_and_output_dir(tmp_path: Path):
    """Verify safe_walk ignores node_modules, .venv, .git, and dynamic output_dir."""
    # Setup directory structure
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("git config")

    (tmp_path / ".venv" / "lib" / "python3.11").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "python3.11" / "site.py").write_text("# site")

    (tmp_path / "node_modules" / "express").mkdir(parents=True)
    (tmp_path / "node_modules" / "express" / "index.js").write_text("// express")

    out_dir = tmp_path / "reports" / "repository-inventory"
    out_dir.mkdir(parents=True)
    (out_dir / "repository-inventory.json").write_text("{}")
    (out_dir / "API_REFERENCE.md").write_text("# API")

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("print('hello')")
    (src_dir / "package.json").write_text('{"name": "test"}')

    visited_files = []
    visited_roots = []

    for root, dirs, files in safe_walk(tmp_path, output_dir=out_dir):
        visited_roots.append(root.relative_to(tmp_path).as_posix())
        for f in files:
            visited_files.append((root / f).relative_to(tmp_path).as_posix())

    # Assert ignored directories are never visited
    assert not any(".git" in r for r in visited_roots)
    assert not any(".venv" in r for r in visited_roots)
    assert not any("node_modules" in r for r in visited_roots)
    assert not any("reports/repository-inventory" in r for r in visited_roots)

    # Assert legitimate files are found
    assert "src/main.py" in visited_files
    assert "src/package.json" in visited_files

    # Assert ignored files are never collected
    assert not any(".venv" in f for f in visited_files)
    assert not any("node_modules" in f for f in visited_files)
    assert not any("reports/repository-inventory" in f for f in visited_files)


def test_find_spec_files_excludes_ignored_directories(tmp_path: Path):
    """Verify find_spec_files only returns specs in valid source trees."""
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "openapi.json").write_text('{"openapi": "3.0.0"}')

    out_dir = tmp_path / "reports"
    out_dir.mkdir()
    (out_dir / "openapi.enriched.json").write_text('{"openapi": "3.0.0"}')

    valid_specs_dir = tmp_path / "specs"
    valid_specs_dir.mkdir()
    (valid_specs_dir / "swagger.yaml").write_text("openapi: 3.0.0")

    found = find_spec_files(tmp_path, output_dir=out_dir)
    assert [p.relative_to(tmp_path).as_posix() for p in found] == ["specs/swagger.yaml"]


def test_discover_repo_inventory_files_fast_precheck(tmp_path: Path):
    """Verify fast discover_repo_inventory_files categorizes files accurately."""
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "hidden.py").write_text("# hidden")

    src = tmp_path / "src"
    src.mkdir()
    (src / "service.py").write_text("def run(): pass")
    (src / "index.ts").write_text("console.log('hi');")
    (tmp_path / "requirements.txt").write_text("requests==2.31.0")

    inv = discover_repo_inventory_files(tmp_path)
    assert inv["total_files"] == 3
    assert any(f.name == "service.py" for f in inv["source_files"])
    assert any(f.name == "index.ts" for f in inv["source_files"])
    assert any(f.name == "requirements.txt" for f in inv["manifest_files"])


def test_scanner_progress_events_emitted_in_order():
    """Verify RepositoryIntelligenceScanner emits ordered structured progress events."""
    events = []

    def on_progress(evt):
        events.append(evt)

    scanner = RepositoryIntelligenceScanner(FIXTURE_REPO, on_progress=on_progress)
    inventory = scanner.scan()

    assert len(events) >= 7

    phases = [e["phase"] for e in events]
    assert "starting" in phases
    assert "discovering_files" in phases
    assert "inspecting_dependencies" in phases
    assert "analyzing_source" in phases
    assert "checking_specifications" in phases
    assert "evaluating_tests" in phases
    assert "completed" in phases

    # Verify event structure
    for e in events:
        assert "phase" in e
        assert "message" in e
        assert isinstance(e["message"], str)

    completed_evt = [e for e in events if e["phase"] == "completed"][-1]
    assert completed_evt.get("endpoints_count") == len(inventory.endpoints)
    assert completed_evt.get("dependencies_count") == len(inventory.dependencies)


def test_cli_scan_repo_streams_json_lines_to_stderr_and_valid_stdout(tmp_path: Path):
    """Verify CLI streams progress JSON lines to stderr while preserving clean stdout JSON."""
    out_dir = tmp_path / "reports" / "inventory"

    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

    try:
        ret = run_cli([
            "scan-repo",
            str(FIXTURE_REPO),
            "--output",
            str(out_dir),
            "--format",
            "json",
            "--mode",
            "algorithmic",
        ])
    finally:
        stdout_val = sys.stdout.getvalue()
        stderr_val = sys.stderr.getvalue()
        sys.stdout, sys.stderr = old_stdout, old_stderr

    assert ret == 0

    # Verify stdout is valid JSON
    parsed_stdout = json.loads(stdout_val)
    assert "metadata" in parsed_stdout
    assert "endpoints" in parsed_stdout
    assert "dependencies" in parsed_stdout

    # Verify stderr received structured JSON lines for progress
    stderr_lines = [l.strip() for l in stderr_val.splitlines() if l.strip()]
    progress_lines = []
    for line in stderr_lines:
        if line.startswith("{") and '"type"' in line and '"progress"' in line:
            data = json.loads(line)
            progress_lines.append(data)

    assert len(progress_lines) >= 6
    phases = [p["phase"] for p in progress_lines]
    assert "starting" in phases
    assert "completed" in phases
    for p in progress_lines:
        assert p["type"] == "progress"
        assert "message" in p


def test_demo_app_scan_completes_quickly_without_hanging(tmp_path: Path):
    """Verify scanner handles demo-app quickly and discovers external integrations."""
    if not DEMO_APP.exists():
        pytest.skip(f"demo-app not found at {DEMO_APP}")

    events = []
    out_dir = tmp_path / "reports" / "repository-inventory"

    scanner = RepositoryIntelligenceScanner(DEMO_APP, on_progress=lambda e: events.append(e))
    inventory = scanner.scan(output_dir=out_dir)

    assert inventory.metadata.total_files_scanned > 0
    # demo-app has external service calls (httpx to user/payment/search)
    assert len(inventory.integrations) > 0
    # Reports should be generated in output directory
    assert (out_dir / "repository-inventory.json").exists()
    assert (out_dir / "API_REFERENCE.md").exists()
    assert (out_dir / "INTEGRATION_MAP.md").exists()
