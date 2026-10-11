from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.project import Project, ProjectMember
from app.schemas.project import ProjectCreate, ProjectMemberCreate


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, project_id: str) -> Optional[Project]:
        return self.db.query(Project).filter(Project.id == project_id).first()

    def list_paginated(self, page: int = 1, page_size: int = 20) -> Tuple[List[Project], int]:
        total = self.db.query(func.count(Project.id)).scalar() or 0
        offset = (page - 1) * page_size
        items = (
            self.db.query(Project)
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        return items, total

    def create(self, data: ProjectCreate) -> Project:
        project = Project(
            name=data.name,
            description=data.description,
            repository_url=str(data.repository_url) if data.repository_url else None,
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_member(self, project_id: str, user_id: str) -> Optional[ProjectMember]:
        return (
            self.db.query(ProjectMember)
            .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
            .first()
        )

    def list_members(self, project_id: str) -> List[ProjectMember]:
        return (
            self.db.query(ProjectMember)
            .filter(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.joined_at.asc())
            .all()
        )

    def add_member(self, project_id: str, data: ProjectMemberCreate) -> ProjectMember:
        member = ProjectMember(
            project_id=project_id,
            user_id=data.user_id,
            role=data.role,
            display_name=data.display_name,
            email=data.email,
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member
