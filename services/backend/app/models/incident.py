from sqlalchemy import Column, String, Text, Float, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now
from app.models.observation import incident_observations


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    dependency_id = Column(String(36), ForeignKey("dependencies.id", ondelete="CASCADE"), nullable=False, index=True)
    assignee_id = Column(String(36), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    change_type = Column(String(50), nullable=False, default="unknown")
    severity = Column(String(50), nullable=False, default="medium")
    status = Column(String(50), nullable=False, default="open")  # open, acknowledged, resolved, reopened, triaged, in_progress, dismissed
    provenance = Column(String(50), nullable=False, default="contract_diff")  # static_ast, contract_diff, live_probe, ai_inferred
    confidence = Column(Float, nullable=True)
    fingerprint = Column(String(255), nullable=True, index=True)
    occurrence_count = Column(Integer, nullable=False, default=1)
    recommended_action = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    review_notes = Column(Text, nullable=True)
    affected_workflows = Column(JSON, default=list, nullable=False)
    affected_files = Column(JSON, default=list, nullable=False)
    first_detected_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_observed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String(36), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    reopened_at = Column(DateTime(timezone=True), nullable=True)
    last_scan_id = Column(String(36), nullable=True)
    evidence_summary = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    project = relationship("Project", back_populates="incidents")
    dependency = relationship("Dependency", back_populates="incidents")
    observations = relationship("Observation", secondary=incident_observations, back_populates="incidents")
    events = relationship("IncidentEvent", back_populates="incident", cascade="all, delete-orphan", order_by="IncidentEvent.created_at.desc()")
    repair_proposals = relationship("RepairProposal", back_populates="incident", cascade="all, delete-orphan", order_by="RepairProposal.created_at.desc()")


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # detected, acknowledged, resolved, reopened, deduplicated, commented
    actor_id = Column(String(36), nullable=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=True)
    message = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    incident = relationship("Incident", back_populates="events")
