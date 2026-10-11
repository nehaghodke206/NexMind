import hashlib
import json
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.dependency import BaselineVersion
from app.schemas.baseline import BaselineCreate


class BaselineRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, baseline_id: str) -> Optional[BaselineVersion]:
        return self.db.query(BaselineVersion).filter(BaselineVersion.id == baseline_id).first()

    def list_by_dependency(self, dependency_id: str) -> List[BaselineVersion]:
        return (
            self.db.query(BaselineVersion)
            .filter(BaselineVersion.dependency_id == dependency_id)
            .order_by(BaselineVersion.version_number.desc())
            .all()
        )

    def get_latest_version_number(self, dependency_id: str) -> int:
        max_v = (
            self.db.query(func.max(BaselineVersion.version_number))
            .filter(BaselineVersion.dependency_id == dependency_id)
            .scalar()
        )
        return max_v if max_v is not None else 0

    def create(self, dependency_id: str, data: BaselineCreate) -> BaselineVersion:
        next_version = self.get_latest_version_number(dependency_id) + 1
        serialized = json.dumps(data.contract, sort_keys=True)
        content_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        baseline = BaselineVersion(
            dependency_id=dependency_id,
            version_number=next_version,
            contract=data.contract,
            source=data.source,
            content_hash=content_hash,
            created_by=data.created_by,
            notes=data.notes,
        )
        self.db.add(baseline)
        self.db.commit()
        self.db.refresh(baseline)
        return baseline
