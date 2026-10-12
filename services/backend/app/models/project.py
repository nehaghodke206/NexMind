from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    repository_url = Column(String(512), nullable=True)
    repository_root_name = Column(String(255), nullable=True)
    default_branch = Column(String(100), default="main", nullable=False)
    last_scanned_revision = Column(String(100), nullable=True)
    created_by = Column(String(36), nullable=True)
    settings_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    dependencies = relationship("Dependency", back_populates="project", cascade="all, delete-orphan")
    baselines = relationship("ProjectBaseline", back_populates="project", cascade="all, delete-orphan", order_by="ProjectBaseline.version_number.desc()")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    scans = relationship("ScanRun", back_populates="project", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="project", cascade="all, delete-orphan")
    activity_events = relationship("ActivityEvent", back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="developer")
    display_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    joined_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    project = relationship("Project", back_populates="members")
