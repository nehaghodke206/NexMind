from typing import List
from sqlalchemy.orm import Session
from app.core.exceptions import (
    NotFoundException,
    ConflictException,
    InvalidLifecycleTransitionException,
)
from app.models.repair import (
    RepairProposal,
    ValidationRun,
    RepairApproval,
    RepairApplication,
)
from app.repositories.repair_repo import RepairRepository
from app.repositories.incident_repo import IncidentRepository
from app.repositories.activity_repo import ActivityRepository
from app.schemas.repair import RepairProposalCreate
from app.schemas.validation import ValidationRunCreate
from app.schemas.approval import RepairApprovalCreate, RepairRejectionCreate
from app.schemas.application import RepairApplicationCreate


class RepairService:
    def __init__(self, db: Session):
        self.db = db
        self.repair_repo = RepairRepository(db)
        self.incident_repo = IncidentRepository(db)
        self.activity_repo = ActivityRepository(db)

    def get_proposal(self, repair_id: str) -> RepairProposal:
        proposal = self.repair_repo.get_proposal_by_id(repair_id)
        if not proposal:
            raise NotFoundException("RepairProposal", repair_id)
        return proposal

    def list_proposals(self, incident_id: str) -> List[RepairProposal]:
        incident = self.incident_repo.get_by_id(incident_id)
        if not incident:
            raise NotFoundException("Incident", incident_id)
        return self.repair_repo.list_proposals_by_incident(incident_id)

    def create_proposal(
        self, incident_id: str, data: RepairProposalCreate
    ) -> RepairProposal:
        incident = self.incident_repo.get_by_id(incident_id)
        if not incident:
            raise NotFoundException("Incident", incident_id)

        proposal = self.repair_repo.create_proposal(incident_id, data)
        self.activity_repo.create(
            project_id=incident.project_id,
            event_type="repair.proposed",
            message=f"Repair proposal created for incident {incident_id}: '{proposal.strategy}'",
            actor_id=data.created_by,
            resource_type="repair_proposal",
            resource_id=proposal.id,
            metadata={"strategy": proposal.strategy},
        )
        return proposal

    def list_validation_runs(self, repair_id: str) -> List[ValidationRun]:
        self.get_proposal(repair_id)
        return self.repair_repo.list_validation_runs(repair_id)

    def create_validation_run(
        self, repair_id: str, data: ValidationRunCreate
    ) -> ValidationRun:
        proposal = self.get_proposal(repair_id)
        val_run = self.repair_repo.create_validation_run(proposal, data)

        self.activity_repo.create(
            project_id=proposal.incident.project_id,
            event_type="repair.validated",
            message=f"Validation run #{val_run.run_number} for repair {repair_id} result: {val_run.status}",
            resource_type="validation_run",
            resource_id=val_run.id,
            metadata={"status": val_run.status, "repair_status": proposal.status},
        )
        return val_run

    def approve_proposal(
        self, repair_id: str, data: RepairApprovalCreate
    ) -> RepairApproval:
        proposal = self.get_proposal(repair_id)

        # Enforce lifecycle invariant: proposal cannot be re-approved if already decided
        if proposal.status in ["approved", "rejected", "applied"]:
            raise ConflictException(
                f"Repair proposal '{repair_id}' has already been decided or applied (status: {proposal.status})"
            )

        approval = self.repair_repo.create_approval(proposal, data)
        self.activity_repo.create(
            project_id=proposal.incident.project_id,
            event_type="repair.approved",
            message=f"Repair proposal {repair_id} approved by reviewer {data.reviewer_id}",
            actor_id=data.reviewer_id,
            resource_type="repair_approval",
            resource_id=approval.id,
        )
        return approval

    def reject_proposal(
        self, repair_id: str, data: RepairRejectionCreate
    ) -> RepairProposal:
        proposal = self.get_proposal(repair_id)

        # Enforce lifecycle invariant: proposal cannot be rejected if already decided
        if proposal.status in ["approved", "rejected", "applied"]:
            raise ConflictException(
                f"Repair proposal '{repair_id}' has already been decided or applied (status: {proposal.status})"
            )

        self.repair_repo.create_rejection(proposal, data)
        self.activity_repo.create(
            project_id=proposal.incident.project_id,
            event_type="repair.rejected",
            message=f"Repair proposal {repair_id} rejected: {data.reason}",
            actor_id=data.reviewer_id,
            resource_type="repair_proposal",
            resource_id=proposal.id,
        )
        return proposal

    def record_application(
        self, repair_id: str, data: RepairApplicationCreate
    ) -> RepairApplication:
        proposal = self.get_proposal(repair_id)

        # Enforce invariant: repair must be approved before it can be applied!
        if proposal.status != "approved":
            raise ConflictException(
                f"Repair proposal '{repair_id}' has not been approved yet (current status: {proposal.status})"
            )

        application = self.repair_repo.create_application(proposal, data)
        self.activity_repo.create(
            project_id=proposal.incident.project_id,
            event_type="repair.applied" if data.status == "applied" else "repair.application_failed",
            message=f"Local repair application reported status: {data.status}"
            + (f" ({data.message})" if data.message else ""),
            actor_id=data.agent_id,
            resource_type="repair_application",
            resource_id=application.id,
        )
        return application
