"""In-memory Payment repository (v2)."""
from datetime import datetime, timezone
from typing import Dict, Optional
import uuid
from ..schemas.payment import PaymentCreate, PaymentStatus


class PaymentRepository:
    def __init__(self):
        self._data: Dict[int, dict] = {
            1: {
                "id": 1,
                "order_id": 1,
                "amount": "289.49",  # String formatted for decimal precision
                "currency": "USD",
                "payment_method": "credit_card",
                "status": PaymentStatus.completed,
                "transaction_id": "txn_v2_9876543210",
                "created_at": "2026-03-01T10:05:00Z",
            }
        }
        self._next_id = 2

    def get_by_id(self, payment_id: int) -> Optional[dict]:
        return self._data.get(payment_id)

    def get_by_order_id(self, order_id: int) -> Optional[dict]:
        for p in self._data.values():
            if p["order_id"] == order_id:
                return p
        return None

    def create(self, payment_in: PaymentCreate, status: PaymentStatus = PaymentStatus.completed) -> dict:
        pid = self._next_id
        self._next_id += 1
        record = {
            "id": pid,
            "order_id": payment_in.order_id,
            "amount": f"{payment_in.amount:.2f}",  # String format in v2
            "currency": payment_in.currency.upper(),
            "payment_method": payment_in.payment_method,
            "status": status,
            "transaction_id": f"txn_v2_{uuid.uuid4().hex[:12]}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._data[pid] = record
        return record
