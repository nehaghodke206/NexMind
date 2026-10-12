from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.incident_service import IncidentService
from app.services.repair_service import RepairService
from app.schemas.incident import (
    IncidentCreate,
    IncidentUpdate,
    IncidentResponse,
    IncidentListResponse,
    IncidentEventResponse,
    IncidentTransitionRequest,
)
from app.schemas.observation import ObservationResponse
from app.schemas.repair import RepairProposalCreate, RepairProposalResponse

router = APIRouter(tags=["Incidents"])


@router.get("/projects/{project_id}/incidents", response_model=IncidentListResponse, summary="List project incidents")
def list_incidents(
    project_id: str,
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    assignee_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service = IncidentService(db)
    items, total = service.list_incidents(
        project_id=project_id,
        status=status,
        severity=severity,
        assignee_id=assignee_id,
        page=page,
        page_size=page_size,
    )
    return IncidentListResponse(
        items=[IncidentResponse.model_validate(inc) for inc in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/projects/{project_id}/incidents", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED, summary="Create an incident from a detected behavior change")
def create_incident(project_id: str, payload: IncidentCreate, db: Session = Depends(get_db)):
    service = IncidentService(db)
    incident = service.create_incident(project_id, payload)
    return IncidentResponse.model_validate(incident)


@router.get("/incidents/{incident_id}", response_model=IncidentResponse, summary="Get incident details")
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    service = IncidentService(db)
    incident = service.get_incident(incident_id)
    return IncidentResponse.model_validate(incident)


@router.patch("/incidents/{incident_id}", response_model=IncidentResponse, summary="Update incident status, assignment, or review notes")
def update_incident(incident_id: str, payload: IncidentUpdate, db: Session = Depends(get_db)):
    service = IncidentService(db)
    incident = service.update_incident(incident_id, payload)
    return IncidentResponse.model_validate(incident)


@router.post("/incidents/{incident_id}/acknowledge", response_model=IncidentResponse, summary="Acknowledge an incident")
def acknowledge_incident(
    incident_id: str,
    payload: Optional[IncidentTransitionRequest] = None,
    db: Session = Depends(get_db),
):
    service = IncidentService(db)
    notes = payload.notes if payload else None
    actor_id = payload.actor_id if payload else None
    incident = service.acknowledge_incident(incident_id, notes=notes, actor_id=actor_id)
    return IncidentResponse.model_validate(incident)


@router.post("/incidents/{incident_id}/resolve", response_model=IncidentResponse, summary="Resolve an incident with optional notes")
def resolve_incident(
    incident_id: str,
    payload: Optional[IncidentTransitionRequest] = None,
    db: Session = Depends(get_db),
):
    service = IncidentService(db)
    notes = payload.notes if payload else None
    actor_id = payload.actor_id if payload else None
    incident = service.resolve_incident(incident_id, notes=notes, actor_id=actor_id)
    return IncidentResponse.model_validate(incident)


@router.post("/incidents/{incident_id}/reopen", response_model=IncidentResponse, summary="Reopen an incident with optional notes")
def reopen_incident(
    incident_id: str,
    payload: Optional[IncidentTransitionRequest] = None,
    db: Session = Depends(get_db),
):
    service = IncidentService(db)
    notes = payload.notes if payload else None
    actor_id = payload.actor_id if payload else None
    incident = service.reopen_incident(incident_id, notes=notes, actor_id=actor_id)
    return IncidentResponse.model_validate(incident)


@router.get("/incidents/{incident_id}/events", response_model=List[IncidentEventResponse], summary="Get incident lifecycle event history")
def list_incident_events(incident_id: str, db: Session = Depends(get_db)):
    service = IncidentService(db)
    events = service.list_incident_events(incident_id)
    return [IncidentEventResponse.model_validate(e) for e in events]


@router.get("/incidents/{incident_id}/observations", response_model=List[ObservationResponse], tags=["Observations"], summary="List evidence observations attached to an incident")
def list_incident_observations(incident_id: str, db: Session = Depends(get_db)):
    service = IncidentService(db)
    observations = service.list_incident_observations(incident_id)
    return [ObservationResponse.model_validate(obs) for obs in observations]


# Repair proposal creation and listing on incidents (with route aliases for api-contract.md)
@router.get("/incidents/{incident_id}/repair-proposals", response_model=List[RepairProposalResponse], tags=["Repairs"], summary="List repair proposals for an incident")
@router.get("/incidents/{incident_id}/repairs", response_model=List[RepairProposalResponse], tags=["Repairs"], include_in_schema=False)
def list_repair_proposals(incident_id: str, db: Session = Depends(get_db)):
    service = RepairService(db)
    items = service.list_proposals(incident_id)
    return [RepairProposalResponse.model_validate(p) for p in items]


@router.post("/incidents/{incident_id}/repair-proposals", response_model=RepairProposalResponse, status_code=status.HTTP_201_CREATED, tags=["Repairs"], summary="Create a proposed compatibility repair")
@router.post("/incidents/{incident_id}/repairs", response_model=RepairProposalResponse, status_code=status.HTTP_201_CREATED, tags=["Repairs"], include_in_schema=False)
def create_repair_proposal(incident_id: str, payload: RepairProposalCreate, db: Session = Depends(get_db)):
    service = RepairService(db)
    proposal = service.create_proposal(incident_id, payload)
    return RepairProposalResponse.model_validate(proposal)
