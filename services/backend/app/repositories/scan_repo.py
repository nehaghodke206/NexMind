from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.scan import ScanRun
from app.schemas.scan import ScanCreate, ScanCompleteRequest


class ScanRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, scan_id: str) -> Optional[ScanRun]:
        return self.db.query(ScanRun).filter(ScanRun.id == scan_id).first()

    def list_by_project(self, project_id: str) -> List[ScanRun]:
        return (
            self.db.query(ScanRun)
            .filter(ScanRun.project_id == project_id)
            .order_by(ScanRun.started_at.desc())
            .all()
        )

    def create(self, project_id: str, data: ScanCreate) -> ScanRun:
        scan = ScanRun(
            project_id=project_id,
            dependency_id=data.dependency_id,
            initiated_by=data.initiated_by,
            scan_type=data.scan_type,
            status="running",
        )
        self.db.add(scan)
        self.db.commit()
        self.db.refresh(scan)
        return scan

    def complete(self, scan: ScanRun, data: ScanCompleteRequest) -> ScanRun:
        scan.status = data.status
        scan.summary = data.summary
        scan.error_message = data.error_message
        scan.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(scan)
        return scan
