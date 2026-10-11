"""In-memory Order repository."""
from datetime import datetime, timezone
from typing import Dict, List, Optional
from ..schemas.order import OrderCreate, OrderStatus


class OrderRepository:
    def __init__(self):
        self._data: Dict[int, dict] = {
            1: {
                "id": 1,
                "user_id": 1,
                "status": OrderStatus.delivered,
                "items": [
                    {"product_id": 1, "quantity": 1, "unit_price": 199.99},
                    {"product_id": 3, "quantity": 2, "unit_price": 32.00},
                ],
                "total_amount": 263.99,
                "created_at": "2026-10-01T10:00:00Z",
            },
            2: {
                "id": 2,
                "user_id": 2,
                "status": OrderStatus.pending,
                "items": [
                    {"product_id": 2, "quantity": 1, "unit_price": 89.50},
                ],
                "total_amount": 89.50,
                "created_at": "2026-10-10T15:30:00Z",
            },
        }
        self._next_id = 3

    def list(self, status: Optional[OrderStatus] = None, user_id: Optional[int] = None) -> List[dict]:
        items = list(self._data.values())
        if status:
            items = [o for o in items if o["status"] == status]
        if user_id:
            items = [o for o in items if o["user_id"] == user_id]
        return items

    def get_by_id(self, order_id: int) -> Optional[dict]:
        return self._data.get(order_id)

    def create(self, order_in: OrderCreate, enriched_items: List[dict], total_amount: float) -> dict:
        oid = self._next_id
        self._next_id += 1
        record = {
            "id": oid,
            "user_id": order_in.user_id,
            "status": OrderStatus.pending,
            "items": enriched_items,
            "total_amount": round(total_amount, 2),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._data[oid] = record
        return record

    def update_status(self, order_id: int, status: OrderStatus) -> Optional[dict]:
        order = self._data.get(order_id)
        if not order:
            return None
        order["status"] = status
        return order

