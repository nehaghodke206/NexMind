from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.observation import Observation
from app.models.incident import Incident
from app.schemas.observation import ObservationCreate


class ObservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, observation_id: str) -> Optional[Observation]:
        return self.db.query(Observation).filter(Observation.id == observation_id).first()

    def get_by_ids(self, observation_ids: List[str]) -> List[Observation]:
        if not observation_ids:
            return []
        return self.db.query(Observation).filter(Observation.id.in_(observation_ids)).all()

    def list_by_scan(self, scan_id: str) -> List[Observation]:
        return (
            self.db.query(Observation)
            .filter(Observation.scan_id == scan_id)
            .order_by(Observation.observed_at.asc())
            .all()
        )

    def list_by_incident(self, incident: Incident) -> List[Observation]:
        return incident.observations

    def create_batch(self, scan_id: str, items: List[ObservationCreate]) -> List[Observation]:
        created: List[Observation] = []
        for item in items:
            obs = Observation(
                scan_id=scan_id,
                dependency_id=item.dependency_id,
                observation_type=item.observation_type,
                endpoint=item.endpoint,
                method=item.method,
                observed_at=item.observed_at or datetime.now(timezone.utc),
                payload=item.payload,
                fingerprint=item.fingerprint,
            )
            self.db.add(obs)
            created.append(obs)
        self.db.commit()
        for obs in created:
            self.db.refresh(obs)
        return created
