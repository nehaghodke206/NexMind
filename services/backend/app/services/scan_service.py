from typing import List, Tuple
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundException
from app.models.scan import ScanRun
from app.models.observation import Observation
from app.repositories.scan_repo import ScanRepository
from app.repositories.observation_repo import ObservationRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.dependency_repo import DependencyRepository
from app.repositories.activity_repo import ActivityRepository
from app.schemas.scan import ScanCreate, ScanCompleteRequest
from app.schemas.observation import ObservationCreate


class ScanService:
    def __init__(self, db: Session):
        self.db = db
        self.scan_repo = ScanRepository(db)
        self.obs_repo = ObservationRepository(db)
        self.project_repo = ProjectRepository(db)
        self.dep_repo = DependencyRepository(db)
        self.activity_repo = ActivityRepository(db)

    def get_scan(self, scan_id: str) -> ScanRun:
        scan = self.scan_repo.get_by_id(scan_id)
        if not scan:
            raise NotFoundException("ScanRun", scan_id)
        return scan

    def list_scans(self, project_id: str) -> List[ScanRun]:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)
        return self.scan_repo.list_by_project(project_id)

    def start_scan(self, project_id: str, data: ScanCreate) -> ScanRun:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)
        if data.dependency_id:
            dep = self.dep_repo.get_by_id(data.dependency_id)
            if not dep:
                raise NotFoundException("Dependency", data.dependency_id)

        scan = self.scan_repo.create(project_id, data)
        self.activity_repo.create(
            project_id=project_id,
            event_type="scan.started",
            message=f"Scan {scan.id} started ({scan.scan_type})",
            actor_id=data.initiated_by,
            resource_type="scan",
            resource_id=scan.id,
        )
        return scan

    def submit_observations(
        self, scan_id: str, items: List[ObservationCreate]
    ) -> Tuple[int, List[str]]:
        scan = self.get_scan(scan_id)

        # Validate that referenced dependencies exist
        for item in items:
            dep = self.dep_repo.get_by_id(item.dependency_id)
            if not dep:
                raise NotFoundException("Dependency", item.dependency_id)

        created_obs = self.obs_repo.create_batch(scan_id, items)
        obs_ids = [obs.id for obs in created_obs]

        self.activity_repo.create(
            project_id=scan.project_id,
            event_type="observations.recorded",
            message=f"Recorded {len(obs_ids)} observations under scan {scan_id}",
            resource_type="scan",
            resource_id=scan_id,
            metadata={"observation_count": len(obs_ids)},
        )
        return len(obs_ids), obs_ids

    def complete_scan(self, scan_id: str, data: ScanCompleteRequest) -> ScanRun:
        scan = self.get_scan(scan_id)
        completed = self.scan_repo.complete(scan, data)
        self.activity_repo.create(
            project_id=scan.project_id,
            event_type="scan.completed" if data.status == "completed" else "scan.failed",
            message=f"Scan {scan_id} {data.status}"
            + (f": {data.summary}" if data.summary else ""),
            resource_type="scan",
            resource_id=scan_id,
        )
        return completed
