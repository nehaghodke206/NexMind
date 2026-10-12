"""Bridge module exposing centralized settings to Dependency Guardian Detection Agent."""

from pathlib import Path
import sys

# Ensure repository root is on sys.path so agents.common is importable
_repo_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from agents.common.settings import (
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

__all__ = [
    "DEFAULT_BACKEND_BASE_URL",
    "DEFAULT_BACKEND_TIMEOUT_SECONDS",
    "DEFAULT_OLLAMA_BASE_URL",
    "DEFAULT_OLLAMA_MODEL",
    "DEFAULT_OLLAMA_TIMEOUT_SECONDS",
    "DEFAULT_REQUEST_TIMEOUT_SECONDS",
    "Settings",
    "get_settings",
    "normalize_backend_url",
    "normalize_ollama_url",
]
