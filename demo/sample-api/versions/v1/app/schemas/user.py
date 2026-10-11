from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class UserRole(str, Enum):
    admin = "admin"
    member = "member"
    guest = "guest"


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: str = Field(..., description="User email address")
    role: UserRole = Field(default=UserRole.member, description="Account permission role")


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[str] = Field(default=None)
    role: Optional[UserRole] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


class UserResponse(UserBase):
    id: int = Field(..., description="Unique integer ID")
    is_active: bool = Field(default=True, description="Account active status")

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int

