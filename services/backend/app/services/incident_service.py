from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.exceptions import (
    NotFoundException,
    BadRequestException,
    InvalidLifecycleTransitionException,
)
from app.models.incident import Incident, IncidentEvent
from app.models.observation import Observation
from app.repositories.incident_repo import IncidentRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.dependency_repo import DependencyRepository
from app.repositories.observation_repo import ObservationRepository
from app.repositories.activity_repo import ActivityRepository
from app.schemas.incident import IncidentCreate, IncidentUpdate


VALID_INCIDENT_STATUS_TRANSITIONS = {
    "open": {"acknowledged", "resolved", "triaged", "in_progress", "dismissed"},
    "acknowledged": {"resolved", "open", "in_progress", "dismissed"},
    "triaged": {"in_progress", "acknowledged", "resolved", "dismissed"},
    "in_progress": {"awaiting_review", "acknowledged", "resolved", "dismissed"},
    "awaiting_review": {"in_progress", "resolved", "dismissed"},
    "resolved": {"reopened", "open"},  # Can reopen if regression observed
    "reopened": {"acknowledged", "resolved", "in_progress", "open"},
    "dismissed": {"open", "reopened"},
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

    def list_incident_events(self, incident_id: str) -> List[IncidentEvent]:
        self.get_incident(incident_id)
        return self.incident_repo.list_events(incident_id)

    def create_incident(self, project_id: str, data: IncidentCreate) -> Incident:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)

        if data.dependency_id:
            dep = self.dep_repo.get_by_id(data.dependency_id)
            if not dep:
                raise NotFoundException("Dependency", data.dependency_id)
            if dep.project_id != project_id:
                raise BadRequestException(
                    f"Dependency '{data.dependency_id}' does not belong to project '{project_id}'"
                )
        else:
            deps = self.dep_repo.list_by_project(project_id)
            if deps:
                data.dependency_id = deps[0].id

        observations = []
        if data.observation_ids:
            observations = self.obs_repo.get_by_ids(data.observation_ids)

        # Stable fingerprint deduplication
        if data.fingerprint:
            existing = self.incident_repo.find_by_fingerprint(
                project_id, data.fingerprint, data.dependency_id
            )
            if existing:
                updated, was_reopened = self.incident_repo.update_dedup(
                    existing, data, new_observations=observations
                )
                self.activity_repo.create(
                    project_id=project_id,
                    event_type="incident.reopened" if was_reopened else "incident.deduplicated",
                    message=f"Incident {updated.id} ('{updated.title}') "
                    + ("reopened on recurring observation" if was_reopened else "deduplicated observation"),
                    resource_type="incident",
                    resource_id=updated.id,
                    metadata={"fingerprint": data.fingerprint, "occurrence_count": updated.occurrence_count},
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

    def acknowledge_incident(
        self, incident_id: str, notes: Optional[str] = None, actor_id: Optional[str] = None
    ) -> Incident:
        incident = self.get_incident(incident_id)
        allowed = VALID_INCIDENT_STATUS_TRANSITIONS.get(incident.status, set())
        if "acknowledged" not in allowed and incident.status != "acknowledged":
            raise InvalidLifecycleTransitionException(
                f"Cannot acknowledge incident currently in '{incident.status}' status",
                current_status=incident.status,
                target_status="acknowledged",
            )

        updated = self.incident_repo.transition_status(
            incident, "acknowledged", actor_id=actor_id, notes=notes
        )
        self.activity_repo.create(
            project_id=updated.project_id,
            event_type="incident.acknowledged",
            message=f"Incident {updated.id} acknowledged by {actor_id or 'developer'}",
            resource_type="incident",
            resource_id=updated.id,
            metadata={"notes": notes},
        )
        return updated

    def resolve_incident(
        self, incident_id: str, notes: Optional[str] = None, actor_id: Optional[str] = None
    ) -> Incident:
        incident = self.get_incident(incident_id)
        allowed = VALID_INCIDENT_STATUS_TRANSITIONS.get(incident.status, set())
        if "resolved" not in allowed and incident.status != "resolved":
            raise InvalidLifecycleTransitionException(
                f"Cannot resolve incident currently in '{incident.status}' status",
                current_status=incident.status,
                target_status="resolved",
            )

        updated = self.incident_repo.transition_status(
            incident, "resolved", actor_id=actor_id, notes=notes
        )
        self.activity_repo.create(
            project_id=updated.project_id,
            event_type="incident.resolved",
            message=f"Incident {updated.id} resolved" + (f": {notes}" if notes else ""),
            resource_type="incident",
            resource_id=updated.id,
            metadata={"notes": notes},
        )
        return updated

    def reopen_incident(
        self, incident_id: str, notes: Optional[str] = None, actor_id: Optional[str] = None
    ) -> Incident:
        incident = self.get_incident(incident_id)
        allowed = VALID_INCIDENT_STATUS_TRANSITIONS.get(incident.status, set())
        if "reopened" not in allowed and incident.status != "reopened":
            raise InvalidLifecycleTransitionException(
                f"Cannot reopen incident currently in '{incident.status}' status",
                current_status=incident.status,
                target_status="reopened",
            )

        updated = self.incident_repo.transition_status(
            incident, "reopened", actor_id=actor_id, notes=notes
        )
        self.activity_repo.create(
            project_id=updated.project_id,
            event_type="incident.reopened",
            message=f"Incident {updated.id} reopened" + (f": {notes}" if notes else ""),
            resource_type="incident",
            resource_id=updated.id,
            metadata={"notes": notes},
        )
        return updated
