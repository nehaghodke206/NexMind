"""Configuration loader and validator for dependency-guardian.yml."""

import os
from typing import List, Optional, Dict, Any
import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class ProbeConfig(BaseModel):
    id: str
    method: str = "GET"
    path: str
    expected_contract: Optional[str] = None
    known_values: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"}
        v_upper = v.upper()
        if v_upper not in valid_methods:
            raise ValueError(f"Unsupported HTTP method: '{v}'. Must be one of {valid_methods}")
        return v_upper


class DependencyConfig(BaseModel):
    id: str
    name: str
    base_url: str
    probes: List[ProbeConfig] = Field(default_factory=list)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(f"Invalid base_url: '{v}'. Must start with http:// or https://")
        return v.rstrip("/")

    @model_validator(mode="after")
    def validate_probe_ids(self) -> "DependencyConfig":
        probe_ids = set()
        for probe in self.probes:
            if probe.id in probe_ids:
                raise ValueError(f"Duplicate probe id '{probe.id}' found in dependency '{self.id}'")
            probe_ids.add(probe.id)
        return self


class WorkflowConfig(BaseModel):
    id: str
    name: str
    dependencies: List[str] = Field(default_factory=list)
    source_files: List[str] = Field(default_factory=list)
    fields: List[str] = Field(default_factory=list)
    tests: List[str] = Field(default_factory=list)


class SettingsConfig(BaseModel):
    request_timeout_seconds: float = 3.0
    scan_timeout_seconds: float = 10.0
    max_response_bytes: int = 1_000_000
    allow_private_network_targets: bool = True
    llm_explanations_enabled: bool = False


class ProjectConfig(BaseModel):
    name: str
    validation_command: str = "pytest -q demo-app/tests"


class GuardianConfig(BaseModel):
    project: ProjectConfig
    settings: SettingsConfig = Field(default_factory=SettingsConfig)
    dependencies: List[DependencyConfig] = Field(default_factory=list)
    workflows: List[WorkflowConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_relationships(self) -> "GuardianConfig":
        dep_ids = set()
        for dep in self.dependencies:
            if dep.id in dep_ids:
                raise ValueError(f"Duplicate dependency id '{dep.id}' detected")
            dep_ids.add(dep.id)

        wf_ids = set()
        for wf in self.workflows:
            if wf.id in wf_ids:
                raise ValueError(f"Duplicate workflow id '{wf.id}' detected")
            wf_ids.add(wf.id)
            for d in wf.dependencies:
                if d not in dep_ids:
                    raise ValueError(f"Workflow '{wf.id}' references unknown dependency '{d}'")

        return self


def load_guardian_config(config_path: str) -> GuardianConfig:
    """Loads and validates configuration from the specified YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        try:
            raw_data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise ValueError(f"YAML parsing error in {config_path}: {exc}") from exc

    if not isinstance(raw_data, dict):
        raise ValueError(f"Configuration in {config_path} must be a valid mapping dictionary.")

    return GuardianConfig(**raw_data)
