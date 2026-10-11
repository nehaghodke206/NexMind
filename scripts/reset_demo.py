"""Reset all simulated services to v1 baseline and restore clean demo application code."""

import os
import sys
import httpx

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

ports = [8001, 8002, 8003, 8004]

def reset():
    print("Resetting simulated services...")
    for p in ports:
        try:
            r = httpx.post(f"http://127.0.0.1:{p}/reset", timeout=2.0)
            print(f"  Port {p}: {r.status_code} - {r.json()}")
        except Exception as e:
            print(f"  Port {p}: (Service not currently running or offline: {e})")

    # Restore clean user_service.py
    user_service_path = os.path.join(root_dir, "demo-app", "src", "services", "user_service.py")
    clean_code = '''import httpx


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
'''
    with open(user_service_path, "w", encoding="utf-8") as f:
        f.write(clean_code)
    print("Clean demo application files restored.")


if __name__ == "__main__":
    reset()
