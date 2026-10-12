import logging
from typing import List, Tuple
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundException
from app.models.scan import ScanRun
from app.models.observation import Observation
from app.repositories.scan_repo import ScanRepository
from app.repositories.observation_repo import ObservationRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.dependency_repo import DependencyRepository
from app.repositories.incident_repo import IncidentRepository
from app.repositories.activity_repo import ActivityRepository
from app.schemas.scan import ScanCreate, ScanCompleteRequest, ScanIngestRequest
from app.schemas.observation import ObservationCreate
from app.schemas.incident import IncidentCreate
from app.schemas.dependency import DependencyCreate

logger = logging.getLogger(__name__)


class ScanService:
    def __init__(self, db: Session):
        self.db = db
        self.scan_repo = ScanRepository(db)
        self.obs_repo = ObservationRepository(db)
        self.project_repo = ProjectRepository(db)
        self.dep_repo = DependencyRepository(db)
        self.incident_repo = IncidentRepository(db)
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

    def ingest_scan(self, project_id: str, data: ScanIngestRequest) -> ScanRun:
        """
        Ingest a locally executed scan from VS Code, synchronize findings into incidents,
        and handle retries idempotently via client_run_id.
        """
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)

        # Check if already ingested with client_run_id
        is_retry = False
        if data.client_run_id:
            existing = self.scan_repo.find_by_client_run_id(project_id, data.client_run_id)
            if existing:
                is_retry = True

        scan = self.scan_repo.create_ingested(project_id, data)

        # If not a duplicate retry, synchronize findings into project incidents
        synced_count = 0
        reopened_count = 0
        deduped_count = 0

        if not is_retry and data.findings:
            # Get default dependency or create placeholder if none exists
            default_dep = None
            deps = self.dep_repo.list_by_project(project_id)
            if deps:
                default_dep = deps[0]

            for f in data.findings:
                fp = f.get("fingerprint")
                path_str = f.get("path") or "/"
                method_str = f.get("method") or "ALL"
                rule_id = f.get("rule_id") or "RULE-UNKNOWN"
                if not fp:
                    fp = f"{rule_id}:{method_str}:{path_str}"

                sev = (f.get("severity") or "medium").lower()
                if sev not in ("low", "medium", "high", "critical", "blocked"):
                    sev = "medium"

                prov = f.get("provenance") or "contract_diff"
                title = f.get("title") or f.get("message") or f"{rule_id}: {method_str} {path_str}"

                dep_id = f.get("dependency_id")
                if not dep_id and default_dep:
                    dep_id = default_dep.id
                elif not dep_id:
                    # Create or resolve a root dependency container for project
                    dep = self.dep_repo.create(
                        project_id=project_id,
                        data=DependencyCreate(
                            name=path_str if path_str != "/" else "Root API",
                            kind="rest_api",
                        ),
                    )
                    default_dep = dep
                    dep_id = dep.id

                inc_payload = IncidentCreate(
                    dependency_id=dep_id,
                    title=title,
                    description=f.get("description") or f.get("message") or title,
                    change_type=rule_id,
                    severity=sev,
                    provenance=prov,
                    confidence=f.get("confidence"),
                    fingerprint=fp,
                    recommended_action=f.get("recommended_action"),
                    affected_files=f.get("evidence", {}).get("affected_files") or (
                        [f["evidence"]["file"]] if isinstance(f.get("evidence"), dict) and "file" in f["evidence"] else []
                    ),
                    evidence=f.get("evidence") if isinstance(f.get("evidence"), dict) else {},
                )

                existing_inc = self.incident_repo.find_by_fingerprint(project_id, fp)
                if existing_inc:
                    _, was_reopened = self.incident_repo.update_dedup(
                        existing_inc, inc_payload, scan_id=scan.id
                    )
                    if was_reopened:
                        reopened_count += 1
                    else:
                        deduped_count += 1
                else:
                    self.incident_repo.create(project_id, inc_payload, scan_id=scan.id)
                    synced_count += 1

        self.activity_repo.create(
            project_id=project_id,
            event_type="scan.ingested",
            message=f"Ingested scan run {scan.id} (Status: {scan.status}, New: {synced_count}, Reopened: {reopened_count}, Deduped: {deduped_count})",
            resource_type="scan",
            resource_id=scan.id,
            metadata={
                "client_run_id": data.client_run_id,
                "detection_mode": data.detection_mode,
                "synced_incidents": synced_count,
                "reopened_incidents": reopened_count,
            },
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
            event_type="scan.completed" if data.status in ("completed", "succeeded") else "scan.failed",
            message=f"Scan {scan_id} {data.status}"
            + (f": {data.summary}" if data.summary else ""),
            resource_type="scan",
            resource_id=scan_id,
        )
        return completed
