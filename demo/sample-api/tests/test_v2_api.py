"""Runtime test suite for Sample API v2 verifying modified behaviors and breaking changes."""
import pytest
from fastapi.testclient import TestClient
from demo.sample_api.versions.v2.app.main import create_app


@pytest.fixture
def client_v2():
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_v2_health(client_v2):
    resp = client_v2.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0.0"
    assert data["service"] == "sample-api"


def test_v2_users_with_search_and_notes(client_v2):
    # 1. Search users (non-breaking optional query param)
    resp = client_v2.get("/api/v1/users?search=alice")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["username"] == "alice"
    # Optional field 'notes' is present in response
    assert "notes" in data["items"][0]
    assert data["items"][0]["notes"] == "System administrator"

    # 2. Search with no matches
    resp = client_v2.get("/api/v1/users?search=nonexistentuser")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_v2_products_breaking_and_non_breaking_changes(client_v2):
    # 1. Breaking: store_id query param is required; calling without it returns 422
    resp_missing_store = client_v2.get("/api/v1/products")
    assert resp_missing_store.status_code == 422

    # Calling with required store_id succeeds
    resp_with_store = client_v2.get("/api/v1/products?store_id=store-main")
    assert resp_with_store.status_code == 200
    products = resp_with_store.json()["items"]
    assert len(products) >= 1

    # 2. Breaking: 'stock' field removed from ProductResponse
    prod = products[0]
    assert "stock" not in prod
    # Non-breaking: 'sku' field present in ProductResponse
    assert "sku" in prod
    assert prod["sku"] is not None

    # 3. Breaking: DELETE method removed on /api/v1/products/{id} -> 405 Method Not Allowed
    resp_del = client_v2.delete("/api/v1/products/1")
    assert resp_del.status_code == 405


def test_v2_payments_breaking_changes(client_v2):
    # 1. Breaking: 'currency' field is required in PaymentCreate; omitting it returns 422
    payload_no_curr = {
        "order_id": 1,
        "amount": 289.49,
        "payment_method": "credit_card",
    }
    resp_fail = client_v2.post("/api/v1/payments", json=payload_no_curr)
    assert resp_fail.status_code == 422

    # 2. Breaking: 'crypto' enum removed from PaymentMethod; submitting it returns 422
    payload_crypto = {
        "order_id": 1,
        "amount": 289.49,
        "currency": "USD",
        "payment_method": "crypto",
    }
    resp_crypto = client_v2.post("/api/v1/payments", json=payload_crypto)
    assert resp_crypto.status_code == 422

    # 3. Valid payment with required currency succeeds
    valid_payload = {
        "order_id": 1,
        "amount": 289.49,
        "currency": "USD",
        "payment_method": "credit_card",
    }
    resp_ok = client_v2.post("/api/v1/payments", json=valid_payload)
    assert resp_ok.status_code == 201
    pay_data = resp_ok.json()

    # 4. Breaking: 'amount' type is now a string, not a float
    assert isinstance(pay_data["amount"], str)
    assert pay_data["amount"] == "289.49"
    assert pay_data["currency"] == "USD"

    # 5. Breaking: path /api/v1/payments/{id}/receipt removed -> 404 Not Found
    resp_receipt = client_v2.get(f"/api/v1/payments/{pay_data['id']}/receipt")
    assert resp_receipt.status_code == 404


def test_v2_orders_with_discount(client_v2):
    # 1. Create order
    order_data = {
        "user_id": 1,
        "items": [
            {"product_id": 1, "quantity": 1},  # $199.99
            {"product_id": 2, "quantity": 1},  # $89.50 -> Total $289.49 -> Discount $15 -> $274.49
        ],
        "notes": "Deliver urgent",
    }
    resp = client_v2.post("/api/v1/orders", json=order_data)
    assert resp.status_code == 201
    order = resp.json()
    assert "discount_amount" in order
    assert order["discount_amount"] == 15.0
    assert order["total_amount"] == 274.49
