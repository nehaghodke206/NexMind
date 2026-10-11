import sys
import os

# Ensure demo-app/src is importable
current_dir = os.path.dirname(__file__)
src_dir = os.path.abspath(os.path.join(current_dir, "..", "src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from services.user_service import get_user_profile


def test_user_profile_returns_expected_fields():
    profile = get_user_profile("u_123")
    assert profile["id"] == "u_123"
    assert profile["name"] == "Alice"
    assert profile["email"] == "alice@example.com"
