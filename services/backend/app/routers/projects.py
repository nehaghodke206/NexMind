from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.project_service import ProjectService
from app.services.activity_service import ActivityService
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectListResponse,
    ProjectMemberCreate,
    ProjectMemberResponse,
)
from app.schemas.activity import ActivityEventListResponse, ActivityEventResponse
from app.schemas.dashboard import ProjectSummaryResponse

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=ProjectListResponse, summary="List projects")
def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service = ProjectService(db)
    items, total = service.list_projects(page=page, page_size=page_size)
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, summary="Create a project")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    service = ProjectService(db)
    project = service.create_project(payload)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse, summary="Get project details")
def get_project(project_id: str, db: Session = Depends(get_db)):
    service = ProjectService(db)
    project = service.get_project(project_id)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse], tags=["Members"], summary="List project members")
def list_members(project_id: str, db: Session = Depends(get_db)):
    service = ProjectService(db)
    members = service.list_members(project_id)
    return [ProjectMemberResponse.model_validate(m) for m in members]


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED, tags=["Members"], summary="Add a member to a project")
def add_member(project_id: str, payload: ProjectMemberCreate, db: Session = Depends(get_db)):
    service = ProjectService(db)
    member = service.add_member(project_id, payload)
    return ProjectMemberResponse.model_validate(member)


@router.get("/{project_id}/activity", response_model=ActivityEventListResponse, tags=["Activity"], summary="Get project activity history")
def list_activity(
    project_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service = ActivityService(db)
    items, total = service.list_activity(project_id, page=page, page_size=page_size)
    return ActivityEventListResponse(
        items=[ActivityEventResponse.model_validate(e) for e in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{project_id}/summary", response_model=ProjectSummaryResponse, tags=["Dashboard"], summary="Get manager dashboard summary")
def get_project_summary(project_id: str, db: Session = Depends(get_db)):
    service = ProjectService(db)
    return service.get_project_summary(project_id)
