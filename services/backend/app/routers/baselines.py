from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.services.baseline_service import BaselineService
from app.schemas.baseline import (
    BaselineCreate,
    BaselineResponse,
    ProjectBaselineCreate,
    ProjectBaselineResponse,
    ProjectBaselineListResponse,
    ProjectBaselineCompareResponse,
)

router = APIRouter(tags=["Baselines"])


# =============================================================================
# Project-level Baselines (Milestone 6)
# =============================================================================

@router.get(
    "/projects/{project_id}/baselines",
    response_model=ProjectBaselineListResponse,
    summary="List all versioned baselines for a project",
)
def list_project_baselines(project_id: str, db: Session = Depends(get_db)):
    service = BaselineService(db)
    items = service.list_project_baselines(project_id)
    active = service.get_active_project_baseline(project_id)
    return ProjectBaselineListResponse(
        items=[ProjectBaselineResponse.model_validate(b) for b in items],
        total=len(items),
        active_baseline=ProjectBaselineResponse.model_validate(active) if active else None,
    )


@router.post(
    "/projects/{project_id}/baselines",
    response_model=ProjectBaselineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new versioned baseline snapshot for a project",
)
def create_project_baseline(
    project_id: str, payload: ProjectBaselineCreate, db: Session = Depends(get_db)
):
    service = BaselineService(db)
    baseline = service.create_project_baseline(project_id, payload)
    return ProjectBaselineResponse.model_validate(baseline)


@router.get(
    "/projects/{project_id}/baselines/active",
    response_model=Optional[ProjectBaselineResponse],
    summary="Get the currently promoted/active baseline for a project",
)
def get_active_project_baseline(project_id: str, db: Session = Depends(get_db)):
    service = BaselineService(db)
    baseline = service.get_active_project_baseline(project_id)
    if not baseline:
        return None
    return ProjectBaselineResponse.model_validate(baseline)


@router.get(
    "/projects/{project_id}/baselines/compare",
    response_model=ProjectBaselineCompareResponse,
    summary="Compare two baseline versions for a project",
)
def compare_project_baselines(
    project_id: str,
    base: str = Query(..., description="Base baseline ID or version number"),
    target: str = Query(..., description="Target baseline ID or version number"),
    db: Session = Depends(get_db),
):
    service = BaselineService(db)
    return service.compare_project_baselines(project_id, base, target)


@router.get(
    "/projects/{project_id}/baselines/{baseline_id}",
    response_model=ProjectBaselineResponse,
    summary="Get baseline details and snapshot for a project",
)
def get_project_baseline(project_id: str, baseline_id: str, db: Session = Depends(get_db)):
    service = BaselineService(db)
    baseline = service.get_project_baseline(project_id, baseline_id)
    return ProjectBaselineResponse.model_validate(baseline)


@router.post(
    "/projects/{project_id}/baselines/{baseline_id}/promote",
    response_model=ProjectBaselineResponse,
    summary="Explicitly promote a baseline version to be the active reference for the project",
)
def promote_project_baseline(
    project_id: str,
    baseline_id: str,
    promoted_by: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    service = BaselineService(db)
    baseline = service.promote_project_baseline(project_id, baseline_id, actor_id=promoted_by)
    return ProjectBaselineResponse.model_validate(baseline)


# =============================================================================
# Legacy / Dependency-level Baselines
# =============================================================================

@router.get(
    "/dependencies/{dependency_id}/baselines",
    response_model=List[BaselineResponse],
    summary="List saved baselines for a dependency",
)
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


@router.post(
    "/dependencies/{dependency_id}/baselines",
    response_model=BaselineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a baseline for a dependency",
)
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


# =============================================================================
# Top-Level Baselines Routes (Active Project Resolution)
# =============================================================================

@router.post(
    "/baselines",
    response_model=ProjectBaselineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new versioned baseline snapshot (resolving project from query or active project)",
)
def create_baseline_top_level(
    payload: Optional[ProjectBaselineCreate] = None,
    project_id: Optional[str] = Query(None, description="Target project ID"),
    db: Session = Depends(get_db),
):
    service = BaselineService(db)
    target_project_id = project_id
    if not target_project_id:
        projects, _ = service.project_repo.list_paginated(page=1, page_size=1)
        if not projects:
            raise NotFoundException("Project", "default")
        target_project_id = projects[0].id

    actual_payload = payload or ProjectBaselineCreate()
    baseline = service.create_project_baseline(target_project_id, actual_payload)
    return ProjectBaselineResponse.model_validate(baseline)


@router.get(
    "/baselines",
    response_model=ProjectBaselineListResponse,
    summary="List all versioned baselines for a project (resolving from query or active project)",
)
def list_baselines_top_level(
    project_id: Optional[str] = Query(None, description="Target project ID"),
    db: Session = Depends(get_db),
):
    service = BaselineService(db)
    target_project_id = project_id
    if not target_project_id:
        projects, _ = service.project_repo.list_paginated(page=1, page_size=1)
        if not projects:
            return ProjectBaselineListResponse(items=[], total=0, active_baseline=None)
        target_project_id = projects[0].id
    items = service.list_project_baselines(target_project_id)
    active = service.get_active_project_baseline(target_project_id)
    return ProjectBaselineListResponse(
        items=[ProjectBaselineResponse.model_validate(b) for b in items],
        total=len(items),
        active_baseline=ProjectBaselineResponse.model_validate(active) if active else None,
    )


@router.get(
    "/baselines/active",
    response_model=Optional[ProjectBaselineResponse],
    summary="Get active reference baseline for a project (resolving from query or active project)",
)
def get_active_baseline_top_level(
    project_id: Optional[str] = Query(None, description="Target project ID"),
    db: Session = Depends(get_db),
):
    service = BaselineService(db)
    target_project_id = project_id
    if not target_project_id:
        projects, _ = service.project_repo.list_paginated(page=1, page_size=1)
        if not projects:
            return None
        target_project_id = projects[0].id
    baseline = service.get_active_project_baseline(target_project_id)
    if not baseline:
        return None
    return ProjectBaselineResponse.model_validate(baseline)


@router.get(
    "/baselines/compare",
    response_model=ProjectBaselineCompareResponse,
    summary="Compare two baseline versions (resolving project from query or active project)",
)
def compare_baselines_top_level(
    base: str = Query(..., description="Base baseline ID or version number"),
    target: str = Query(..., description="Target baseline ID or version number"),
    project_id: Optional[str] = Query(None, description="Target project ID"),
    db: Session = Depends(get_db),
):
    service = BaselineService(db)
    target_project_id = project_id
    if not target_project_id:
        projects, _ = service.project_repo.list_paginated(page=1, page_size=1)
        if not projects:
            raise NotFoundException("Project", "default")
        target_project_id = projects[0].id
    return service.compare_project_baselines(target_project_id, base, target)


@router.get(
    "/baselines/{baseline_id}",
    response_model=BaselineResponse,
    summary="Get baseline details and captured contract",
)
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

