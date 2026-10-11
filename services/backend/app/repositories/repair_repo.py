from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.repair import (
    RepairProposal,
    ValidationRun,
    RepairApproval,
    RepairApplication,
)
from app.schemas.repair import RepairProposalCreate
from app.schemas.validation import ValidationRunCreate
from app.schemas.approval import RepairApprovalCreate, RepairRejectionCreate
from app.schemas.application import RepairApplicationCreate


class RepairRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_proposal_by_id(self, repair_id: str) -> Optional[RepairProposal]:
        return self.db.query(RepairProposal).filter(RepairProposal.id == repair_id).first()

    def list_proposals_by_incident(self, incident_id: str) -> List[RepairProposal]:
        return (
            self.db.query(RepairProposal)
            .filter(RepairProposal.incident_id == incident_id)
            .order_by(RepairProposal.created_at.desc())
            .all()
        )

    def create_proposal(self, incident_id: str, data: RepairProposalCreate) -> RepairProposal:
        diff_preview = data.diff_preview
        if not diff_preview and data.patch:
            diff_preview = data.patch.get("content")

        proposal = RepairProposal(
            incident_id=incident_id,
            status="proposed",
            rationale=data.rationale,
            strategy=data.strategy,
            diff_preview=diff_preview,
            proposed_changes=data.proposed_changes or {},
            confidence=data.confidence,
            created_by=data.created_by,
        )
        self.db.add(proposal)
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def create_validation_run(
        self, proposal: RepairProposal, data: ValidationRunCreate
    ) -> ValidationRun:
        status_val = data.status
        if data.result:
            status_val = "passed" if data.result.lower() == "passed" else "failed"

        details = dict(data.details or {})
        if data.summary:
            details["summary"] = data.summary

        run_count = len(proposal.validation_runs) + 1
        now = datetime.now(timezone.utc)

        run = ValidationRun(
            repair_id=proposal.id,
            run_number=run_count,
            status=status_val,
            test_command=data.test_command,
            output=data.output,
            details=details,
            started_at=data.started_at or now,
            completed_at=data.completed_at or now,
        )
        self.db.add(run)

        # Update proposal status according to validation result
        if status_val == "passed":
            proposal.status = "ready_for_review"
        elif status_val in ["failed", "error"]:
            proposal.status = "failed"
        elif status_val in ["queued", "running"]:
            proposal.status = "validating"

        self.db.commit()
        self.db.refresh(run)
        self.db.refresh(proposal)
        return run

    def list_validation_runs(self, repair_id: str) -> List[ValidationRun]:
        return (
            self.db.query(ValidationRun)
            .filter(ValidationRun.repair_id == repair_id)
            .order_by(ValidationRun.created_at.desc())
            .all()
        )

    def create_approval(
        self, proposal: RepairProposal, data: RepairApprovalCreate
    ) -> RepairApproval:
        now = datetime.now(timezone.utc)
        approval = RepairApproval(
            repair_id=proposal.id,
            reviewer_id=data.reviewer_id,
            decision="approved",
            comment=data.comment,
            decided_at=now,
        )
        self.db.add(approval)
        proposal.status = "approved"
        self.db.commit()
        self.db.refresh(approval)
        self.db.refresh(proposal)
        return approval

    def create_rejection(
        self, proposal: RepairProposal, data: RepairRejectionCreate
    ) -> RepairApproval:
        now = datetime.now(timezone.utc)
        rejection = RepairApproval(
            repair_id=proposal.id,
            reviewer_id=data.reviewer_id,
            decision="rejected",
            comment=data.reason,
            decided_at=now,
        )
        self.db.add(rejection)
        proposal.status = "rejected"
        self.db.commit()
        self.db.refresh(rejection)
        self.db.refresh(proposal)
        return rejection

    def create_application(
        self, proposal: RepairProposal, data: RepairApplicationCreate
    ) -> RepairApplication:
        now = datetime.now(timezone.utc)
        app_record = RepairApplication(
            repair_id=proposal.id,
            agent_id=data.agent_id,
            status=data.status,
            workspace_reference=data.workspace_reference,
            message=data.message,
            reported_at=now,
        )
        self.db.add(app_record)

        if data.status == "applied":
            proposal.status = "applied"
            proposal.applied_at = now
            # If application succeeded, mark the linked incident as resolved
            if proposal.incident:
                proposal.incident.status = "resolved"
                proposal.incident.resolved_at = now
        elif data.status == "failed":
            proposal.status = "failed"

        self.db.commit()
        self.db.refresh(app_record)
        self.db.refresh(proposal)
        return app_record
