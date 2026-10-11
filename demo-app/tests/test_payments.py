import sys
import os

current_dir = os.path.dirname(__file__)
src_dir = os.path.abspath(os.path.join(current_dir, "..", "src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from services.payment_service import get_payment_details


def test_payment_status_confirmed():
    payment = get_payment_details("p_123")
    assert payment["id"] == "p_123"
    assert payment["status"] == "paid"
    assert payment["amount"] == 100
    assert payment["is_confirmed"] is True
