"""In-memory Payment repository."""
from datetime import datetime, timezone
import uuid
from typing import Dict, Optional
from ..schemas.payment import PaymentCreate, PaymentMethod, PaymentStatus


class PaymentRepository:
    def __init__(self):
        self._data: Dict[int, dict] = {
            1: {
                "id": 1,
                "order_id": 1,
                "amount": 263.99,
                "payment_method": PaymentMethod.credit_card,
                "status": PaymentStatus.completed,
                "transaction_id": "txn_live_99812739",
                "created_at": "2026-10-01T10:01:00Z",
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
        txn_id = f"txn_{uuid.uuid4().hex[:12]}"
        record = {
            "id": pid,
            "order_id": payment_in.order_id,
            "amount": payment_in.amount,
            "payment_method": payment_in.payment_method,
            "status": status,
            "transaction_id": txn_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._data[pid] = record
        return record

