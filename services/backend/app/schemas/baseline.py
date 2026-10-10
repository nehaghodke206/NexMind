from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


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
