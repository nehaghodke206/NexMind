"""
AI-Generated Regression Test Suite for Dependency Guardian (V2).
STATUS: APPROVED (Generated from detected contract changes).
SAFETY: Validated against AST constraints. No arbitrary shell or filesystem operations.
"""
import pytest
from fastapi.testclient import TestClient
from demo.sample_api.versions.v2.app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_regression_enum_value_removed_api_v1_payments(client):
    """Verify removed enum value 'crypto' causes 422 rejection on v2."""
    payload_removed_enum = {
        "order_id": 1,
        "amount": 289.49,
        "currency": "USD",
        "payment_method": "crypto",
    }
    resp = client.post("/api/v1/payments", json=payload_removed_enum)
    assert resp.status_code == 422, f"Expected 422 for removed enum 'crypto', got {resp.status_code}"


def test_regression_required_request_field_api_v1_payments(client):
    """Verify newly required payload field causes 422 if omitted by legacy client."""
    legacy_payload = {
        "order_id": 1,
        "amount": 289.49,
        "payment_method": "credit_card",
    }
    resp = client.post("/api/v1/payments", json=legacy_payload)
    # Expected outcome on v2: 422 Unprocessable Entity due to missing required 'currency' field
    assert resp.status_code == 422, f"Expected 422 for legacy payload lacking new required field, got {resp.status_code}"


def test_regression_field_type_amount_changed(client):
    """Verify response field 'amount' type is string (decimal format) on v2."""
    resp = client.get("/api/v1/payments/1")
    assert resp.status_code == 200
    data = resp.json()
    # Legacy consumer expecting float/int will encounter type error when parsing
    assert isinstance(data["amount"], str), f"Expected 'amount' to be string in v2, got {type(data['amount'])}"
    assert data["amount"] == "289.49"


def test_regression_path_removed_api_v1_payments__payment_id__receipt(client):
    """Verify removed path '/api/v1/payments/{payment_id}/receipt' returns 404 on v2."""
    test_path = "/api/v1/payments/{payment_id}/receipt".replace("{payment_id}", "1").replace("{user_id}", "1").replace("{product_id}", "1").replace("{order_id}", "1")
    resp = client.get(test_path)
    # Expected regression outcome on v2: removed endpoint returns 404 Not Found
    assert resp.status_code == 404, f"Expected 404 for removed endpoint, got {resp.status_code}"


def test_regression_required_param_store_id_api_v1_products(client):
    """Verify newly required parameter 'store_id' fails when omitted on v2."""
    # Request without required parameter must fail validation (422)
    resp_omitted = client.get("/api/v1/products")
    assert resp_omitted.status_code == 422, f"Expected 422 when omitting 'store_id', got {resp_omitted.status_code}"

    # Request with required parameter must succeed (200)
    resp_provided = client.get("/api/v1/products?store_id=store-main")
    assert resp_provided.status_code == 200, f"Expected 200 when providing 'store_id', got {resp_provided.status_code}"


def test_regression_method_removed_delete_api_v1_products__product_id(client):
    """Verify removed method 'DELETE' on '/api/v1/products/{product_id}' returns 405 on v2."""
    test_path = "/api/v1/products/{product_id}".replace("{product_id}", "1").replace("{user_id}", "1").replace("{order_id}", "1").replace("{payment_id}", "1")
    resp = client.request("DELETE", test_path)
    # Expected regression outcome: 405 Method Not Allowed
    assert resp.status_code == 405, f"Expected 405 for removed HTTP method, got {resp.status_code}"


def test_regression_response_field_stock_removed(client):
    """Verify removed field 'stock' is absent from response on v2."""
    resp = client.get("/api/v1/products/1")
    assert resp.status_code == 200
    data = resp.json()
    # Breaking change assertion: client code asserting 'stock' in response will break
    assert "stock" not in data, "Expected 'stock' field to be removed in v2"
    assert "sku" in data, "Expected new 'sku' field to be present"


def test_regression_optional_param_search_supported(client):
    """Verify optional parameter 'search' works without breaking default listing."""
    resp_all = client.get("/api/v1/users")
    assert resp_all.status_code == 200

    resp_filtered = client.get("/api/v1/users?search=alice")
    assert resp_filtered.status_code == 200
    items = resp_filtered.json()["items"]
    assert len(items) == 1
    assert items[0]["username"] == "alice"
