from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.scan_service import ScanService
from app.schemas.scan import ScanCreate, ScanRunResponse, ScanCompleteRequest
from app.schemas.observation import ObservationBatchCreate, ObservationBatchResponse

router = APIRouter(tags=["Scans"])


@router.get("/projects/{project_id}/scans", response_model=List[ScanRunResponse], summary="List scans for a project")
def list_scans(project_id: str, db: Session = Depends(get_db)):
    service = ScanService(db)
    items = service.list_scans(project_id)
    return [ScanRunResponse.model_validate(s) for s in items]


@router.post("/projects/{project_id}/scans", response_model=ScanRunResponse, status_code=status.HTTP_202_ACCEPTED, summary="Start a dependency scan")
def start_scan(project_id: str, payload: ScanCreate, db: Session = Depends(get_db)):
    service = ScanService(db)
    scan = service.start_scan(project_id, payload)
    return ScanRunResponse.model_validate(scan)


@router.get("/scans/{scan_id}", response_model=ScanRunResponse, summary="Get scan status and summary")
def get_scan(scan_id: str, db: Session = Depends(get_db)):
    service = ScanService(db)
    scan = service.get_scan(scan_id)
    return ScanRunResponse.model_validate(scan)


@router.post("/scans/{scan_id}/observations", response_model=ObservationBatchResponse, status_code=status.HTTP_201_CREATED, tags=["Observations"], summary="Submit observations collected by a local scanner")
def submit_observations(scan_id: str, payload: ObservationBatchCreate, db: Session = Depends(get_db)):
    service = ScanService(db)
    count, ids = service.submit_observations(scan_id, payload.observations)
    return ObservationBatchResponse(accepted_count=count, observation_ids=ids)


@router.post("/scans/{scan_id}/complete", response_model=ScanRunResponse, summary="Mark a scan as completed or failed")
def complete_scan(scan_id: str, payload: ScanCompleteRequest, db: Session = Depends(get_db)):
    service = ScanService(db)
    scan = service.complete_scan(scan_id, payload)
    return ScanRunResponse.model_validate(scan)
