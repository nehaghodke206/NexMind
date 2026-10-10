from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, examples=["Checkout Service"])
    description: Optional[str] = Field(default=None)
    repository_url: Optional[str] = Field(default=None)


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    page: int
    page_size: int
    total: int


class ProjectMemberCreate(BaseModel):
    user_id: str
    role: str = Field(default="developer", pattern="^(owner|admin|developer|reviewer)$")
    display_name: Optional[str] = None
    email: Optional[str] = None


class ProjectMemberResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    role: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)
