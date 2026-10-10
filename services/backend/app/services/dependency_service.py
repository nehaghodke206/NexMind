from typing import List
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundException
from app.models.dependency import Dependency
from app.repositories.dependency_repo import DependencyRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.activity_repo import ActivityRepository
from app.schemas.dependency import DependencyCreate, DependencyUpdate


class DependencyService:
    def __init__(self, db: Session):
        self.db = db
        self.dep_repo = DependencyRepository(db)
        self.project_repo = ProjectRepository(db)
        self.activity_repo = ActivityRepository(db)

    def get_dependency(self, dependency_id: str) -> Dependency:
        dep = self.dep_repo.get_by_id(dependency_id)
        if not dep:
            raise NotFoundException("Dependency", dependency_id)
        return dep

    def list_dependencies(self, project_id: str) -> List[Dependency]:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)
        return self.dep_repo.list_by_project(project_id)

    def create_dependency(self, project_id: str, data: DependencyCreate) -> Dependency:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)

        dep = self.dep_repo.create(project_id, data)
        self.activity_repo.create(
            project_id=project_id,
            event_type="dependency.registered",
            message=f"Dependency '{dep.name}' ({dep.kind}) registered",
            resource_type="dependency",
            resource_id=dep.id,
        )
        return dep

    def update_dependency(self, dependency_id: str, data: DependencyUpdate) -> Dependency:
        dep = self.get_dependency(dependency_id)
        updated = self.dep_repo.update(dep, data)
        self.activity_repo.create(
            project_id=updated.project_id,
            event_type="dependency.updated",
            message=f"Dependency '{updated.name}' was updated",
            resource_type="dependency",
            resource_id=updated.id,
        )
        return updated
