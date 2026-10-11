from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProductCategory(str, Enum):
    electronics = "electronics"
    apparel = "apparel"
    home = "home"
    books = "books"


class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    price: float = Field(..., gt=0, description="Price in USD")
    category: ProductCategory = Field(default=ProductCategory.electronics)


class ProductCreate(ProductBase):
    stock: int = Field(default=0, ge=0)
    sku: Optional[str] = Field(default=None, max_length=30)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    price: Optional[float] = Field(default=None, gt=0)
    category: Optional[ProductCategory] = Field(default=None)
    stock: Optional[int] = Field(default=None, ge=0)
    sku: Optional[str] = Field(default=None, max_length=30)


class ProductResponse(ProductBase):
    id: int = Field(..., description="Unique product identifier")
    # Breaking change: 'stock' field removed from response
    sku: Optional[str] = Field(default=None, description="Stock Keeping Unit (non-breaking optional field)")

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
