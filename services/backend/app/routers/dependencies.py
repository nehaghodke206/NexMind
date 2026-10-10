from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.dependency_service import DependencyService
from app.schemas.dependency import (
    DependencyCreate,
    DependencyUpdate,
    DependencyResponse,
)

router = APIRouter(tags=["Dependencies"])


@router.get("/projects/{project_id}/dependencies", response_model=List[DependencyResponse], summary="List dependencies registered for a project")
def list_dependencies(project_id: str, db: Session = Depends(get_db)):
    service = DependencyService(db)
    items = service.list_dependencies(project_id)
    return [DependencyResponse.model_validate(d) for d in items]


@router.post("/projects/{project_id}/dependencies", response_model=DependencyResponse, status_code=status.HTTP_201_CREATED, summary="Register a dependency")
def create_dependency(project_id: str, payload: DependencyCreate, db: Session = Depends(get_db)):
    service = DependencyService(db)
    dep = service.create_dependency(project_id, payload)
    return DependencyResponse.model_validate(dep)


@router.get("/dependencies/{dependency_id}", response_model=DependencyResponse, summary="Get dependency details")
def get_dependency(dependency_id: str, db: Session = Depends(get_db)):
    service = DependencyService(db)
    dep = service.get_dependency(dependency_id)
    return DependencyResponse.model_validate(dep)


@router.patch("/dependencies/{dependency_id}", response_model=DependencyResponse, summary="Update dependency metadata or configuration")
def update_dependency(dependency_id: str, payload: DependencyUpdate, db: Session = Depends(get_db)):
    service = DependencyService(db)
    dep = service.update_dependency(dependency_id, payload)
    return DependencyResponse.model_validate(dep)
