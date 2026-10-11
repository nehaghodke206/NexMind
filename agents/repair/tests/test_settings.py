from pathlib import Path
import pytest
from repair_agent.backend_client import RepairBackendClient
from repair_agent.models import FindingInput, RepairRequest
from repair_agent.ollama_client import OllamaRepairClient
from repair_agent.settings import (
    DEFAULT_BACKEND_BASE_URL,
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    Settings,
    get_settings,
    normalize_backend_url,
    normalize_ollama_url,
)


def test_repair_settings_defaults():
    """Verify Repair Agent sees canonical shared defaults."""
    settings = Settings.load(environ={})
    assert settings.backend_base_url == "http://127.0.0.1:8000/api/v1"
    assert settings.backend_timeout_seconds == 10.0
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_model == "qwen2.5-coder:3b"
    assert settings.ollama_timeout_seconds == 30.0


def test_repair_backend_client_uses_shared_settings(monkeypatch):
    """Verify RepairBackendClient picks up centralized settings when arguments omitted."""
    monkeypatch.setenv("BACKEND_BASE_URL", "http://custom-repair-backend:8000")
    monkeypatch.setenv("BACKEND_TIMEOUT_SECONDS", "14.5")
    get_settings(reload=True)

    client_default = RepairBackendClient()
    assert client_default.base_url == "http://custom-repair-backend:8000/api/v1"
    assert client_default.timeout == 14.5

    client_override = RepairBackendClient(base_url="http://override:9999", timeout=3.0)
    assert client_override.base_url == "http://override:9999/api/v1"
    assert client_override.timeout == 3.0

    monkeypatch.delenv("BACKEND_BASE_URL", raising=False)
    monkeypatch.delenv("BACKEND_TIMEOUT_SECONDS", raising=False)
    get_settings(reload=True)


def test_repair_ollama_client_uses_shared_settings(monkeypatch):
    """Verify OllamaRepairClient picks up centralized settings when arguments omitted."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama-repair-host:11434/")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "42.0")
    get_settings(reload=True)

    ollama_default = OllamaRepairClient()
    assert ollama_default.base_url == "http://ollama-repair-host:11434"
    assert ollama_default.model == "qwen2.5-coder:7b"
    assert ollama_default.timeout == 42.0

    ollama_override = OllamaRepairClient(
        base_url="http://explicit-ollama:11434",
        model="llama3:8b",
        timeout=10.0,
    )
    assert ollama_override.base_url == "http://explicit-ollama:11434"
    assert ollama_override.model == "llama3:8b"
    assert ollama_override.timeout == 10.0

    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_TIMEOUT_SECONDS", raising=False)
    get_settings(reload=True)


def test_repair_request_model_defaults_to_shared_settings(monkeypatch):
    """Verify RepairRequest model defaults to configured OLLAMA_MODEL and OLLAMA_BASE_URL."""
    monkeypatch.setenv("OLLAMA_MODEL", "custom-model:3b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom-ollama:11434")
    get_settings(reload=True)

    finding = FindingInput(id="find_001", path="/users", rule_id="RULE_001", target_file="service.py")
    req = RepairRequest(finding=finding)

    assert req.model == "custom-model:3b"
    assert req.base_url == "http://custom-ollama:11434"

    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    get_settings(reload=True)
