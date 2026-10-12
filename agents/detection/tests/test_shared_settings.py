from pathlib import Path
import pytest
from dependency_guardian.client.backend import BackendClient
from dependency_guardian.settings import (
    DEFAULT_BACKEND_BASE_URL,
    DEFAULT_BACKEND_TIMEOUT_SECONDS,
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_TIMEOUT_SECONDS,
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    Settings,
    get_settings,
    normalize_backend_url,
    normalize_ollama_url,
)


def test_shared_settings_defaults():
    """Verify built-in default values match canonical configuration."""
    settings = Settings.load(environ={})
    assert settings.backend_base_url == "http://127.0.0.1:8000/api/v1"
    assert settings.backend_timeout_seconds == 10.0
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_model == "qwen2.5-coder:3b"
    assert settings.ollama_timeout_seconds == 30.0
    assert settings.request_timeout_seconds == 10.0


def test_shared_settings_environment_overrides(monkeypatch):
    """Verify environment variables override defaults."""
    env = {
        "BACKEND_BASE_URL": "http://production-host:8080",
        "BACKEND_TIMEOUT_SECONDS": "20.5",
        "OLLAMA_BASE_URL": "http://ollama-cluster:11434/",
        "OLLAMA_MODEL": "codellama:7b",
        "OLLAMA_TIMEOUT_SECONDS": "45.0",
        "REQUEST_TIMEOUT_SECONDS": "15.0",
    }
    settings = Settings.load(environ=env)
    assert settings.backend_base_url == "http://production-host:8080/api/v1"
    assert settings.backend_timeout_seconds == 20.5
    assert settings.ollama_base_url == "http://ollama-cluster:11434"
    assert settings.ollama_model == "codellama:7b"
    assert settings.ollama_timeout_seconds == 45.0
    assert settings.request_timeout_seconds == 15.0


def test_shared_settings_legacy_env_fallbacks():
    """Verify legacy DEPENDENCY_GUARDIAN_* env vars remain supported."""
    env = {
        "DEPENDENCY_GUARDIAN_BACKEND_BASE_URL": "http://legacy-host:9000",
        "DEPENDENCY_GUARDIAN_AI_BASE_URL": "http://legacy-ai:11434",
        "DEPENDENCY_GUARDIAN_AI_MODEL": "mistral:instruct",
        "DEPENDENCY_GUARDIAN_AI_TIMEOUT_SECONDS": "60.0",
    }
    settings = Settings.load(environ=env)
    assert settings.backend_base_url == "http://legacy-host:9000/api/v1"
    assert settings.ollama_base_url == "http://legacy-ai:11434"
    assert settings.ollama_model == "mistral:instruct"
    assert settings.ollama_timeout_seconds == 60.0


def test_shared_settings_dotenv_loading(tmp_path):
    """Verify loading from .env file when OS env vars are absent."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "BACKEND_BASE_URL=http://staging-api:8000/api/v1\n"
        "OLLAMA_MODEL=deepseek-coder:6.7b\n"
        "BACKEND_TIMEOUT_SECONDS=25.0\n",
        encoding="utf-8",
    )
    settings = Settings.load(env_file=env_file, environ={})
    assert settings.backend_base_url == "http://staging-api:8000/api/v1"
    assert settings.ollama_model == "deepseek-coder:6.7b"
    assert settings.backend_timeout_seconds == 25.0


def test_shared_settings_os_env_precedence_over_dotenv(tmp_path):
    """Verify OS environment variables take precedence over .env file values."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "BACKEND_BASE_URL=http://file-host:8000\n"
        "OLLAMA_MODEL=file-model\n",
        encoding="utf-8",
    )
    os_env = {
        "BACKEND_BASE_URL": "http://os-host:9000",
    }
    settings = Settings.load(env_file=env_file, environ=os_env)
    assert settings.backend_base_url == "http://os-host:9000/api/v1"
    assert settings.ollama_model == "file-model"


def test_url_normalization():
    """Verify normalization handles slashes, missing /api/v1, and /health."""
    assert normalize_backend_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000/api/v1"
    assert normalize_backend_url("http://127.0.0.1:8000/") == "http://127.0.0.1:8000/api/v1"
    assert normalize_backend_url("http://127.0.0.1:8000/api/v1") == "http://127.0.0.1:8000/api/v1"
    assert normalize_backend_url("http://127.0.0.1:8000/api/v1/") == "http://127.0.0.1:8000/api/v1"
    assert normalize_backend_url("http://127.0.0.1:8000/health") == "http://127.0.0.1:8000/health"
    assert normalize_backend_url(None) == "http://127.0.0.1:8000/api/v1"

    assert normalize_ollama_url("http://localhost:11434/") == "http://localhost:11434"
    assert normalize_ollama_url("http://localhost:11434") == "http://localhost:11434"
    assert normalize_ollama_url(None) == "http://localhost:11434"


def test_detection_backend_client_uses_shared_settings(monkeypatch):
    """Verify Detection BackendClient adopts shared settings by default and respects overrides."""
    monkeypatch.setenv("BACKEND_BASE_URL", "http://configured-backend:8000")
    monkeypatch.setenv("BACKEND_TIMEOUT_SECONDS", "18.0")
    get_settings(reload=True)

    client_default = BackendClient()
    assert client_default.base_url == "http://configured-backend:8000/api/v1"
    assert client_default.timeout == 18.0

    client_override = BackendClient(base_url="http://explicit-backend:9000", timeout=5.0)
    assert client_override.base_url == "http://explicit-backend:9000/api/v1"
    assert client_override.timeout == 5.0

    # Reset cache
    monkeypatch.delenv("BACKEND_BASE_URL", raising=False)
    monkeypatch.delenv("BACKEND_TIMEOUT_SECONDS", raising=False)
    get_settings(reload=True)
