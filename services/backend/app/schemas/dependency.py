from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class DependencyBase(BaseModel):
    name: str = Field(..., min_length=1, examples=["users-service"])
    kind: str = Field(default="rest_api", pattern="^(rest_api|sdk|package|mcp_tool|other)$")
    base_url: Optional[str] = None
    version: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = Field(default_factory=dict)


class DependencyCreate(DependencyBase):
    pass


class DependencyUpdate(BaseModel):
    name: Optional[str] = None
    kind: Optional[str] = Field(default=None, pattern="^(rest_api|sdk|package|mcp_tool|other)$")
    base_url: Optional[str] = None
    version: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None


class DependencyResponse(BaseModel):
    id: str
    project_id: str
    name: str
    kind: str
    base_url: Optional[str] = None
    version: Optional[str] = None
    configuration: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
