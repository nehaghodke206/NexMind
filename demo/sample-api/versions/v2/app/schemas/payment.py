from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class PaymentMethod(str, Enum):
    credit_card = "credit_card"
    debit_card = "debit_card"
    paypal = "paypal"
    # Breaking change: "crypto" enum value removed


class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class PaymentCreate(BaseModel):
    order_id: int = Field(..., gt=0)
    # Breaking change: amount is still required, but new required field 'currency' added
    amount: float = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3, description="ISO-4217 3-letter currency code, e.g. USD")
    payment_method: PaymentMethod = Field(default=PaymentMethod.credit_card)


class PaymentResponse(BaseModel):
    id: int
    order_id: int
    # Breaking change: 'amount' type changed from number (float) to string for currency precision
    amount: str = Field(..., description="Amount formatted as fixed-decimal string")
    currency: str = Field(default="USD", description="Currency code")
    payment_method: PaymentMethod
    status: PaymentStatus
    transaction_id: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)
