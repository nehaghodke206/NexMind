"""
Fixture FastAPI Service Application.
Demonstrates route decorators, parameter extraction, Pydantic models, auth dependencies,
error cases, and database/external service side effects.
"""
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, Path, Query, status
import httpx
import psycopg2
from pydantic import BaseModel, Field
import redis
import stripe

app = FastAPI(title="Fixture User Service", version="1.0.0")


class UserCreate(BaseModel):
    """Payload to register a new user account."""
    username: str = Field(min_length=3, max_length=50, description="Unique username")
    email: str = Field(description="User primary email address")
    age: Optional[int] = Field(default=None, ge=18, le=120, description="User age in years")
    status: str = Field(default="pending", description="Account status")


class UserResponse(BaseModel):
    """User account response record."""
    id: int = Field(description="Unique user ID")
    username: str = Field(description="User name")
    email: str = Field(description="Email address")
    created_at: str = Field(description="Account creation timestamp")


class OrderCreate(BaseModel):
    """Order placement request schema."""
    item_name: str = Field(min_length=1, description="Item identifier")
    amount: float = Field(gt=0, description="Order total in USD")


def get_current_user() -> str:
    """Security bearer authentication dependency."""
    return "authorized_user"


@app.get("/api/v1/users", response_model=List[UserResponse])
def list_users(
    role: Optional[str] = Query(None, description="Filter users by role"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of items to return"),
):
    """Retrieve paginated list of registered users."""
    return []


@app.post("/api/v1/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    current_user: str = Depends(get_current_user),
):
    """Register a new user in the system."""
    if body.username == "forbidden_admin":
        raise HTTPException(status_code=400, detail="Username already taken")

    # Database side effect
    conn = psycopg2.connect("postgresql://app_user:dummy_password@localhost:5432/app_db")
    cur = conn.cursor()
    cur.execute("INSERT INTO users (username, email) VALUES (%s, %s)", (body.username, body.email))
    conn.commit()

    # Outbound HTTP call to Stripe API
    httpx.post(
        "https://api.stripe.com/v1/customers",
        json={"email": body.email, "name": body.username},
        headers={"Authorization": "Bearer sk_test_51MzFakeKeyForTesting00000000"}
    )

    # Redis message broker publish side effect
    r = redis.Redis(host="localhost", port=6379, db=0)
    r.publish("user_events", f"user_created:{body.username}")

    return UserResponse(
        id=101,
        username=body.username,
        email=body.email,
        created_at="2026-10-11T00:00:00Z"
    )


@app.get("/api/v1/users/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int = Path(..., description="Target user identifier"),
):
    """Fetch single user by unique identifier."""
    if user_id == 999:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user_id,
        username="sample_user",
        email="user@example.com",
        created_at="2026-10-11T00:00:00Z"
    )


@app.post("/api/v1/orders", status_code=201)
def create_order(order: OrderCreate):
    """
    Undocumented route implemented in source code but missing from OpenAPI spec.
    """
    conn = psycopg2.connect("postgresql://app_user:dummy_password@localhost:5432/app_db")
    cur = conn.cursor()
    cur.execute("INSERT INTO orders (item, amount) VALUES (%s, %s)", (order.item_name, order.amount))
    conn.commit()
    return {"order_id": 42, "status": "created"}
