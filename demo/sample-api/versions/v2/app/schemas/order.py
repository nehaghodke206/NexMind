from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class OrderStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


class OrderItemBase(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    unit_price: float = Field(..., gt=0, description="Price per unit at purchase time")

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    user_id: int = Field(..., gt=0)
    items: List[OrderItemCreate] = Field(..., min_length=1)
    notes: Optional[str] = Field(default=None, description="Optional customer notes")


class OrderUpdateStatus(BaseModel):
    status: OrderStatus = Field(..., description="Target status")


class OrderResponse(BaseModel):
    id: int
    user_id: int
    status: OrderStatus
    items: List[OrderItemResponse]
    total_amount: float
    # Non-breaking optional field added
    discount_amount: Optional[float] = Field(default=0.0, description="Promotional discount amount applied")
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    items: List[OrderResponse]
    total: int
