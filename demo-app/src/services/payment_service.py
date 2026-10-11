import httpx


def get_payment_details(payment_id: str, base_url: str = "http://127.0.0.1:8002") -> dict:
    """Fetch payment details from Payments API dependency.
    Requires status == 'paid' for confirmed payment workflows.
    """
    response = httpx.get(f"{base_url}/payments/{payment_id}", timeout=5.0)
    response.raise_for_status()
    data = response.json()
    return {
        "id": data["id"],
        "status": data["status"],
        "amount": data["amount"],
        "is_confirmed": data["status"] == "paid",
    }
