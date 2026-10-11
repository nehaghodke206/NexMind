from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class PaymentMethod(str, Enum):
    credit_card = "credit_card"
    debit_card = "debit_card"
    paypal = "paypal"
    crypto = "crypto"


class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class PaymentCreate(BaseModel):
    order_id: int = Field(..., gt=0)
    amount: float = Field(..., gt=0)
    payment_method: PaymentMethod = Field(default=PaymentMethod.credit_card)


class PaymentResponse(BaseModel):
    id: int
    order_id: int
    amount: float
    payment_method: PaymentMethod
    status: PaymentStatus
    transaction_id: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class PaymentReceiptResponse(BaseModel):
    receipt_id: str
    payment_id: int
    amount: float
    issued_at: str

    model_config = ConfigDict(from_attributes=True)

