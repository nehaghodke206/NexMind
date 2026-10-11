"""Orders REST API endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from ..schemas.order import OrderCreate, OrderListResponse, OrderResponse, OrderStatus, OrderUpdateStatus
from ..services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])

_shared_order_service = OrderService()


def get_order_service() -> OrderService:
    return _shared_order_service


@router.get("", response_model=OrderListResponse, summary="List orders")
def list_orders(
    status_filter: Optional[OrderStatus] = Query(default=None, alias="status", description="Filter by order status"),
    user_id: Optional[int] = Query(default=None, description="Filter by user ID"),
    service: OrderService = Depends(get_order_service),
):
    return service.list_orders(status=status_filter, user_id=user_id)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, summary="Create order")
def create_order(
    payload: OrderCreate,
    service: OrderService = Depends(get_order_service),
):
    return service.create_order(payload)


@router.get("/{order_id}", response_model=OrderResponse, summary="Get order by ID")
def get_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
):
    return service.get_order(order_id)


@router.patch("/{order_id}/status", response_model=OrderResponse, summary="Update order status")
def update_order_status(
    order_id: int,
    payload: OrderUpdateStatus,
    service: OrderService = Depends(get_order_service),
):
    return service.update_order_status(order_id, payload.status)

