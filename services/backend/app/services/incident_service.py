from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    InvalidLifecycleTransitionException,
)
from app.models.incident import Incident
from app.models.observation import Observation
from app.repositories.incident_repo import IncidentRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.dependency_repo import DependencyRepository
from app.repositories.observation_repo import ObservationRepository
from app.repositories.activity_repo import ActivityRepository
from app.schemas.incident import IncidentCreate, IncidentUpdate


VALID_INCIDENT_STATUS_TRANSITIONS = {
    "open": {"triaged", "in_progress", "awaiting_review", "resolved", "dismissed"},
    "triaged": {"in_progress", "awaiting_review", "resolved", "dismissed"},
    "in_progress": {"awaiting_review", "resolved", "dismissed"},
    "awaiting_review": {"in_progress", "resolved", "dismissed"},
    "resolved": {"open", "in_progress"},  # Can reopen if regression observed
    "dismissed": {"open"},  # Can reopen
}


class IncidentService:
    def __init__(self, db: Session):
        self.db = db
        self.incident_repo = IncidentRepository(db)
        self.project_repo = ProjectRepository(db)
        self.dep_repo = DependencyRepository(db)
        self.obs_repo = ObservationRepository(db)
        self.activity_repo = ActivityRepository(db)

    def get_incident(self, incident_id: str) -> Incident:
        incident = self.incident_repo.get_by_id(incident_id)
        if not incident:
            raise NotFoundException("Incident", incident_id)
        return incident

    def list_incidents(
        self,
        project_id: str,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        assignee_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Incident], int]:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)
        return self.incident_repo.list_paginated(
            project_id=project_id,
            status=status,
            severity=severity,
            assignee_id=assignee_id,
            page=page,
            page_size=page_size,
        )

    def list_incident_observations(self, incident_id: str) -> List[Observation]:
        incident = self.get_incident(incident_id)
        return self.obs_repo.list_by_incident(incident)

    def create_incident(self, project_id: str, data: IncidentCreate) -> Incident:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)

        dep = self.dep_repo.get_by_id(data.dependency_id)
        if not dep:
            raise NotFoundException("Dependency", data.dependency_id)
        if dep.project_id != project_id:
            raise BadRequestException(
                f"Dependency '{data.dependency_id}' does not belong to project '{project_id}'"
            )

        observations = []
        if data.observation_ids:
            observations = self.obs_repo.get_by_ids(data.observation_ids)

        # Stable fingerprint deduplication
        if data.fingerprint:
            existing = self.incident_repo.find_by_fingerprint(
                project_id, data.dependency_id, data.fingerprint
            )
            if existing:
                updated = self.incident_repo.update_dedup(
                    existing, data, new_observations=observations
                )
                self.activity_repo.create(
                    project_id=project_id,
                    event_type="incident.deduplicated",
                    message=f"Deduplicated observation against incident {updated.id} ('{updated.title}')",
                    resource_type="incident",
                    resource_id=updated.id,
                    metadata={"fingerprint": data.fingerprint},
                )
                return updated

        # Create new incident
        incident = self.incident_repo.create(
            project_id=project_id, data=data, observations=observations
        )
        self.activity_repo.create(
            project_id=project_id,
            event_type="incident.created",
            message=f"Incident '{incident.title}' detected with severity {incident.severity}",
            resource_type="incident",
            resource_id=incident.id,
            metadata={"severity": incident.severity, "change_type": incident.change_type},
        )
        return incident

    def update_incident(self, incident_id: str, data: IncidentUpdate) -> Incident:
        incident = self.get_incident(incident_id)

        if data.status and data.status != incident.status:
            allowed = VALID_INCIDENT_STATUS_TRANSITIONS.get(incident.status, set())
            if data.status not in allowed:
                raise InvalidLifecycleTransitionException(
                    f"Cannot transition incident from '{incident.status}' to '{data.status}'",
                    current_status=incident.status,
                    target_status=data.status,
                )

        updated = self.incident_repo.update(incident, data)
        self.activity_repo.create(
            project_id=updated.project_id,
            event_type="incident.updated",
            message=f"Incident {updated.id} updated (status: {updated.status})",
            resource_type="incident",
            resource_id=updated.id,
        )
        return updated
