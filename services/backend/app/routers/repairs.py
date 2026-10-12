from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.repair_service import RepairService
from app.schemas.repair import RepairProposalResponse
from app.schemas.validation import ValidationRunCreate, ValidationRunResponse
from app.schemas.approval import (
    RepairApprovalCreate,
    RepairRejectionCreate,
    RepairApprovalResponse,
)
from app.schemas.application import (
    RepairApplicationCreate,
    RepairApplicationResponse,
)

router = APIRouter(tags=["Repairs"])


@router.get("/repair-proposals/{repair_id}", response_model=RepairProposalResponse, summary="Get repair proposal and diff preview")
@router.get("/repairs/{repair_id}", response_model=RepairProposalResponse, include_in_schema=False)
def get_repair_proposal(repair_id: str, db: Session = Depends(get_db)):
    service = RepairService(db)
    proposal = service.get_proposal(repair_id)
    return RepairProposalResponse.model_validate(proposal)


@router.get("/repair-proposals/{repair_id}/validation-runs", response_model=List[ValidationRunResponse], tags=["Validation"], summary="List validation runs for a repair proposal")
@router.get("/repairs/{repair_id}/validation-runs", response_model=List[ValidationRunResponse], tags=["Validation"], include_in_schema=False)
def list_validation_runs(repair_id: str, db: Session = Depends(get_db)):
    service = RepairService(db)
    runs = service.list_validation_runs(repair_id)
    return [ValidationRunResponse.model_validate(r) for r in runs]


@router.post("/repair-proposals/{repair_id}/validation-runs", response_model=ValidationRunResponse, status_code=status.HTTP_201_CREATED, tags=["Validation"], summary="Record or request validation for a repair proposal")
@router.post("/repairs/{repair_id}/validate", response_model=ValidationRunResponse, status_code=status.HTTP_201_CREATED, tags=["Validation"], include_in_schema=False)
def create_validation_run(repair_id: str, payload: ValidationRunCreate, db: Session = Depends(get_db)):
    service = RepairService(db)
    run = service.create_validation_run(repair_id, payload)
    return ValidationRunResponse.model_validate(run)


@router.post("/repair-proposals/{repair_id}/approvals", response_model=RepairApprovalResponse, status_code=status.HTTP_201_CREATED, tags=["Approvals"], summary="Approve a repair proposal")
@router.post("/repairs/{repair_id}/approve", response_model=RepairApprovalResponse, status_code=status.HTTP_201_CREATED, tags=["Approvals"], include_in_schema=False)
def approve_repair(repair_id: str, payload: RepairApprovalCreate, db: Session = Depends(get_db)):
    service = RepairService(db)
    approval = service.approve_proposal(repair_id, payload)
    return RepairApprovalResponse.model_validate(approval)


@router.post("/repair-proposals/{repair_id}/rejection", response_model=RepairProposalResponse, tags=["Approvals"], summary="Reject a repair proposal")
@router.post("/repairs/{repair_id}/reject", response_model=RepairProposalResponse, tags=["Approvals"], include_in_schema=False)
def reject_repair(repair_id: str, payload: RepairRejectionCreate, db: Session = Depends(get_db)):
    service = RepairService(db)
    proposal = service.reject_proposal(repair_id, payload)
    return RepairProposalResponse.model_validate(proposal)


@router.post("/repair-proposals/{repair_id}/applications", response_model=RepairApplicationResponse, status_code=status.HTTP_201_CREATED, tags=["Applications"], summary="Record local application result reported by the extension")
@router.post("/repairs/{repair_id}/apply-result", response_model=RepairApplicationResponse, status_code=status.HTTP_201_CREATED, tags=["Applications"], include_in_schema=False)
def record_repair_application(repair_id: str, payload: RepairApplicationCreate, db: Session = Depends(get_db)):
    service = RepairService(db)
    app_record = service.record_application(repair_id, payload)
    return RepairApplicationResponse.model_validate(app_record)


@router.post("/repair-proposals/{repair_id}/rollback", response_model=RepairProposalResponse, tags=["Applications"], summary="Rollback an applied repair proposal")
@router.post("/repairs/{repair_id}/rollback", response_model=RepairProposalResponse, tags=["Applications"], include_in_schema=False)
def rollback_repair(repair_id: str, db: Session = Depends(get_db)):
    service = RepairService(db)
    proposal = service.rollback_application(repair_id)
    return RepairProposalResponse.model_validate(proposal)
