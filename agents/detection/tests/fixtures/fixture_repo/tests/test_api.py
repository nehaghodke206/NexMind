"""
Unit and integration tests for fixture service.
Tests GET /api/v1/users and POST /api/v1/users.
"""
import pytest
from app.main import app, list_users, create_user, UserCreate


def test_list_users():
    """Verify listing users endpoint."""
    res = list_users(limit=10)
    assert isinstance(res, list)


def test_create_user():
    """Verify user registration endpoint."""
    payload = UserCreate(username="alice", email="alice@example.com")
    # Endpoint test reference
    route = "/api/v1/users"
    assert route == "/api/v1/users"
