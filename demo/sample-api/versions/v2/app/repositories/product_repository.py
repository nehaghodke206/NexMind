"""In-memory Product repository (v2)."""
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
                "sku": "HEADPH-ANC-01",
                "store_id": "store-main",
            },
            2: {
                "id": 2,
                "name": "Merino Wool Sweater",
                "description": "Warm, breathable lightweight crewneck",
                "price": 89.50,
                "category": ProductCategory.apparel,
                "stock": 20,
                "sku": "SWEATER-WOOL-02",
                "store_id": "store-main",
            },
            3: {
                "id": 3,
                "name": "Ceramic Pour-Over Dripper",
                "description": "Manual coffee dripper for single cup brewing",
                "price": 32.00,
                "category": ProductCategory.home,
                "stock": 100,
                "sku": "COFFEE-DRIP-03",
                "store_id": "store-main",
            },
        }
        self._next_id = 4

    def list(
        self,
        store_id: str,
        category: Optional[ProductCategory] = None,
        min_price: Optional[float] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[dict]:
        items = [p for p in self._data.values() if p.get("store_id") == store_id or store_id == "all"]
        if category:
            items = [p for p in items if p["category"] == category]
        if min_price is not None:
            items = [p for p in items if p["price"] >= min_price]
        return items[offset : offset + limit]

    def count(
        self,
        store_id: str,
        category: Optional[ProductCategory] = None,
        min_price: Optional[float] = None,
    ) -> int:
        items = [p for p in self._data.values() if p.get("store_id") == store_id or store_id == "all"]
        if category:
            items = [p for p in items if p["category"] == category]
        if min_price is not None:
            items = [p for p in items if p["price"] >= min_price]
        return len(items)

    def get_by_id(self, product_id: int) -> Optional[dict]:
        return self._data.get(product_id)

    def create(self, product_in: ProductCreate, store_id: str = "store-main") -> dict:
        pid = self._next_id
        self._next_id += 1
        record = {
            "id": pid,
            "name": product_in.name,
            "description": product_in.description,
            "price": product_in.price,
            "category": product_in.category,
            "stock": product_in.stock,
            "sku": product_in.sku or f"SKU-{pid:04d}",
            "store_id": store_id,
        }
        self._data[pid] = record
        return record

    def update(self, product_id: int, product_in: ProductUpdate) -> Optional[dict]:
        prod = self._data.get(product_id)
        if not prod:
            return None
        if product_in.name is not None:
            prod["name"] = product_in.name
        if product_in.description is not None:
            prod["description"] = product_in.description
        if product_in.price is not None:
            prod["price"] = product_in.price
        if product_in.category is not None:
            prod["category"] = product_in.category
        if product_in.stock is not None:
            prod["stock"] = product_in.stock
        if product_in.sku is not None:
            prod["sku"] = product_in.sku
        return prod

    # Note: delete() is intentionally removed as part of API deprecation
