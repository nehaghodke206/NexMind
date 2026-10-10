import json
import os
from pathlib import Path
import pytest
from dependency_guardian.config import (
    AIFallbackPolicy,
    DetectionConfig,
    load_configuration,
)
from dependency_guardian.contracts.findings import DetectionMode


def test_default_configuration():
    config = DetectionConfig()
    assert config.detection_mode == DetectionMode.ALGORITHMIC
    assert config.ai_provider is None
    assert config.ai_fallback_policy == AIFallbackPolicy.FAIL
    assert config.ai_timeout_seconds == 30.0
    assert config.logging_level == "INFO"


def test_validate_for_mode_requires_provider_for_ai_and_hybrid():
    # Algorithmic mode doesn't need AI provider
    cfg_algo = DetectionConfig(detection_mode=DetectionMode.ALGORITHMIC)
    cfg_algo.validate_for_mode()  # Should not raise

    # AI mode without provider raises ValueError
    cfg_ai = DetectionConfig(detection_mode=DetectionMode.AI)
    with pytest.raises(ValueError, match="requires 'ai_provider' to be configured"):
        cfg_ai.validate_for_mode()

    # AI mode with provider succeeds
    cfg_ai_valid = DetectionConfig(detection_mode=DetectionMode.AI, ai_provider="mock")
    cfg_ai_valid.validate_for_mode()

    # Hybrid mode without provider raises ValueError
    cfg_hybrid = DetectionConfig(detection_mode=DetectionMode.HYBRID)
    with pytest.raises(ValueError, match="requires 'ai_provider' to be configured"):
        cfg_hybrid.validate_for_mode()

    # Hybrid mode with provider succeeds
    cfg_hybrid_valid = DetectionConfig(detection_mode=DetectionMode.HYBRID, ai_provider="mock")
    cfg_hybrid_valid.validate_for_mode()


def test_to_safe_dict_redacts_api_key():
    config = DetectionConfig(ai_api_key="sk-proj-secret-1234567890abcdef")
    safe = config.to_safe_dict()
    assert "sk-p" in safe["ai_api_key"]
    assert "cdef (redacted)" in safe["ai_api_key"]
    assert "secret" not in safe["ai_api_key"]

    short_config = DetectionConfig(ai_api_key="1234")
    safe_short = short_config.to_safe_dict()
    assert safe_short["ai_api_key"] == "******** (redacted)"


def test_logging_level_validation():
    valid = DetectionConfig(logging_level="debug")
    assert valid.logging_level == "DEBUG"

    warn = DetectionConfig(logging_level="warn")
    assert warn.logging_level == "WARNING"

    with pytest.raises(ValueError, match="Invalid logging_level"):
        DetectionConfig(logging_level="INVALID_LEVEL")


def test_5_level_precedence_hierarchy(tmp_path, monkeypatch):
    # Level 2: User config file
    user_dir = tmp_path / "user_home"
    user_dir.mkdir()
    user_config = user_dir / "config.json"
    user_config.write_text(
        json.dumps({
            "detection_mode": "ai",
            "ai_provider": "user-provider",
            "ai_timeout_seconds": 15.0,
        }),
        encoding="utf-8",
    )

    # Level 3: Workspace config file
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    ws_config = ws_dir / ".dependency-guardian.json"
    ws_config.write_text(
        json.dumps({
            "ai_provider": "workspace-provider",
            "ai_timeout_seconds": 25.0,
        }),
        encoding="utf-8",
    )

    # Verify workspace overrides user config
    cfg1 = load_configuration(
        workspace_dir=ws_dir,
        user_config_path=user_config,
    )
    assert cfg1.detection_mode == DetectionMode.AI  # from user config
    assert cfg1.ai_provider == "workspace-provider"  # workspace overrode user
    assert cfg1.ai_timeout_seconds == 25.0  # workspace overrode user

    # Level 4: Environment variables override workspace and user
    monkeypatch.setenv("DEPENDENCY_GUARDIAN_AI_PROVIDER", "env-provider")
    monkeypatch.setenv("DEPENDENCY_GUARDIAN_DETECTION_MODE", "hybrid")
    cfg2 = load_configuration(
        workspace_dir=ws_dir,
        user_config_path=user_config,
    )
    assert cfg2.detection_mode == DetectionMode.HYBRID  # env overrode user
    assert cfg2.ai_provider == "env-provider"  # env overrode workspace

    # Level 5: CLI overrides override everything
    cli_overrides = {
        "detection_mode": DetectionMode.ALGORITHMIC,
        "ai_provider": "cli-provider",
    }
    cfg3 = load_configuration(
        workspace_dir=ws_dir,
        user_config_path=user_config,
        cli_overrides=cli_overrides,
    )
    assert cfg3.detection_mode == DetectionMode.ALGORITHMIC  # CLI won
    assert cfg3.ai_provider == "cli-provider"  # CLI won

