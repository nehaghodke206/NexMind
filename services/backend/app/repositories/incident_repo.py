import json
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.incident import Incident
from app.models.observation import Observation
from app.schemas.incident import IncidentCreate, IncidentUpdate


class IncidentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, incident_id: str) -> Optional[Incident]:
        return self.db.query(Incident).filter(Incident.id == incident_id).first()

    def find_by_fingerprint(
        self, project_id: str, dependency_id: str, fingerprint: str
    ) -> Optional[Incident]:
        if not fingerprint:
            return None
        return (
            self.db.query(Incident)
            .filter(
                Incident.project_id == project_id,
                Incident.dependency_id == dependency_id,
                Incident.fingerprint == fingerprint,
                Incident.status.in_(["open", "triaged", "in_progress", "awaiting_review"]),
            )
            .first()
        )

    def list_paginated(
        self,
        project_id: str,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        assignee_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Incident], int]:
        query = self.db.query(Incident).filter(Incident.project_id == project_id)
        if status:
            query = query.filter(Incident.status == status)
        if severity:
            query = query.filter(Incident.severity == severity)
        if assignee_id:
            query = query.filter(Incident.assignee_id == assignee_id)

        total = query.with_entities(func.count(Incident.id)).scalar() or 0
        offset = (page - 1) * page_size
        items = query.order_by(Incident.created_at.desc()).offset(offset).limit(page_size).all()
        return items, total

    def create(
        self,
        project_id: str,
        data: IncidentCreate,
        observations: Optional[List[Observation]] = None,
    ) -> Incident:
        now = datetime.now(timezone.utc)
        evidence_summary_str = None
        if data.evidence:
            evidence_summary_str = json.dumps(data.evidence)

        incident = Incident(
            project_id=project_id,
            dependency_id=data.dependency_id,
            title=data.title,
            description=data.description,
            change_type=data.change_type,
            severity=data.severity,
            status="open",
            confidence=data.confidence,
            fingerprint=data.fingerprint,
            affected_workflows=data.affected_workflows or [],
            affected_files=data.affected_files or [],
            first_detected_at=now,
            last_observed_at=now,
            evidence_summary=evidence_summary_str,
            metadata_json={"evidence": data.evidence} if data.evidence else {},
        )
        if observations:
            incident.observations.extend(observations)

        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)
        return incident

    def update_dedup(
        self,
        incident: Incident,
        data: IncidentCreate,
        new_observations: Optional[List[Observation]] = None,
    ) -> Incident:
        incident.last_observed_at = datetime.now(timezone.utc)
        if data.confidence is not None:
            incident.confidence = data.confidence
        if data.description and not incident.description:
            incident.description = data.description
        if data.evidence:
            metadata = dict(incident.metadata_json or {})
            metadata["latest_evidence"] = data.evidence
            incident.metadata_json = metadata
            incident.evidence_summary = json.dumps(data.evidence)

        if new_observations:
            existing_obs_ids = {obs.id for obs in incident.observations}
            for obs in new_observations:
                if obs.id not in existing_obs_ids:
                    incident.observations.append(obs)

        self.db.commit()
        self.db.refresh(incident)
        return incident

    def update(self, incident: Incident, data: IncidentUpdate) -> Incident:
        if data.status is not None:
            incident.status = data.status
            if data.status == "resolved":
                incident.resolved_at = datetime.now(timezone.utc)
        if data.assignee_id is not None:
            incident.assignee_id = data.assignee_id
        if data.review_notes is not None:
            incident.review_notes = data.review_notes
        if data.severity is not None:
            incident.severity = data.severity

        self.db.commit()
        self.db.refresh(incident)
        return incident
