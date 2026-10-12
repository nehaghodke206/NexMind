from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.base import utc_now
from app.models.scan import ScanRun
from app.schemas.scan import ScanCreate, ScanCompleteRequest, ScanIngestRequest


class ScanRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, scan_id: str) -> Optional[ScanRun]:
        return self.db.query(ScanRun).filter(ScanRun.id == scan_id).first()

    def find_by_client_run_id(self, project_id: str, client_run_id: str) -> Optional[ScanRun]:
        return (
            self.db.query(ScanRun)
            .filter(
                ScanRun.project_id == project_id,
                ScanRun.client_run_id == client_run_id,
            )
            .first()
        )

    def list_by_project(self, project_id: str, limit: int = 50) -> List[ScanRun]:
        return (
            self.db.query(ScanRun)
            .filter(ScanRun.project_id == project_id)
            .order_by(ScanRun.started_at.desc())
            .limit(limit)
            .all()
        )

    def create(self, project_id: str, data: ScanCreate) -> ScanRun:
        scan = ScanRun(
            project_id=project_id,
            dependency_id=data.dependency_id,
            initiated_by=data.initiated_by,
            scan_type=data.scan_type,
            detection_mode=data.detection_mode or "algorithmic",
            trigger_type=data.trigger_type or "manual",
            status="running",
            started_at=utc_now(),
        )
        self.db.add(scan)
        self.db.commit()
        self.db.refresh(scan)
        return scan

    def create_ingested(self, project_id: str, data: ScanIngestRequest) -> ScanRun:
        # Check idempotency via client_run_id
        if data.client_run_id:
            existing = self.find_by_client_run_id(project_id, data.client_run_id)
            if existing:
                return existing

        now = utc_now()
        started_at = data.started_at or now
        completed_at = data.completed_at or now

        duration = data.duration_seconds
        if duration is None and started_at and completed_at:
            s_at = started_at if started_at.tzinfo else started_at.replace(tzinfo=timezone.utc)
            c_at = completed_at if completed_at.tzinfo else completed_at.replace(tzinfo=timezone.utc)
            duration = max(0.0, (c_at - s_at).total_seconds())

        scan = ScanRun(
            project_id=project_id,
            client_run_id=data.client_run_id,
            scan_type=data.scan_type,
            detection_mode=data.detection_mode,
            capabilities_executed=data.capabilities_executed,
            duration_seconds=duration,
            summary_counts=data.summary_counts,
            findings_json=data.findings,
            summary=f"Ingested scan: {data.summary_counts.get('findings_total', len(data.findings))} findings",
            summary_json=data.summary_counts,
            error_message=data.error_message,
            status=data.status,
            is_local=True,
            sync_status="synchronized",
            scanner_version=data.scanner_version,
            repository_revision=data.repository_revision,
            initiated_by=data.initiated_by,
            started_at=started_at,
            completed_at=completed_at,
            created_at=now,
        )
        self.db.add(scan)
        self.db.commit()
        self.db.refresh(scan)
        return scan

    def complete(self, scan: ScanRun, data: ScanCompleteRequest) -> ScanRun:
        scan.status = data.status
        scan.summary = data.summary
        scan.error_message = data.error_message
        now = utc_now()
        scan.completed_at = now
        if data.duration_seconds is not None:
            scan.duration_seconds = data.duration_seconds
        elif scan.started_at:
            started = scan.started_at if scan.started_at.tzinfo else scan.started_at.replace(tzinfo=timezone.utc)
            scan.duration_seconds = max(0.0, (now - started).total_seconds())
        if data.summary_counts:
            scan.summary_counts = data.summary_counts
        self.db.commit()
        self.db.refresh(scan)
        return scan
