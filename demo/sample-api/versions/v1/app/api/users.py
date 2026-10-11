"""Users REST API endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from ..schemas.user import UserCreate, UserListResponse, UserResponse, UserRole, UserUpdate
from ..services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])

_shared_user_service = UserService()


def get_user_service() -> UserService:
    return _shared_user_service


@router.get("", response_model=UserListResponse, summary="List users")
def list_users(
    role: Optional[UserRole] = Query(default=None, description="Filter by user role"),
    limit: int = Query(default=10, ge=1, le=100, description="Page limit"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    service: UserService = Depends(get_user_service),
):
    return service.list_users(role=role, limit=limit, offset=offset)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create user")
def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
):
    return service.create_user(payload)


@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID")
def get_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
):
    return service.get_user(user_id)


@router.put("/{user_id}", response_model=UserResponse, summary="Update user")
def update_user(
    user_id: int,
    payload: UserUpdate,
    service: UserService = Depends(get_user_service),
):
    return service.update_user(user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete user")
def delete_user(
    user_id: int,
    service: UserService = Depends(get_user_service),
):
    service.delete_user(user_id)
    return None

