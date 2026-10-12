from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class BaselineCreate(BaseModel):
    contract: Dict[str, Any]
    source: str = Field(default="manual", pattern="^(manual|scan|imported)$")
    created_by: Optional[str] = None
    notes: Optional[str] = None


class BaselineResponse(BaseModel):
    id: str
    dependency_id: str
    version: int = Field(..., alias="version")
    contract: Dict[str, Any]
    source: str
    created_by: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProjectBaselineCreate(BaseModel):
    contracts: Dict[str, Any] = Field(default_factory=dict)
    inventory: Dict[str, Any] = Field(default_factory=dict)
    version_tag: Optional[str] = None
    source_scan_id: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    is_promoted: bool = False

    @field_validator("contracts", "inventory", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> Dict[str, Any]:
        return v if isinstance(v, dict) else {}


class ProjectBaselineResponse(BaseModel):
    id: str
    project_id: str
    version_number: int
    version_tag: Optional[str] = None
    contracts: Dict[str, Any] = Field(default_factory=dict)
    inventory: Dict[str, Any] = Field(default_factory=dict)
    source_scan_id: Optional[str] = None
    content_hash: Optional[str] = None
    created_by: Optional[str] = None
    is_active: bool
    is_promoted: bool
    promoted_at: Optional[datetime] = None
    promoted_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("contracts", "inventory", mode="before")
    @classmethod
    def ensure_response_dict(cls, v: Any) -> Dict[str, Any]:
        return v if isinstance(v, dict) else {}

    @computed_field
    @property
    def version(self) -> int:
        return self.version_number

    @computed_field
    @property
    def description(self) -> Optional[str]:
        return self.notes

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProjectBaselineListResponse(BaseModel):
    items: List[ProjectBaselineResponse]
    total: int
    active_baseline: Optional[ProjectBaselineResponse] = None


class ProjectBaselineCompareResponse(BaseModel):
    project_id: str
    base_version: int
    target_version: int
    base_id: str
    target_id: str
    endpoints_added: List[Dict[str, Any]] = Field(default_factory=list)
    endpoints_removed: List[Dict[str, Any]] = Field(default_factory=list)
    endpoints_modified: List[Dict[str, Any]] = Field(default_factory=list)
    contract_diffs: Dict[str, Any] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)
