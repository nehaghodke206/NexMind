import json
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.base import utc_now
from app.models.incident import Incident, IncidentEvent
from app.models.observation import Observation
from app.schemas.incident import IncidentCreate, IncidentUpdate


class IncidentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, incident_id: str) -> Optional[Incident]:
        return self.db.query(Incident).filter(Incident.id == incident_id).first()

    def find_by_fingerprint(
        self, project_id: str, fingerprint: str, dependency_id: Optional[str] = None
    ) -> Optional[Incident]:
        if not fingerprint:
            return None
        query = self.db.query(Incident).filter(
            Incident.project_id == project_id,
            Incident.fingerprint == fingerprint,
        )
        if dependency_id:
            query = query.filter(Incident.dependency_id == dependency_id)
        return query.first()

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
        scan_id: Optional[str] = None,
    ) -> Incident:
        now = utc_now()
        evidence_summary_str = None
        if data.evidence:
            evidence_summary_str = json.dumps(data.evidence)

        dep_id = data.dependency_id or (project_id if len(project_id) <= 36 else project_id[:36])

        incident = Incident(
            project_id=project_id,
            dependency_id=dep_id,
            title=data.title,
            description=data.description,
            change_type=data.change_type or "contract_drift",
            severity=data.severity or "medium",
            status="open",
            provenance=data.provenance or "contract_diff",
            confidence=data.confidence,
            fingerprint=data.fingerprint,
            occurrence_count=1,
            recommended_action=data.recommended_action,
            affected_workflows=data.affected_workflows or [],
            affected_files=data.affected_files or [],
            first_detected_at=now,
            last_observed_at=now,
            last_scan_id=scan_id,
            evidence_summary=evidence_summary_str,
            metadata_json={"evidence": data.evidence} if data.evidence else {},
            created_at=now,
            updated_at=now,
        )
        if observations:
            incident.observations.extend(observations)

        self.db.add(incident)
        self.db.flush()

        # Record initial detected event
        event = IncidentEvent(
            incident_id=incident.id,
            event_type="detected",
            from_status=None,
            to_status="open",
            message=f"Incident initially detected ({incident.severity}): {incident.title}",
            metadata_json={"fingerprint": data.fingerprint, "provenance": incident.provenance},
            created_at=now,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(incident)
        return incident

    def update_dedup(
        self,
        incident: Incident,
        data: IncidentCreate,
        new_observations: Optional[List[Observation]] = None,
        scan_id: Optional[str] = None,
    ) -> Tuple[Incident, bool]:
        now = utc_now()
        was_reopened = False
        from_status = incident.status

        incident.last_observed_at = now
        incident.occurrence_count = (incident.occurrence_count or 1) + 1
        incident.updated_at = now
        if scan_id:
            incident.last_scan_id = scan_id

        if data.confidence is not None:
            incident.confidence = data.confidence
        if data.recommended_action and not incident.recommended_action:
            incident.recommended_action = data.recommended_action
        if data.description and not incident.description:
            incident.description = data.description
        if data.evidence:
            metadata = dict(incident.metadata_json or {})
            metadata["latest_evidence"] = data.evidence
            incident.metadata_json = metadata
            incident.evidence_summary = json.dumps(data.evidence)

        # Reopen if previously resolved
        if incident.status == "resolved":
            incident.status = "reopened"
            incident.reopened_at = now
            was_reopened = True

        if new_observations:
            existing_obs_ids = {obs.id for obs in incident.observations}
            for obs in new_observations:
                if obs.id not in existing_obs_ids:
                    incident.observations.append(obs)

        # Log event
        if was_reopened:
            event = IncidentEvent(
                incident_id=incident.id,
                event_type="reopened",
                from_status=from_status,
                to_status="reopened",
                message=f"Resolved incident recurred in scan (occurrence #{incident.occurrence_count})",
                metadata_json={"scan_id": scan_id},
                created_at=now,
            )
        else:
            event = IncidentEvent(
                incident_id=incident.id,
                event_type="deduplicated",
                from_status=from_status,
                to_status=incident.status,
                message=f"Recurring finding observed in scan (occurrence #{incident.occurrence_count})",
                metadata_json={"scan_id": scan_id},
                created_at=now,
            )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(incident)
        return incident, was_reopened

    def transition_status(
        self,
        incident: Incident,
        target_status: str,
        actor_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Incident:
        now = utc_now()
        from_status = incident.status
        incident.status = target_status
        incident.updated_at = now

        if target_status == "acknowledged":
            incident.acknowledged_at = now
            incident.acknowledged_by = actor_id
            if notes:
                incident.review_notes = notes
        elif target_status == "resolved":
            incident.resolved_at = now
            if notes:
                incident.resolution_notes = notes
        elif target_status == "reopened":
            incident.reopened_at = now
            if notes:
                incident.review_notes = notes

        event = IncidentEvent(
            incident_id=incident.id,
            event_type=target_status,
            actor_id=actor_id,
            from_status=from_status,
            to_status=target_status,
            message=f"Incident transitioned to {target_status}" + (f": {notes}" if notes else ""),
            metadata_json={"notes": notes} if notes else {},
            created_at=now,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(incident)
        return incident

    def update(self, incident: Incident, data: IncidentUpdate) -> Incident:
        now = utc_now()
        if data.status is not None and data.status != incident.status:
            self.transition_status(
                incident,
                data.status,
                actor_id=data.assignee_id,
                notes=data.resolution_notes or data.review_notes,
            )

        if data.assignee_id is not None:
            incident.assignee_id = data.assignee_id
        if data.review_notes is not None:
            incident.review_notes = data.review_notes
        if data.resolution_notes is not None:
            incident.resolution_notes = data.resolution_notes
        if data.recommended_action is not None:
            incident.recommended_action = data.recommended_action
        if data.severity is not None:
            incident.severity = data.severity
        incident.updated_at = now

        self.db.commit()
        self.db.refresh(incident)
        return incident

    def list_events(self, incident_id: str) -> List[IncidentEvent]:
        return (
            self.db.query(IncidentEvent)
            .filter(IncidentEvent.incident_id == incident_id)
            .order_by(IncidentEvent.created_at.desc())
            .all()
        )
