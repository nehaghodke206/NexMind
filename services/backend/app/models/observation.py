from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

incident_observations = Table(
    "incident_observations",
    Base.metadata,
    Column("incident_id", String(36), ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True),
    Column("observation_id", String(36), ForeignKey("observations.id", ondelete="CASCADE"), primary_key=True),
)


class Observation(Base):
    __tablename__ = "observations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scan_id = Column(String(36), ForeignKey("scan_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    dependency_id = Column(String(36), ForeignKey("dependencies.id", ondelete="CASCADE"), nullable=False, index=True)
    observation_type = Column(String(50), nullable=False)
    endpoint = Column(String(512), nullable=True)
    method = Column(String(20), nullable=True)
    observed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    fingerprint = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    scan = relationship("ScanRun", back_populates="observations")
    dependency = relationship("Dependency", back_populates="observations")
    incidents = relationship("Incident", secondary=incident_observations, back_populates="observations")
