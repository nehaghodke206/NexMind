from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.dependency import Dependency
from app.schemas.dependency import DependencyCreate, DependencyUpdate


class DependencyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, dependency_id: str) -> Optional[Dependency]:
        return self.db.query(Dependency).filter(Dependency.id == dependency_id).first()

    def list_by_project(self, project_id: str) -> List[Dependency]:
        return (
            self.db.query(Dependency)
            .filter(Dependency.project_id == project_id)
            .order_by(Dependency.created_at.asc())
            .all()
        )

    def create(self, project_id: str, data: DependencyCreate) -> Dependency:
        dep = Dependency(
            project_id=project_id,
            name=data.name,
            kind=data.kind,
            base_url=str(data.base_url) if data.base_url else None,
            version=data.version,
            configuration=data.configuration or {},
        )
        self.db.add(dep)
        self.db.commit()
        self.db.refresh(dep)
        return dep

    def update(self, dep: Dependency, data: DependencyUpdate) -> Dependency:
        if data.name is not None:
            dep.name = data.name
        if data.kind is not None:
            dep.kind = data.kind
        if data.base_url is not None:
            dep.base_url = str(data.base_url)
        if data.version is not None:
            dep.version = data.version
        if data.configuration is not None:
            dep.configuration = data.configuration

        self.db.commit()
        self.db.refresh(dep)
        return dep
