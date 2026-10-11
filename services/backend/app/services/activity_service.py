from typing import List, Tuple
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundException
from app.models.activity import ActivityEvent
from app.repositories.activity_repo import ActivityRepository
from app.repositories.project_repo import ProjectRepository


class ActivityService:
    def __init__(self, db: Session):
        self.db = db
        self.activity_repo = ActivityRepository(db)
        self.project_repo = ProjectRepository(db)

    def list_activity(
        self, project_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[ActivityEvent], int]:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)
        return self.activity_repo.list_paginated(
            project_id=project_id, page=page, page_size=page_size
        )
