from enum import Enum
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
import yaml
from .contracts.findings import DetectionMode

logger = logging.getLogger("dependency_guardian.config")


class AIFallbackPolicy(str, Enum):
    FAIL = "fail"
    FALLBACK_TO_ALGORITHMIC = "fallback_to_algorithmic"
    NONE = "none"


class DetectionConfig(BaseModel):
    """Canonical configuration model for Dependency Guardian detection."""

    detection_mode: DetectionMode = Field(
        default=DetectionMode.ALGORITHMIC,
        description="Active detection mode: algorithmic, ai, or hybrid.",
    )
    ai_provider: Optional[str] = Field(
        default=None,
        description="Configured AI provider identifier (e.g. 'ollama', 'hosted', 'mock').",
    )
    ai_model: Optional[str] = Field(
        default=None,
        description="Target model name for the AI provider.",
    )
    ai_base_url: Optional[str] = Field(
        default=None,
        description="Endpoint URL for the AI provider.",
    )
    ai_api_key: Optional[str] = Field(
        default=None,
        description="Secret API key for hosted AI providers (redacted in summaries).",
    )
    ai_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Timeout for AI provider calls in seconds.",
    )
    ai_fallback_policy: AIFallbackPolicy = Field(
        default=AIFallbackPolicy.FAIL,
        description="Policy when AI provider fails: 'fail', 'fallback_to_algorithmic', or 'none'.",
    )
    backend_base_url: Optional[str] = Field(
        default=None,
        description="Dependency Guardian FastAPI backend base URL.",
    )
    logging_level: str = Field(
        default="INFO",
        description="Log verbosity level.",
    )

    model_config = ConfigDict(extra="ignore")

    @field_validator("logging_level")
    @classmethod
    def validate_logging_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"Invalid logging_level: '{v}'. Must be one of {valid}")
        return "WARNING" if upper == "WARN" else upper

    def validate_for_mode(self) -> None:
        """Validate that required fields for the active mode are present."""
        if self.detection_mode in (DetectionMode.AI, DetectionMode.HYBRID):
            if not self.ai_provider:
                raise ValueError(
                    f"Detection mode '{self.detection_mode.value}' requires 'ai_provider' to be configured. "
                    f"Please specify an AI provider (e.g. 'ollama', 'hosted') or switch to 'algorithmic' mode."
                )

    def to_safe_dict(self) -> Dict[str, Any]:
        """Return a representation suitable for logging with secrets redacted."""
        data = self.model_dump()
        if data.get("ai_api_key"):
            key = str(data["ai_api_key"])
            if len(key) > 8:
                data["ai_api_key"] = f"{key[:4]}...{key[-4:]} (redacted)"
            else:
                data["ai_api_key"] = "******** (redacted)"
        return data


def _load_file_dict(path: Path) -> Dict[str, Any]:
    """Load configuration from JSON or YAML file if it exists."""
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return {}
        if path.suffix.lower() in (".yaml", ".yml"):
            return yaml.safe_load(text) or {}
        return json.loads(text) or {}
    except Exception as exc:
        logger.warning("Could not read configuration from %s: %s", path, exc)
        return {}


def load_configuration(
    workspace_dir: Optional[Path] = None,
    user_config_path: Optional[Path] = None,
    cli_overrides: Optional[Dict[str, Any]] = None,
) -> DetectionConfig:
    """
    Resolve configuration honoring the strict 5-level precedence hierarchy:
    1. Built-in defaults
    2. User-level configuration (~/.dependency-guardian/config.json or yaml)
    3. Workspace-level configuration (.dependency-guardian.json or yaml)
    4. Environment-variable overrides (DEPENDENCY_GUARDIAN_*)
    5. Explicit CLI overrides for this invocation
    """
    merged: Dict[str, Any] = {}

    # 1. Built-in defaults are provided by DetectionConfig field defaults

    # 2. User-level config
    if user_config_path is None:
        user_home = Path.home() / ".dependency-guardian"
        for candidate in ("config.json", "config.yaml", "config.yml"):
            p = user_home / candidate
            if p.is_file():
                user_config_path = p
                break
    if user_config_path and user_config_path.is_file():
        user_dict = _load_file_dict(user_config_path)
        merged.update({k: v for k, v in user_dict.items() if v is not None})

    # 3. Workspace-level config
    if workspace_dir:
        for candidate in (
            ".dependency-guardian.json",
            ".dependency-guardian.yaml",
            ".dependency-guardian.yml",
        ):
            p = workspace_dir / candidate
            if p.is_file():
                ws_dict = _load_file_dict(p)
                merged.update({k: v for k, v in ws_dict.items() if v is not None})
                break

    # 4. Environment-variable overrides
    env_mappings = {
        "DEPENDENCY_GUARDIAN_DETECTION_MODE": "detection_mode",
        "DEPENDENCY_GUARDIAN_AI_PROVIDER": "ai_provider",
        "DEPENDENCY_GUARDIAN_AI_MODEL": "ai_model",
        "DEPENDENCY_GUARDIAN_AI_BASE_URL": "ai_base_url",
        "DEPENDENCY_GUARDIAN_AI_API_KEY": "ai_api_key",
        "DEPENDENCY_GUARDIAN_AI_TIMEOUT_SECONDS": "ai_timeout_seconds",
        "DEPENDENCY_GUARDIAN_AI_FALLBACK_POLICY": "ai_fallback_policy",
        "DEPENDENCY_GUARDIAN_BACKEND_BASE_URL": "backend_base_url",
        "DEPENDENCY_GUARDIAN_LOGGING_LEVEL": "logging_level",
    }
    for env_var, field_name in env_mappings.items():
        val = os.getenv(env_var)
        if val is not None and val.strip() != "":
            if field_name == "ai_timeout_seconds":
                try:
                    merged[field_name] = float(val)
                except ValueError:
                    pass
            else:
                merged[field_name] = val

    # 5. CLI overrides
    if cli_overrides:
        merged.update({k: v for k, v in cli_overrides.items() if v is not None})

    config = DetectionConfig(**merged)
    return config
