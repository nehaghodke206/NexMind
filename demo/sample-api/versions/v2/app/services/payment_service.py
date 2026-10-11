"""Payment business logic service (v2)."""
from typing import Optional
from fastapi import HTTPException, status
from ..repositories.order_repository import OrderRepository
from ..repositories.payment_repository import PaymentRepository
from ..schemas.order import OrderStatus
from ..schemas.payment import PaymentCreate, PaymentResponse, PaymentStatus


class PaymentService:
    def __init__(
        self,
        payment_repo: Optional[PaymentRepository] = None,
        order_repo: Optional[OrderRepository] = None,
    ):
        self.payment_repo = payment_repo or PaymentRepository()
        self.order_repo = order_repo or OrderRepository()

    def process_payment(self, payment_in: PaymentCreate) -> PaymentResponse:
        order = self.order_repo.get_by_id(payment_in.order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Order with ID {payment_in.order_id} not found")

        if round(payment_in.amount, 2) < round(order["total_amount"], 2):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Payment amount ${payment_in.amount:.2f} is less than order total ${order['total_amount']:.2f}",
            )

        payment = self.payment_repo.create(payment_in, status=PaymentStatus.completed)
        self.order_repo.update_status(payment_in.order_id, OrderStatus.confirmed)
        return PaymentResponse.model_validate(payment)

    def get_payment(self, payment_id: int) -> PaymentResponse:
        payment = self.payment_repo.get_by_id(payment_id)
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Payment with ID {payment_id} not found")
        return PaymentResponse.model_validate(payment)
