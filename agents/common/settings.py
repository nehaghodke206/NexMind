"""Centralized environment configuration for Dependency Guardian.

Provides shared settings across Detection and Repair agents for:
- BACKEND_BASE_URL and request timeouts
- OLLAMA_BASE_URL and OLLAMA_MODEL
- .env file discovery and environment variable overrides
"""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000/api/v1"
DEFAULT_BACKEND_TIMEOUT_SECONDS = 10.0
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:3b"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 30.0
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10.0


def normalize_backend_url(raw_url: Optional[str]) -> str:
    """Normalize backend API base URL to ensure valid /api/v1 endpoint."""
    url = (raw_url or DEFAULT_BACKEND_BASE_URL).strip().rstrip("/")
    if not url.endswith("/api/v1") and not url.endswith("/health"):
        url = f"{url}/api/v1"
    return url


def normalize_ollama_url(raw_url: Optional[str]) -> str:
    """Normalize local Ollama base URL by stripping trailing slashes."""
    url = (raw_url or DEFAULT_OLLAMA_BASE_URL).strip().rstrip("/")
    return url


def _parse_simple_env(file_path: Path) -> Dict[str, str]:
    """Fallback simple .env line parser when python-dotenv is unavailable."""
    result: Dict[str, str] = {}
    if not file_path.is_file():
        return result
    try:
        content = file_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                result[k] = v
    except Exception:
        pass
    return result


def _find_env_file() -> Optional[Path]:
    """Discover .env file in cwd or repository root."""
    cwd_env = Path.cwd() / ".env"
    if cwd_env.is_file():
        return cwd_env

    # Search upward from this file location to locate repository root
    current = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = current / ".env"
        if candidate.is_file():
            return candidate
        if (current / ".git").exists() or (current / "dependency-guardian.yml").exists():
            break
        current = current.parent
    return None


@dataclass(frozen=True)
class Settings:
    """Canonical immutable configuration settings shared across agents."""

    backend_base_url: str = DEFAULT_BACKEND_BASE_URL
    backend_timeout_seconds: float = DEFAULT_BACKEND_TIMEOUT_SECONDS
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL
    ollama_model: str = DEFAULT_OLLAMA_MODEL
    ollama_timeout_seconds: float = DEFAULT_OLLAMA_TIMEOUT_SECONDS
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS

    @classmethod
    def load(
        cls,
        env_file: Optional[Union[str, Path]] = None,
        environ: Optional[Dict[str, str]] = None,
    ) -> "Settings":
        """Load settings from environment variables and optional .env file."""
        env_dict = environ if environ is not None else dict(os.environ)

        # Load values from .env file if available
        file_vals: Dict[str, str] = {}
        target_env = Path(env_file) if env_file else _find_env_file()
        if target_env and target_env.is_file():
            try:
                import dotenv
                file_vals = {
                    k: v
                    for k, v in dotenv.dotenv_values(target_env).items()
                    if v is not None
                }
            except ImportError:
                file_vals = _parse_simple_env(target_env)

        def _get_val(*keys: str, default: Any) -> Any:
            for k in keys:
                if k in env_dict and env_dict[k].strip() != "":
                    return env_dict[k].strip()
            for k in keys:
                if k in file_vals and file_vals[k].strip() != "":
                    return file_vals[k].strip()
            return default

        # 1. Backend URL
        raw_backend = _get_val(
            "BACKEND_BASE_URL",
            "DEPENDENCY_GUARDIAN_BACKEND_BASE_URL",
            default=DEFAULT_BACKEND_BASE_URL,
        )
        backend_url = normalize_backend_url(raw_backend)

        # 2. General / Backend Timeout
        general_timeout_str = _get_val(
            "REQUEST_TIMEOUT_SECONDS",
            default=str(DEFAULT_REQUEST_TIMEOUT_SECONDS),
        )
        try:
            req_timeout = float(general_timeout_str)
        except (ValueError, TypeError):
            req_timeout = DEFAULT_REQUEST_TIMEOUT_SECONDS

        backend_timeout_str = _get_val(
            "BACKEND_TIMEOUT_SECONDS",
            "DEPENDENCY_GUARDIAN_BACKEND_TIMEOUT_SECONDS",
            default=str(req_timeout),
        )
        try:
            backend_timeout = float(backend_timeout_str)
        except (ValueError, TypeError):
            backend_timeout = req_timeout

        # 3. Ollama URL
        raw_ollama_url = _get_val(
            "OLLAMA_BASE_URL",
            "DEPENDENCY_GUARDIAN_AI_BASE_URL",
            "DEPENDENCY_GUARDIAN_OLLAMA_BASE_URL",
            default=DEFAULT_OLLAMA_BASE_URL,
        )
        ollama_url = normalize_ollama_url(raw_ollama_url)

        # 4. Ollama Model
        ollama_model = _get_val(
            "OLLAMA_MODEL",
            "DEPENDENCY_GUARDIAN_AI_MODEL",
            "DEPENDENCY_GUARDIAN_OLLAMA_MODEL",
            default=DEFAULT_OLLAMA_MODEL,
        )

        # 5. Ollama Timeout
        ollama_timeout_str = _get_val(
            "OLLAMA_TIMEOUT_SECONDS",
            "DEPENDENCY_GUARDIAN_AI_TIMEOUT_SECONDS",
            default=str(DEFAULT_OLLAMA_TIMEOUT_SECONDS),
        )
        try:
            ollama_timeout = float(ollama_timeout_str)
        except (ValueError, TypeError):
            ollama_timeout = DEFAULT_OLLAMA_TIMEOUT_SECONDS

        return cls(
            backend_base_url=backend_url,
            backend_timeout_seconds=backend_timeout,
            ollama_base_url=ollama_url,
            ollama_model=ollama_model,
            ollama_timeout_seconds=ollama_timeout,
            request_timeout_seconds=req_timeout,
        )


_cached_settings: Optional[Settings] = None


def get_settings(
    env_file: Optional[Union[str, Path]] = None,
    reload: bool = False,
) -> Settings:
    """Return globally cached shared Settings instance."""
    global _cached_settings
    if _cached_settings is None or reload or env_file is not None:
        loaded = Settings.load(env_file=env_file)
        if env_file is None:
            _cached_settings = loaded
        return loaded
    return _cached_settings
