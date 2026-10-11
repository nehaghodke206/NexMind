import httpx


def get_user_profile(user_id: str, base_url: str = "http://127.0.0.1:8001") -> dict:
    """Fetch user profile from Users API dependency.
    Expects 'name' and 'email' fields in response.
    """
    response = httpx.get(f"{base_url}/users/{user_id}", timeout=5.0)
    response.raise_for_status()
    data = response.json()
    return {
        "id": data["id"],
        "name": data["name"],
        "email": data["email"],
    }
