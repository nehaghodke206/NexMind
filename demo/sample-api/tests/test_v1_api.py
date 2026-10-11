"""Runtime test suite for Sample API v1."""
import pytest
from fastapi.testclient import TestClient
from demo.sample_api.versions.v1.app.main import create_app


@pytest.fixture
def client_v1():
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_v1_health(client_v1):
    resp = client_v1.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert data["service"] == "sample-api"


def test_v1_users_crud_and_validation(client_v1):
    # 1. List users
    resp = client_v1.get("/api/v1/users")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3
    assert len(data["items"]) >= 3

    # 2. Filter by role
    resp = client_v1.get("/api/v1/users?role=admin")
    assert resp.status_code == 200
    data = resp.json()
    assert all(u["role"] == "admin" for u in data["items"])

    # 3. Create user
    new_user = {
        "username": "dnyaneshwar",
        "email": "dnyaneshwar@example.com",
        "role": "member",
    }
    resp = client_v1.post("/api/v1/users", json=new_user)
    assert resp.status_code == 201
    created = resp.json()
    assert created["username"] == "dnyaneshwar"
    assert created["id"] > 0
    assert created["is_active"] is True

    # 4. Duplicate username rejected
    resp = client_v1.post("/api/v1/users", json=new_user)
    assert resp.status_code == 400

    # 5. Get user by ID
    uid = created["id"]
    resp = client_v1.get(f"/api/v1/users/{uid}")
    assert resp.status_code == 200
    assert resp.json()["username"] == "dnyaneshwar"

    # 6. Update user
    resp = client_v1.put(f"/api/v1/users/{uid}", json={"email": "updated@example.com"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "updated@example.com"

    # 7. Delete user
    resp = client_v1.delete(f"/api/v1/users/{uid}")
    assert resp.status_code == 204

    # 8. Not found after delete
    resp = client_v1.get(f"/api/v1/users/{uid}")
    assert resp.status_code == 404


def test_v1_products_crud_and_filtering(client_v1):
    # 1. List products
    resp = client_v1.get("/api/v1/products")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3

    # 2. Filter products
    resp = client_v1.get("/api/v1/products?category=electronics&min_price=100")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert items[0]["category"] == "electronics"
    assert items[0]["price"] >= 100

    # 3. Create product
    new_prod = {
        "name": "Mechanical Keyboard",
        "description": "RGB mechanical keyboard",
        "price": 129.99,
        "category": "electronics",
        "stock": 15,
    }
    resp = client_v1.post("/api/v1/products", json=new_prod)
    assert resp.status_code == 201
    created = resp.json()
    pid = created["id"]
    assert created["stock"] == 15
    assert created["price"] == 129.99

    # 4. Get product
    resp = client_v1.get(f"/api/v1/products/{pid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Mechanical Keyboard"

    # 5. Update product
    resp = client_v1.put(f"/api/v1/products/{pid}", json={"price": 119.99, "stock": 12})
    assert resp.status_code == 200
    assert resp.json()["price"] == 119.99
    assert resp.json()["stock"] == 12

    # 6. Delete product
    resp = client_v1.delete(f"/api/v1/products/{pid}")
    assert resp.status_code == 204

    # 7. Non-existent product
    resp = client_v1.get(f"/api/v1/products/{pid}")
    assert resp.status_code == 404


def test_v1_orders_and_validation(client_v1):
    # 1. Create order
    order_data = {
        "user_id": 1,
        "items": [
            {"product_id": 1, "quantity": 1},
            {"product_id": 2, "quantity": 2},
        ],
        "notes": "Deliver during weekdays",
    }
    resp = client_v1.post("/api/v1/orders", json=order_data)
    assert resp.status_code == 201
    order = resp.json()
    oid = order["id"]
    assert order["user_id"] == 1
    assert order["status"] == "pending"
    assert len(order["items"]) == 2
    assert order["total_amount"] > 0

    # 2. Non-existent product in order returns 404
    invalid_order = {
        "user_id": 1,
        "items": [{"product_id": 9999, "quantity": 1}],
    }
    resp = client_v1.post("/api/v1/orders", json=invalid_order)
    assert resp.status_code == 404

    # 3. Insufficient stock returns 400
    excess_order = {
        "user_id": 1,
        "items": [{"product_id": 1, "quantity": 99999}],
    }
    resp = client_v1.post("/api/v1/orders", json=excess_order)
    assert resp.status_code == 400

    # 4. Get order
    resp = client_v1.get(f"/api/v1/orders/{oid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == oid

    # 5. Update order status
    resp = client_v1.patch(f"/api/v1/orders/{oid}/status", json={"status": "confirmed"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

    # 6. List orders with filter
    resp = client_v1.get("/api/v1/orders?status=confirmed")
    assert resp.status_code == 200
    assert any(o["id"] == oid for o in resp.json()["items"])


def test_v1_payments_flow(client_v1):
    # 1. Successful payment for existing order
    payment_payload = {
        "order_id": 1,
        "amount": 289.49,
        "payment_method": "credit_card",
    }
    resp = client_v1.post("/api/v1/payments", json=payment_payload)
    assert resp.status_code == 201
    payment = resp.json()
    pay_id = payment["id"]
    assert payment["order_id"] == 1
    assert payment["status"] == "completed"
    assert payment["payment_method"] == "credit_card"
    assert payment["amount"] == 289.49
    assert "transaction_id" in payment

    # 2. Payment for non-existent order returns 404
    bad_payload = {
        "order_id": 9999,
        "amount": 10.0,
        "payment_method": "credit_card",
    }
    resp = client_v1.post("/api/v1/payments", json=bad_payload)
    assert resp.status_code == 404

    # 3. Insufficient payment amount returns 402
    underpay_payload = {
        "order_id": 1,
        "amount": 1.0,
        "payment_method": "credit_card",
    }
    resp = client_v1.post("/api/v1/payments", json=underpay_payload)
    assert resp.status_code == 402

    # 3. Get payment status
    resp = client_v1.get(f"/api/v1/payments/{pay_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == pay_id

    # 4. Get payment receipt
    resp = client_v1.get(f"/api/v1/payments/{pay_id}/receipt")
    assert resp.status_code == 200
    receipt = resp.json()
    assert receipt["payment_id"] == pay_id
    assert receipt["amount"] == 289.49
    assert "receipt_id" in receipt
