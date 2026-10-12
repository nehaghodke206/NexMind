import json
from pathlib import Path
import pytest
from dependency_guardian.cli import run

FIXTURES_DIR = Path(__file__).parent / "fixtures"
BASELINE_PATH = str(FIXTURES_DIR / "baseline.json")
PATH_REMOVED_PATH = str(FIXTURES_DIR / "path_removed.json")
IDENTICAL_PATH = str(FIXTURES_DIR / "identical.json")


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exc:
        run(["--help"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "Dependency Guardian Detection Agent CLI" in captured.out


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        run(["--version"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "dependency-guardian 0.1.0" in captured.out


def test_cli_scan_repo_version(capsys):
    with pytest.raises(SystemExit) as exc:
        run(["scan-repo", "--version"])
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "dependency-guardian scan-repo 0.1.0" in captured.out


def test_cli_missing_arguments(capsys):
    ret = run([])
    assert ret == 2
    captured = capsys.readouterr()
    assert "Both baseline and current specification paths are required" in captured.err


def test_cli_identical_specs_json_output(capsys):
    ret = run([BASELINE_PATH, IDENTICAL_PATH, "--format", "json"])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["success"] is True
    assert data["summary"]["total_findings"] == 0
    assert len(data["findings"]) == 0


def test_cli_breaking_changes_with_summary_format(capsys):
    ret = run([BASELINE_PATH, PATH_REMOVED_PATH, "--format", "summary"])
    assert ret == 0
    captured = capsys.readouterr()
    assert "Dependency Guardian Detection Summary" in captured.out
    assert "RULE-PATH-REMOVED" in captured.out
    assert "Breaking:             1" in captured.out


def test_cli_fail_on_breaking_flag(capsys):
    # Without --fail-on-breaking, should return 0
    ret_normal = run([BASELINE_PATH, PATH_REMOVED_PATH, "--quiet"])
    assert ret_normal == 0

    # With --fail-on-breaking, should return 1
    ret_fail = run([BASELINE_PATH, PATH_REMOVED_PATH, "--fail-on-breaking", "--quiet"])
    assert ret_fail == 1


def test_cli_output_to_file(tmp_path):
    out_file = tmp_path / "result.json"
    ret = run([BASELINE_PATH, PATH_REMOVED_PATH, "-o", str(out_file), "--quiet"])
    assert ret == 0
    assert out_file.is_file()

    saved_data = json.loads(out_file.read_text(encoding="utf-8"))
    assert saved_data["success"] is True
    assert saved_data["summary"]["breaking_count"] == 1


def test_cli_mode_and_mock_provider(capsys):
    ret = run([
        BASELINE_PATH,
        PATH_REMOVED_PATH,
        "--mode", "hybrid",
        "--provider", "mock",
        "--model", "test-mock-model",
        "--format", "json",
    ])
    assert ret == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["mode"] == "hybrid"
    assert data["ai_status"] == "completed"


def test_cli_nonexistent_file(capsys):
    ret = run(["nonexistent_baseline.json", IDENTICAL_PATH])
    assert ret == 2
    captured = capsys.readouterr()
    assert "Specification file not found" in captured.err


def test_cli_sync_backend_missing_ids(capsys):
    ret = run([BASELINE_PATH, IDENTICAL_PATH, "--sync-backend"])
    assert ret == 2
    captured = capsys.readouterr()
    assert "Error: Both --project-id and --dependency-id are required for backend synchronization or repair proposals." in captured.err


def test_cli_sync_backend_with_valid_ids(capsys, monkeypatch):
    called = {}

    def mock_sync(self, project_id, dependency_id, result):
        called["project_id"] = project_id
        called["dependency_id"] = dependency_id
        return {
            "synced": True,
            "scan_id": "scan_test_123",
            "observations_count": 0,
            "incidents_created": 0,
            "incident_records": [],
        }

    from dependency_guardian.client.backend import BackendClient
    monkeypatch.setattr(BackendClient, "sync_detection_result", mock_sync)

    ret = run([
        BASELINE_PATH,
        IDENTICAL_PATH,
        "--sync-backend",
        "--project-id", "proj-uuid-123",
        "--dependency-id", "dep-uuid-456",
        "--quiet",
    ])
    assert ret == 0
    assert called["project_id"] == "proj-uuid-123"
    assert called["dependency_id"] == "dep-uuid-456"


def test_cli_sync_backend_with_env_var_ids(capsys, monkeypatch):
    called = {}

    def mock_sync(self, project_id, dependency_id, result):
        called["project_id"] = project_id
        called["dependency_id"] = dependency_id
        return {
            "synced": True,
            "scan_id": "scan_test_456",
            "observations_count": 0,
            "incidents_created": 0,
            "incident_records": [],
        }

    from dependency_guardian.client.backend import BackendClient
    monkeypatch.setattr(BackendClient, "sync_detection_result", mock_sync)
    monkeypatch.setenv("DEPENDENCY_GUARDIAN_PROJECT_ID", "env-proj-789")
    monkeypatch.setenv("DEPENDENCY_GUARDIAN_DEPENDENCY_ID", "env-dep-101")

    ret = run([
        BASELINE_PATH,
        IDENTICAL_PATH,
        "--sync-backend",
        "--quiet",
    ])
    assert ret == 0
    assert called["project_id"] == "env-proj-789"
    assert called["dependency_id"] == "env-dep-101"


