from sqlalchemy import Column, String, Text, Float, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now


class RepairProposal(Base):
    __tablename__ = "repair_proposals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="proposed")  # proposed, validating, ready_for_review, approved, rejected, applied, failed
    rationale = Column(Text, nullable=False)
    strategy = Column(String(50), nullable=False, default="compatibility_adapter")  # compatibility_adapter, callsite_update, pagination_adapter, manual_review, other
    diff_preview = Column(Text, nullable=True)
    proposed_changes = Column(JSON, default=dict, nullable=False)
    confidence = Column(Float, nullable=True)
    created_by = Column(String(36), nullable=True)
    target_ref = Column(String(255), nullable=True)
    base_revision = Column(String(100), nullable=True)
    target_file_paths_json = Column(JSON, nullable=True)
    patch_hash = Column(String(128), nullable=True)
    validation_summary_json = Column(JSON, nullable=True)
    applied_revision = Column(String(100), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    incident = relationship("Incident", back_populates="repair_proposals")
    validation_runs = relationship("ValidationRun", back_populates="repair_proposal", cascade="all, delete-orphan", order_by="ValidationRun.created_at.desc()")
    approvals = relationship("RepairApproval", back_populates="repair_proposal", cascade="all, delete-orphan", order_by="RepairApproval.decided_at.desc()")
    applications = relationship("RepairApplication", back_populates="repair_proposal", cascade="all, delete-orphan", order_by="RepairApplication.reported_at.desc()")


class ValidationRun(Base):
    __tablename__ = "validation_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    repair_id = Column(String(36), ForeignKey("repair_proposals.id", ondelete="CASCADE"), nullable=False, index=True)
    run_number = Column(Integer, default=1, nullable=False)
    status = Column(String(50), nullable=False, default="queued")  # queued, running, passed, failed, blocked, error
    test_command = Column(String(512), nullable=True)
    output = Column(Text, nullable=True)
    details = Column(JSON, default=dict, nullable=False)
    validator_type = Column(String(100), nullable=True)
    input_revision = Column(String(100), nullable=True)
    logs_uri = Column(String(512), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    repair_proposal = relationship("RepairProposal", back_populates="validation_runs")


class RepairApproval(Base):
    __tablename__ = "repair_approvals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    repair_id = Column(String(36), ForeignKey("repair_proposals.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(String(36), nullable=False)
    decision = Column(String(50), nullable=False)  # approved, rejected
    comment = Column(Text, nullable=True)
    decided_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    repair_proposal = relationship("RepairProposal", back_populates="approvals")


class RepairApplication(Base):
    __tablename__ = "repair_applications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    repair_id = Column(String(36), ForeignKey("repair_proposals.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(36), nullable=True)
    status = Column(String(50), nullable=False)  # applied, failed, cancelled
    workspace_reference = Column(String(512), nullable=True)
    message = Column(Text, nullable=True)
    reported_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    repair_proposal = relationship("RepairProposal", back_populates="applications")
