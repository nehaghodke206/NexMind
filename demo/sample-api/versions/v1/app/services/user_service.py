"""User business logic service."""
from typing import Optional
from fastapi import HTTPException, status
from ..repositories.user_repository import UserRepository
from ..schemas.user import UserCreate, UserListResponse, UserResponse, UserRole, UserUpdate


class UserService:
    def __init__(self, repo: Optional[UserRepository] = None):
        self.repo = repo or UserRepository()

    def list_users(self, role: Optional[UserRole] = None, limit: int = 10, offset: int = 0) -> UserListResponse:
        items = self.repo.list(role=role, limit=limit, offset=offset)
        total = self.repo.count(role=role)
        return UserListResponse(items=[UserResponse.model_validate(u) for u in items], total=total)

    def get_user(self, user_id: int) -> UserResponse:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found")
        return UserResponse.model_validate(user)

    def create_user(self, user_in: UserCreate) -> UserResponse:
        existing = self.repo.get_by_username(user_in.username)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Username '{user_in.username}' already registered")
        created = self.repo.create(user_in)
        return UserResponse.model_validate(created)

    def update_user(self, user_id: int, user_in: UserUpdate) -> UserResponse:
        updated = self.repo.update(user_id, user_in)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found")
        return UserResponse.model_validate(updated)

    def delete_user(self, user_id: int) -> None:
        deleted = self.repo.delete(user_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found")

