from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.baseline_service import BaselineService
from app.schemas.baseline import BaselineCreate, BaselineResponse

router = APIRouter(tags=["Baselines"])


@router.get("/dependencies/{dependency_id}/baselines", response_model=List[BaselineResponse], summary="List saved baselines for a dependency")
def list_baselines(dependency_id: str, db: Session = Depends(get_db)):
    service = BaselineService(db)
    items = service.list_baselines(dependency_id)
    return [
        BaselineResponse(
            id=b.id,
            dependency_id=b.dependency_id,
            version=b.version_number,
            contract=b.contract,
            source=b.source,
            created_by=b.created_by,
            created_at=b.created_at,
        )
        for b in items
    ]


@router.post("/dependencies/{dependency_id}/baselines", response_model=BaselineResponse, status_code=status.HTTP_201_CREATED, summary="Save a baseline for a dependency")
def create_baseline(dependency_id: str, payload: BaselineCreate, db: Session = Depends(get_db)):
    service = BaselineService(db)
    b = service.create_baseline(dependency_id, payload)
    return BaselineResponse(
        id=b.id,
        dependency_id=b.dependency_id,
        version=b.version_number,
        contract=b.contract,
        source=b.source,
        created_by=b.created_by,
        created_at=b.created_at,
    )


@router.get("/baselines/{baseline_id}", response_model=BaselineResponse, summary="Get baseline details and captured contract")
def get_baseline(baseline_id: str, db: Session = Depends(get_db)):
    service = BaselineService(db)
    b = service.get_baseline(baseline_id)
    return BaselineResponse(
        id=b.id,
        dependency_id=b.dependency_id,
        version=b.version_number,
        contract=b.contract,
        source=b.source,
        created_by=b.created_by,
        created_at=b.created_at,
    )
