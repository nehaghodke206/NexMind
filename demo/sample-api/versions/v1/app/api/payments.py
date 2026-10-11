"""Payments REST API endpoints."""
from fastapi import APIRouter, Depends, status
from ..schemas.payment import PaymentCreate, PaymentReceiptResponse, PaymentResponse
from ..services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])

_shared_payment_service = PaymentService()


def get_payment_service() -> PaymentService:
    return _shared_payment_service


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED, summary="Process payment")
def process_payment(
    payload: PaymentCreate,
    service: PaymentService = Depends(get_payment_service),
):
    return service.process_payment(payload)


@router.get("/{payment_id}", response_model=PaymentResponse, summary="Get payment status")
def get_payment(
    payment_id: int,
    service: PaymentService = Depends(get_payment_service),
):
    return service.get_payment(payment_id)


@router.get("/{payment_id}/receipt", response_model=PaymentReceiptResponse, summary="Get payment receipt")
def get_payment_receipt(
    payment_id: int,
    service: PaymentService = Depends(get_payment_service),
):
    return service.get_receipt(payment_id)

