from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.exceptions import NotFoundException, ConflictException
from app.models.project import Project, ProjectMember
from app.models.dependency import Dependency
from app.models.incident import Incident
from app.models.scan import ScanRun
from app.models.repair import RepairProposal, ValidationRun
from app.repositories.project_repo import ProjectRepository
from app.repositories.activity_repo import ActivityRepository
from app.schemas.project import ProjectCreate, ProjectMemberCreate
from app.schemas.dashboard import ProjectSummaryResponse


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.activity_repo = ActivityRepository(db)

    def get_project(self, project_id: str) -> Project:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)
        return project

    def list_projects(self, page: int = 1, page_size: int = 20) -> Tuple[List[Project], int]:
        return self.project_repo.list_paginated(page=page, page_size=page_size)

    def create_project(self, data: ProjectCreate) -> Project:
        project = self.project_repo.create(data)
        self.activity_repo.create(
            project_id=project.id,
            event_type="project.created",
            message=f"Project '{project.name}' was created",
            resource_type="project",
            resource_id=project.id,
        )
        return project

    def list_members(self, project_id: str) -> List[ProjectMember]:
        self.get_project(project_id)
        return self.project_repo.list_members(project_id)

    def add_member(self, project_id: str, data: ProjectMemberCreate) -> ProjectMember:
        project = self.get_project(project_id)
        existing = self.project_repo.get_member(project_id, data.user_id)
        if existing:
            raise ConflictException(
                f"User '{data.user_id}' is already a member of project '{project_id}'"
            )
        member = self.project_repo.add_member(project_id, data)
        self.activity_repo.create(
            project_id=project_id,
            event_type="member.added",
            message=f"User '{data.user_id}' joined project as {data.role}",
            resource_type="project_member",
            resource_id=member.id,
        )
        return member

    def get_project_summary(self, project_id: str) -> ProjectSummaryResponse:
        self.get_project(project_id)

        dep_count = (
            self.db.query(func.count(Dependency.id))
            .filter(Dependency.project_id == project_id)
            .scalar()
            or 0
        )

        open_incidents = (
            self.db.query(func.count(Incident.id))
            .filter(
                Incident.project_id == project_id,
                Incident.status.in_(["open", "triaged", "in_progress", "awaiting_review"]),
            )
            .scalar()
            or 0
        )

        pending_reviews = (
            self.db.query(func.count(RepairProposal.id))
            .join(Incident, Incident.id == RepairProposal.incident_id)
            .filter(
                Incident.project_id == project_id,
                RepairProposal.status == "ready_for_review",
            )
            .scalar()
            or 0
        )

        val_pass = (
            self.db.query(func.count(ValidationRun.id))
            .join(RepairProposal, RepairProposal.id == ValidationRun.repair_id)
            .join(Incident, Incident.id == RepairProposal.incident_id)
            .filter(
                Incident.project_id == project_id,
                ValidationRun.status == "passed",
            )
            .scalar()
            or 0
        )

        val_fail = (
            self.db.query(func.count(ValidationRun.id))
            .join(RepairProposal, RepairProposal.id == ValidationRun.repair_id)
            .join(Incident, Incident.id == RepairProposal.incident_id)
            .filter(
                Incident.project_id == project_id,
                ValidationRun.status.in_(["failed", "error"]),
            )
            .scalar()
            or 0
        )

        last_scan = (
            self.db.query(func.max(ScanRun.started_at))
            .filter(ScanRun.project_id == project_id)
            .scalar()
        )

        return ProjectSummaryResponse(
            project_id=project_id,
            dependency_count=dep_count,
            open_incident_count=open_incidents,
            pending_review_count=pending_reviews,
            validation_pass_count=val_pass,
            validation_fail_count=val_fail,
            last_scan_at=last_scan,
        )
