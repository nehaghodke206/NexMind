import hashlib
import json
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.base import utc_now
from app.models.dependency import BaselineVersion
from app.models.baseline import ProjectBaseline
from app.models.scan import ScanRun
from app.schemas.baseline import BaselineCreate, ProjectBaselineCreate


class BaselineRepository:
    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # Dependency-level Baselines (Legacy / Granular)
    # =========================================================================

    def get_by_id(self, baseline_id: str) -> Optional[BaselineVersion]:
        return self.db.query(BaselineVersion).filter(BaselineVersion.id == baseline_id).first()

    def list_by_dependency(self, dependency_id: str) -> List[BaselineVersion]:
        return (
            self.db.query(BaselineVersion)
            .filter(BaselineVersion.dependency_id == dependency_id)
            .order_by(BaselineVersion.version_number.desc())
            .all()
        )

    def get_latest_version_number(self, dependency_id: str) -> int:
        max_v = (
            self.db.query(func.max(BaselineVersion.version_number))
            .filter(BaselineVersion.dependency_id == dependency_id)
            .scalar()
        )
        return max_v if max_v is not None else 0

    def create(self, dependency_id: str, data: BaselineCreate) -> BaselineVersion:
        next_version = self.get_latest_version_number(dependency_id) + 1
        serialized = json.dumps(data.contract, sort_keys=True)
        content_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        baseline = BaselineVersion(
            dependency_id=dependency_id,
            version_number=next_version,
            contract=data.contract,
            source=data.source,
            content_hash=content_hash,
            created_by=data.created_by,
            notes=data.notes,
        )
        self.db.add(baseline)
        self.db.commit()
        self.db.refresh(baseline)
        return baseline

    # =========================================================================
    # Project-level Baselines (Milestone 6)
    # =========================================================================

    def get_latest_project_version_number(self, project_id: str) -> int:
        max_v = (
            self.db.query(func.max(ProjectBaseline.version_number))
            .filter(ProjectBaseline.project_id == project_id)
            .scalar()
        )
        return max_v if max_v is not None else 0

    def create_project_baseline(
        self, project_id: str, data: ProjectBaselineCreate
    ) -> ProjectBaseline:
        next_version = self.get_latest_project_version_number(project_id) + 1
        contracts = data.contracts if data.contracts is not None else {}
        inventory = data.inventory if data.inventory is not None else {}
        combined = {
            "contracts": contracts,
            "inventory": inventory,
        }
        serialized = json.dumps(combined, sort_keys=True)
        content_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        # Sanitize source_scan_id to prevent ForeignKeyViolation
        resolved_scan_id = None
        if data.source_scan_id:
            candidate = str(data.source_scan_id).strip()
            if candidate:
                # 1. Match by primary key id
                scan = self.db.query(ScanRun).filter(ScanRun.id == candidate).first()
                if not scan:
                    # 2. Match by client_run_id
                    scan = self.db.query(ScanRun).filter(ScanRun.client_run_id == candidate).first()
                if scan:
                    resolved_scan_id = scan.id

        now = utc_now()
        is_promoted = bool(data.is_promoted)
        notes = data.notes or getattr(data, "description", None)

        if is_promoted:
            # Deactivate previous active baselines
            self.db.query(ProjectBaseline).filter(
                ProjectBaseline.project_id == project_id,
                ProjectBaseline.is_active == True,
            ).update({"is_active": False, "updated_at": now})

        baseline = ProjectBaseline(
            project_id=project_id,
            version_number=next_version,
            version_tag=data.version_tag or f"v{next_version}.0",
            contracts=contracts,
            inventory=inventory,
            source_scan_id=resolved_scan_id,
            content_hash=content_hash,
            created_by=data.created_by,
            is_active=is_promoted,
            is_promoted=is_promoted,
            promoted_at=now if is_promoted else None,
            promoted_by=data.created_by if is_promoted else None,
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        self.db.add(baseline)
        self.db.commit()
        self.db.refresh(baseline)
        return baseline

    def list_project_baselines(self, project_id: str) -> List[ProjectBaseline]:
        return (
            self.db.query(ProjectBaseline)
            .filter(ProjectBaseline.project_id == project_id)
            .order_by(ProjectBaseline.version_number.desc())
            .all()
        )

    def get_project_baseline(self, project_id: str, baseline_id: str) -> Optional[ProjectBaseline]:
        return (
            self.db.query(ProjectBaseline)
            .filter(
                ProjectBaseline.project_id == project_id,
                ProjectBaseline.id == baseline_id,
            )
            .first()
        )

    def get_project_baseline_by_version(
        self, project_id: str, version_number: int
    ) -> Optional[ProjectBaseline]:
        return (
            self.db.query(ProjectBaseline)
            .filter(
                ProjectBaseline.project_id == project_id,
                ProjectBaseline.version_number == version_number,
            )
            .first()
        )

    def get_active_project_baseline(self, project_id: str) -> Optional[ProjectBaseline]:
        return (
            self.db.query(ProjectBaseline)
            .filter(
                ProjectBaseline.project_id == project_id,
                ProjectBaseline.is_active == True,
            )
            .first()
        )

    def promote_project_baseline(
        self, project_id: str, baseline_id: str, actor_id: Optional[str] = None
    ) -> Optional[ProjectBaseline]:
        target = self.get_project_baseline(project_id, baseline_id)
        if not target:
            return None

        now = utc_now()
        # Deactivate all active baselines in project
        self.db.query(ProjectBaseline).filter(
            ProjectBaseline.project_id == project_id,
            ProjectBaseline.is_active == True,
        ).update({"is_active": False, "updated_at": now})

        target.is_active = True
        target.is_promoted = True
        target.promoted_at = now
        target.promoted_by = actor_id
        target.updated_at = now

        self.db.commit()
        self.db.refresh(target)
        return target
