"""Products REST API endpoints (v2)."""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from ..schemas.product import ProductCategory, ProductCreate, ProductListResponse, ProductResponse, ProductUpdate
from ..services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])

_shared_product_service = ProductService()


def get_product_service() -> ProductService:
    return _shared_product_service


@router.get("", response_model=ProductListResponse, summary="List products")
def list_products(
    # Breaking change: newly required query parameter 'store_id'
    store_id: str = Query(..., description="Store location identifier required for multi-store inventory"),
    category: Optional[ProductCategory] = Query(default=None, description="Filter by product category"),
    min_price: Optional[float] = Query(default=None, ge=0, description="Minimum price filter"),
    limit: int = Query(default=20, ge=1, le=100, description="Page limit"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    service: ProductService = Depends(get_product_service),
):
    return service.list_products(store_id=store_id, category=category, min_price=min_price, limit=limit, offset=offset)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, summary="Create product")
def create_product(
    payload: ProductCreate,
    store_id: str = Query(default="store-main", description="Store ID for initial product placement"),
    service: ProductService = Depends(get_product_service),
):
    return service.create_product(payload, store_id=store_id)


@router.get("/{product_id}", response_model=ProductResponse, summary="Get product by ID")
def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
):
    return service.get_product(product_id)


@router.put("/{product_id}", response_model=ProductResponse, summary="Update product")
def update_product(
    product_id: int,
    payload: ProductUpdate,
    service: ProductService = Depends(get_product_service),
):
    return service.update_product(product_id, payload)


# Breaking change: DELETE /{product_id} method has been removed from this resource
