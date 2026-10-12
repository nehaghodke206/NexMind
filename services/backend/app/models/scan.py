from sqlalchemy import Column, String, Text, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    dependency_id = Column(String(36), ForeignKey("dependencies.id", ondelete="SET NULL"), nullable=True, index=True)
    initiated_by = Column(String(36), nullable=True)
    scan_type = Column(String(50), default="full", nullable=False)
    detection_mode = Column(String(50), default="algorithmic", nullable=True)
    capabilities_executed = Column(JSON, default=list, nullable=False)
    repository_revision = Column(String(100), nullable=True)
    scanner_version = Column(String(50), nullable=True)
    trigger_type = Column(String(50), nullable=True)
    status = Column(String(50), default="queued", nullable=False)  # queued, running, succeeded, partial, failed, canceled, completed
    duration_seconds = Column(Float, nullable=True)
    summary_counts = Column(JSON, default=dict, nullable=False)
    findings_json = Column(JSON, default=list, nullable=False)
    summary = Column(Text, nullable=True)
    summary_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    is_local = Column(Boolean, default=False, nullable=False)
    sync_status = Column(String(50), default="synchronized", nullable=False)
    client_run_id = Column(String(100), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    project = relationship("Project", back_populates="scans")
    dependency = relationship("Dependency", back_populates="scans")
    observations = relationship("Observation", back_populates="scan", cascade="all, delete-orphan")
