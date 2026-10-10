from sqlalchemy import Column, String, Text, Float, DateTime, JSON, ForeignKey
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
    status = Column(String(50), nullable=False, default="open")  # open, triaged, in_progress, awaiting_review, resolved, dismissed
    confidence = Column(Float, nullable=True)
    fingerprint = Column(String(255), nullable=True, index=True)
    review_notes = Column(Text, nullable=True)
    affected_workflows = Column(JSON, default=list, nullable=False)
    affected_files = Column(JSON, default=list, nullable=False)
    first_detected_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_observed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    evidence_summary = Column(Text, nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    project = relationship("Project", back_populates="incidents")
    dependency = relationship("Dependency", back_populates="incidents")
    observations = relationship("Observation", secondary=incident_observations, back_populates="incidents")
    repair_proposals = relationship("RepairProposal", back_populates="incident", cascade="all, delete-orphan", order_by="RepairProposal.created_at.desc()")
