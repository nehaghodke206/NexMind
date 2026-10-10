from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str = Field(..., examples=["not_found"])
    message: str = Field(..., examples=["Resource was not found"])
    details: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
