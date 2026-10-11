from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class Dependency(Base):
    __tablename__ = "dependencies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    kind = Column(String(50), nullable=False, default="rest_api")  # rest_api, sdk, package, mcp_tool, other
    base_url = Column(String(512), nullable=True)
    version = Column(String(100), nullable=True)
    http_method = Column(String(20), nullable=True)
    endpoint_path = Column(String(512), nullable=True)
    environment = Column(String(100), nullable=True)
    configuration = Column(JSON, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="dependencies")
    baselines = relationship("BaselineVersion", back_populates="dependency", cascade="all, delete-orphan", order_by="BaselineVersion.version_number.desc()")
    scans = relationship("ScanRun", back_populates="dependency")
    incidents = relationship("Incident", back_populates="dependency")
    observations = relationship("Observation", back_populates="dependency")


class BaselineVersion(Base):
    __tablename__ = "baseline_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dependency_id = Column(String(36), ForeignKey("dependencies.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, default=1)
    contract = Column(JSON, nullable=False, default=dict)
    source = Column(String(50), default="manual", nullable=False)  # manual, scan, imported
    content_hash = Column(String(128), nullable=True)
    created_by = Column(String(36), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    dependency = relationship("Dependency", back_populates="baselines")
