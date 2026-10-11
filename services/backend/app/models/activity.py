from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String(36), nullable=True)
    event_type = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(36), nullable=True)
    message = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    project = relationship("Project", back_populates="activity_events")
