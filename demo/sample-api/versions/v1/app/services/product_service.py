"""Product business logic service."""
from typing import Optional
from fastapi import HTTPException, status
from ..repositories.product_repository import ProductRepository
from ..schemas.product import ProductCategory, ProductCreate, ProductListResponse, ProductResponse, ProductUpdate


class ProductService:
    def __init__(self, repo: Optional[ProductRepository] = None):
        self.repo = repo or ProductRepository()

    def list_products(
        self,
        category: Optional[ProductCategory] = None,
        min_price: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ProductListResponse:
        items = self.repo.list(category=category, min_price=min_price, limit=limit, offset=offset)
        total = self.repo.count(category=category, min_price=min_price)
        return ProductListResponse(items=[ProductResponse.model_validate(p) for p in items], total=total)

    def get_product(self, product_id: int) -> ProductResponse:
        prod = self.repo.get_by_id(product_id)
        if not prod:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with ID {product_id} not found")
        return ProductResponse.model_validate(prod)

    def create_product(self, prod_in: ProductCreate) -> ProductResponse:
        created = self.repo.create(prod_in)
        return ProductResponse.model_validate(created)

    def update_product(self, product_id: int, prod_in: ProductUpdate) -> ProductResponse:
        updated = self.repo.update(product_id, prod_in)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with ID {product_id} not found")
        return ProductResponse.model_validate(updated)

    def delete_product(self, product_id: int) -> None:
        deleted = self.repo.delete(product_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with ID {product_id} not found")

