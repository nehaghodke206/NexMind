"""In-memory User repository."""
from typing import Dict, List, Optional
from ..schemas.user import UserCreate, UserRole, UserUpdate


class UserRepository:
    def __init__(self):
        self._data: Dict[int, dict] = {
            1: {
                "id": 1,
                "username": "alice",
                "email": "alice@example.com",
                "role": UserRole.admin,
                "is_active": True,
            },
            2: {
                "id": 2,
                "username": "bob",
                "email": "bob@example.com",
                "role": UserRole.member,
                "is_active": True,
            },
            3: {
                "id": 3,
                "username": "carol",
                "email": "carol@example.com",
                "role": UserRole.guest,
                "is_active": False,
            },
        }
        self._next_id = 4

    def list(self, role: Optional[UserRole] = None, limit: int = 10, offset: int = 0) -> List[dict]:
        items = list(self._data.values())
        if role:
            items = [u for u in items if u["role"] == role]
        return items[offset : offset + limit]

    def count(self, role: Optional[UserRole] = None) -> int:
        if role:
            return sum(1 for u in self._data.values() if u["role"] == role)
        return len(self._data)

    def get_by_id(self, user_id: int) -> Optional[dict]:
        return self._data.get(user_id)

    def get_by_username(self, username: str) -> Optional[dict]:
        for u in self._data.values():
            if u["username"].lower() == username.lower():
                return u
        return None

    def create(self, user_in: UserCreate) -> dict:
        uid = self._next_id
        self._next_id += 1
        record = {
            "id": uid,
            "username": user_in.username,
            "email": user_in.email,
            "role": user_in.role,
            "is_active": True,
        }
        self._data[uid] = record
        return record

    def update(self, user_id: int, user_in: UserUpdate) -> Optional[dict]:
        user = self._data.get(user_id)
        if not user:
            return None
        if user_in.username is not None:
            user["username"] = user_in.username
        if user_in.email is not None:
            user["email"] = user_in.email
        if user_in.role is not None:
            user["role"] = user_in.role
        if user_in.is_active is not None:
            user["is_active"] = user_in.is_active
        return user

    def delete(self, user_id: int) -> bool:
        if user_id in self._data:
            del self._data[user_id]
            return True
        return False

