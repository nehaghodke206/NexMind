from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class ProjectBaseline(Base):
    """
    Persistent, versioned baseline for a project capturing contracts and discovered inventory.
    """
    __tablename__ = "project_baselines"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    version_tag = Column(String(100), nullable=True)
    contracts = Column(JSON, nullable=False, default=dict)
    inventory = Column(JSON, nullable=False, default=dict)
    source_scan_id = Column(String(36), ForeignKey("scan_runs.id", ondelete="SET NULL"), nullable=True)
    content_hash = Column(String(128), nullable=True)
    created_by = Column(String(36), nullable=True)
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    is_promoted = Column(Boolean, default=False, nullable=False)
    promoted_at = Column(DateTime(timezone=True), nullable=True)
    promoted_by = Column(String(36), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "version_number", name="uq_project_baseline_version"),
    )

    project = relationship("Project", back_populates="baselines")
    source_scan = relationship("ScanRun")
