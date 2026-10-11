from typing import List
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundException
from app.models.dependency import BaselineVersion
from app.repositories.baseline_repo import BaselineRepository
from app.repositories.dependency_repo import DependencyRepository
from app.repositories.activity_repo import ActivityRepository
from app.schemas.baseline import BaselineCreate


class BaselineService:
    def __init__(self, db: Session):
        self.db = db
        self.baseline_repo = BaselineRepository(db)
        self.dep_repo = DependencyRepository(db)
        self.activity_repo = ActivityRepository(db)

    def get_baseline(self, baseline_id: str) -> BaselineVersion:
        baseline = self.baseline_repo.get_by_id(baseline_id)
        if not baseline:
            raise NotFoundException("Baseline", baseline_id)
        return baseline

    def list_baselines(self, dependency_id: str) -> List[BaselineVersion]:
        dep = self.dep_repo.get_by_id(dependency_id)
        if not dep:
            raise NotFoundException("Dependency", dependency_id)
        return self.baseline_repo.list_by_dependency(dependency_id)

    def create_baseline(self, dependency_id: str, data: BaselineCreate) -> BaselineVersion:
        dep = self.dep_repo.get_by_id(dependency_id)
        if not dep:
            raise NotFoundException("Dependency", dependency_id)

        baseline = self.baseline_repo.create(dependency_id, data)
        self.activity_repo.create(
            project_id=dep.project_id,
            event_type="baseline.saved",
            message=f"Saved baseline v{baseline.version_number} for dependency '{dep.name}'",
            actor_id=data.created_by,
            resource_type="baseline",
            resource_id=baseline.id,
            metadata={"version": baseline.version_number, "source": baseline.source},
        )
        return baseline
