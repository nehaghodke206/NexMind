"""Product business logic service (v2)."""
from typing import Optional
from fastapi import HTTPException, status
from ..repositories.product_repository import ProductRepository
from ..schemas.product import ProductCategory, ProductCreate, ProductListResponse, ProductResponse, ProductUpdate


class ProductService:
    def __init__(self, repo: Optional[ProductRepository] = None):
        self.repo = repo or ProductRepository()

    def list_products(
        self,
        store_id: str,
        category: Optional[ProductCategory] = None,
        min_price: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ProductListResponse:
        items = self.repo.list(store_id=store_id, category=category, min_price=min_price, limit=limit, offset=offset)
        total = self.repo.count(store_id=store_id, category=category, min_price=min_price)
        return ProductListResponse(items=[ProductResponse.model_validate(p) for p in items], total=total)

    def get_product(self, product_id: int) -> ProductResponse:
        product = self.repo.get_by_id(product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with ID {product_id} not found")
        return ProductResponse.model_validate(product)

    def create_product(self, product_in: ProductCreate, store_id: str = "store-main") -> ProductResponse:
        created = self.repo.create(product_in, store_id=store_id)
        return ProductResponse.model_validate(created)

    def update_product(self, product_id: int, product_in: ProductUpdate) -> ProductResponse:
        updated = self.repo.update(product_id, product_in)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with ID {product_id} not found")
        return ProductResponse.model_validate(updated)

    # Deletion method intentionally removed
