from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.scan_service import ScanService
from app.schemas.scan import (
    ScanCreate,
    ScanRunResponse,
    ScanCompleteRequest,
    ScanIngestRequest,
)
from app.schemas.observation import ObservationBatchCreate, ObservationBatchResponse

router = APIRouter(tags=["Scans"])


@router.get(
    "/projects/{project_id}/scans",
    response_model=List[ScanRunResponse],
    summary="List persistent scan runs for a project",
)
def list_scans(
    project_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    service = ScanService(db)
    items = service.list_scans(project_id)
    return [ScanRunResponse.model_validate(s) for s in items[:limit]]


@router.post(
    "/projects/{project_id}/scans",
    response_model=ScanRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a background dependency scan",
)
def start_scan(project_id: str, payload: ScanCreate, db: Session = Depends(get_db)):
    service = ScanService(db)
    scan = service.start_scan(project_id, payload)
    return ScanRunResponse.model_validate(scan)


@router.post(
    "/projects/{project_id}/scans/ingest",
    response_model=ScanRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a completed scan run executed locally in VS Code or CI",
)
def ingest_scan(
    project_id: str, payload: ScanIngestRequest, db: Session = Depends(get_db)
):
    service = ScanService(db)
    scan = service.ingest_scan(project_id, payload)
    return ScanRunResponse.model_validate(scan)


@router.get("/scans/{scan_id}", response_model=ScanRunResponse, summary="Get scan status and summary")
def get_scan(scan_id: str, db: Session = Depends(get_db)):
    service = ScanService(db)
    scan = service.get_scan(scan_id)
    return ScanRunResponse.model_validate(scan)


@router.post(
    "/scans/{scan_id}/observations",
    response_model=ObservationBatchResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Observations"],
    summary="Submit observations collected by a scanner",
)
def submit_observations(
    scan_id: str, payload: ObservationBatchCreate, db: Session = Depends(get_db)
):
    service = ScanService(db)
    count, ids = service.submit_observations(scan_id, payload.observations)
    return ObservationBatchResponse(accepted_count=count, observation_ids=ids)


@router.post(
    "/scans/{scan_id}/complete",
    response_model=ScanRunResponse,
    summary="Mark a scan as completed or failed",
)
def complete_scan(
    scan_id: str, payload: ScanCompleteRequest, db: Session = Depends(get_db)
):
    service = ScanService(db)
    scan = service.complete_scan(scan_id, payload)
    return ScanRunResponse.model_validate(scan)
