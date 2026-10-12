from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundException, BadRequestException
from app.models.dependency import BaselineVersion
from app.models.baseline import ProjectBaseline
from app.repositories.baseline_repo import BaselineRepository
from app.repositories.dependency_repo import DependencyRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.activity_repo import ActivityRepository
from app.schemas.baseline import (
    BaselineCreate,
    ProjectBaselineCreate,
    ProjectBaselineCompareResponse,
)


class BaselineService:
    def __init__(self, db: Session):
        self.db = db
        self.baseline_repo = BaselineRepository(db)
        self.dep_repo = DependencyRepository(db)
        self.project_repo = ProjectRepository(db)
        self.activity_repo = ActivityRepository(db)

    # =========================================================================
    # Dependency-level Baselines
    # =========================================================================

    def get_baseline(self, baseline_id: str) -> BaselineVersion:
        baseline = self.baseline_repo.get_by_id(baseline_id)
        if not baseline:
            raise NotFoundException("Baseline", baseline_id)
        return baseline

    def list_baselines(self, dependency_id: str) -> List[BaselineVersion]:
        dep = self.dep_repo.get_by_id(dependency_id)
        if not dep:
            raise NotFoundException("Dependency", dependency_id)
        return self.baseline_repo.list_by_dependency(dependency_id)

    def create_baseline(self, dependency_id: str, data: BaselineCreate) -> BaselineVersion:
        dep = self.dep_repo.get_by_id(dependency_id)
        if not dep:
            raise NotFoundException("Dependency", dependency_id)

        baseline = self.baseline_repo.create(dependency_id, data)
        self.activity_repo.create(
            project_id=dep.project_id,
            event_type="baseline.saved",
            message=f"Saved baseline v{baseline.version_number} for dependency '{dep.name}'",
            actor_id=data.created_by,
            resource_type="baseline",
            resource_id=baseline.id,
            metadata={"version": baseline.version_number, "source": baseline.source},
        )
        return baseline

    # =========================================================================
    # Project-level Baselines
    # =========================================================================

    def create_project_baseline(
        self, project_id: str, data: ProjectBaselineCreate
    ) -> ProjectBaseline:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)

        baseline = self.baseline_repo.create_project_baseline(project_id, data)
        self.activity_repo.create(
            project_id=project_id,
            event_type="baseline.promoted" if baseline.is_promoted else "baseline.created",
            message=f"Created baseline v{baseline.version_number} ({baseline.version_tag})"
            + (" and promoted to active" if baseline.is_promoted else ""),
            actor_id=data.created_by,
            resource_type="baseline",
            resource_id=baseline.id,
            metadata={
                "version": baseline.version_number,
                "is_promoted": baseline.is_promoted,
                "content_hash": baseline.content_hash,
            },
        )
        return baseline

    def list_project_baselines(self, project_id: str) -> List[ProjectBaseline]:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)
        return self.baseline_repo.list_project_baselines(project_id)

    def get_project_baseline(self, project_id: str, baseline_id: str) -> ProjectBaseline:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)

        baseline = self.baseline_repo.get_project_baseline(project_id, baseline_id)
        if not baseline:
            raise NotFoundException("ProjectBaseline", baseline_id)
        return baseline

    def get_active_project_baseline(self, project_id: str) -> Optional[ProjectBaseline]:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)
        return self.baseline_repo.get_active_project_baseline(project_id)

    def promote_project_baseline(
        self, project_id: str, baseline_id: str, actor_id: Optional[str] = None
    ) -> ProjectBaseline:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)

        baseline = self.baseline_repo.promote_project_baseline(project_id, baseline_id, actor_id)
        if not baseline:
            raise NotFoundException("ProjectBaseline", baseline_id)

        self.activity_repo.create(
            project_id=project_id,
            event_type="baseline.promoted",
            message=f"Promoted baseline v{baseline.version_number} ({baseline.version_tag}) as active project baseline",
            actor_id=actor_id,
            resource_type="baseline",
            resource_id=baseline.id,
            metadata={"version": baseline.version_number},
        )
        return baseline

    def compare_project_baselines(
        self, project_id: str, base_ref: str, target_ref: str
    ) -> ProjectBaselineCompareResponse:
        project = self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException("Project", project_id)

        # Resolve base baseline
        base_bl = (
            self.baseline_repo.get_project_baseline(project_id, base_ref)
            if not base_ref.isdigit()
            else self.baseline_repo.get_project_baseline_by_version(project_id, int(base_ref))
        )
        if not base_bl:
            raise NotFoundException("Base baseline", base_ref)

        # Resolve target baseline
        target_bl = (
            self.baseline_repo.get_project_baseline(project_id, target_ref)
            if not target_ref.isdigit()
            else self.baseline_repo.get_project_baseline_by_version(project_id, int(target_ref))
        )
        if not target_bl:
            raise NotFoundException("Target baseline", target_ref)

        # Extract endpoint sets
        def extract_endpoints(bl: ProjectBaseline) -> Dict[str, Dict[str, Any]]:
            endpoints_map: Dict[str, Dict[str, Any]] = {}
            # From inventory
            inv = bl.inventory or {}
            for ep in inv.get("endpoints", []):
                key = f"{ep.get('method', 'GET').upper()} {ep.get('path', ep.get('endpoint_path', ''))}"
                endpoints_map[key] = ep
            # From contracts
            contracts = bl.contracts or {}
            if "paths" in contracts:
                for p, path_item in contracts["paths"].items():
                    if isinstance(path_item, dict):
                        for m, op in path_item.items():
                            if m.lower() in ("get", "post", "put", "delete", "patch", "options", "head"):
                                key = f"{m.upper()} {p}"
                                endpoints_map.setdefault(key, {"method": m.upper(), "path": p, "operation": op})
            return endpoints_map

        base_eps = extract_endpoints(base_bl)
        target_eps = extract_endpoints(target_bl)

        added = [v for k, v in target_eps.items() if k not in base_eps]
        removed = [v for k, v in base_eps.items() if k not in target_eps]
        modified = []

        for k in set(base_eps.keys()) & set(target_eps.keys()):
            if base_eps[k] != target_eps[k]:
                modified.append({
                    "endpoint": k,
                    "base": base_eps[k],
                    "target": target_eps[k],
                })

        summary = {
            "total_base_endpoints": len(base_eps),
            "total_target_endpoints": len(target_eps),
            "added_count": len(added),
            "removed_count": len(removed),
            "modified_count": len(modified),
        }

        return ProjectBaselineCompareResponse(
            project_id=project_id,
            base_version=base_bl.version_number,
            target_version=target_bl.version_number,
            base_id=base_bl.id,
            target_id=target_bl.id,
            endpoints_added=added,
            endpoints_removed=removed,
            endpoints_modified=modified,
            contract_diffs={},
            summary=summary,
        )
