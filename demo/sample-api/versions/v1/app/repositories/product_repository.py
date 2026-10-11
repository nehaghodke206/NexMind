"""In-memory Product repository."""
from typing import Dict, List, Optional
from ..schemas.product import ProductCategory, ProductCreate, ProductUpdate


class ProductRepository:
    def __init__(self):
        self._data: Dict[int, dict] = {
            1: {
                "id": 1,
                "name": "Noise Cancelling Headphones",
                "description": "High fidelity wireless headphones with ANC",
                "price": 199.99,
                "category": ProductCategory.electronics,
                "stock": 45,
            },
            2: {
                "id": 2,
                "name": "Merino Wool Sweater",
                "description": "Warm, breathable lightweight crewneck",
                "price": 89.50,
                "category": ProductCategory.apparel,
                "stock": 20,
            },
            3: {
                "id": 3,
                "name": "Ceramic Pour-Over Dripper",
                "description": "Manual coffee dripper for single cup brewing",
                "price": 32.00,
                "category": ProductCategory.home,
                "stock": 100,
            },
        }
        self._next_id = 4

    def list(
        self,
        category: Optional[ProductCategory] = None,
        min_price: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[dict]:
        items = list(self._data.values())
        if category:
            items = [p for p in items if p["category"] == category]
        if min_price is not None:
            items = [p for p in items if p["price"] >= min_price]
        return items[offset : offset + limit]

    def count(
        self,
        category: Optional[ProductCategory] = None,
        min_price: Optional[float] = None,
    ) -> int:
        items = list(self._data.values())
        if category:
            items = [p for p in items if p["category"] == category]
        if min_price is not None:
            items = [p for p in items if p["price"] >= min_price]
        return len(items)

    def get_by_id(self, product_id: int) -> Optional[dict]:
        return self._data.get(product_id)

    def create(self, prod_in: ProductCreate) -> dict:
        pid = self._next_id
        self._next_id += 1
        record = {
            "id": pid,
            "name": prod_in.name,
            "description": prod_in.description,
            "price": prod_in.price,
            "category": prod_in.category,
            "stock": prod_in.stock,
        }
        self._data[pid] = record
        return record

    def update(self, product_id: int, prod_in: ProductUpdate) -> Optional[dict]:
        prod = self._data.get(product_id)
        if not prod:
            return None
        if prod_in.name is not None:
            prod["name"] = prod_in.name
        if prod_in.description is not None:
            prod["description"] = prod_in.description
        if prod_in.price is not None:
            prod["price"] = prod_in.price
        if prod_in.category is not None:
            prod["category"] = prod_in.category
        if prod_in.stock is not None:
            prod["stock"] = prod_in.stock
        return prod

    def delete(self, product_id: int) -> bool:
        if product_id in self._data:
            del self._data[product_id]
            return True
        return False

