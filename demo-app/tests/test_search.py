import sys
import os

current_dir = os.path.dirname(__file__)
src_dir = os.path.abspath(os.path.join(current_dir, "..", "src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from services.search_service import search_users


def test_search_page_pagination():
    result = search_users(page=1)
    assert "items" in result
    assert len(result["items"]) == 1
    assert result["page"] == 1
    assert result["next_page"] == 2
