import httpx


def search_users(page: int = 1, base_url: str = "http://127.0.0.1:8003") -> dict:
    """Execute search query against Search API dependency.
    Expects classic page-based pagination ('items', 'page', 'next_page').
    """
    response = httpx.get(f"{base_url}/search", params={"page": page}, timeout=5.0)
    response.raise_for_status()
    data = response.json()
    return {
        "items": data["items"],
        "page": data["page"],
        "next_page": data["next_page"],
    }
