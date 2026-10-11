"""Order business logic service (v2)."""
from typing import List, Optional
from fastapi import HTTPException, status
from ..repositories.order_repository import OrderRepository
from ..repositories.product_repository import ProductRepository
from ..repositories.user_repository import UserRepository
from ..schemas.order import OrderCreate, OrderListResponse, OrderResponse, OrderStatus


class OrderService:
    def __init__(
        self,
        order_repo: Optional[OrderRepository] = None,
        product_repo: Optional[ProductRepository] = None,
        user_repo: Optional[UserRepository] = None,
    ):
        self.order_repo = order_repo or OrderRepository()
        self.product_repo = product_repo or ProductRepository()
        self.user_repo = user_repo or UserRepository()

    def list_orders(self, status: Optional[OrderStatus] = None, user_id: Optional[int] = None) -> OrderListResponse:
        items = self.order_repo.list(status=status, user_id=user_id)
        return OrderListResponse(items=[OrderResponse.model_validate(o) for o in items], total=len(items))

    def get_order(self, order_id: int) -> OrderResponse:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order with ID {order_id} not found")
        return OrderResponse.model_validate(order)

    def create_order(self, order_in: OrderCreate) -> OrderResponse:
        user = self.user_repo.get_by_id(order_in.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {order_in.user_id} not found")

        enriched_items: List[dict] = []
        total_amount = 0.0

        for item in order_in.items:
            product = self.product_repo.get_by_id(item.product_id)
            if not product:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with ID {item.product_id} not found")
            if product["stock"] < item.quantity:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficient stock for product '{product['name']}'")

            unit_price = product["price"]
            total_amount += unit_price * item.quantity
            enriched_items.append({
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": unit_price,
            })

        # Apply promotional discount if order exceeds $200
        discount = 15.0 if total_amount >= 200.0 else 0.0
        final_total = max(0.0, total_amount - discount)

        created = self.order_repo.create(
            user_id=order_in.user_id,
            items=enriched_items,
            total_amount=round(final_total, 2),
            notes=order_in.notes,
            discount_amount=discount,
        )
        return OrderResponse.model_validate(created)

    def update_order_status(self, order_id: int, new_status: OrderStatus) -> OrderResponse:
        updated = self.order_repo.update_status(order_id, new_status)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order with ID {order_id} not found")
        return OrderResponse.model_validate(updated)
