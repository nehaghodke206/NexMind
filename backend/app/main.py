"""FastAPI entry point for Dependency Guardian backend."""

import asyncio
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx

from .config import load_guardian_config, GuardianConfig
from .models import (
    ScanResult,
    ChangeItem,
    ImpactItem,
    RepairProposal,
    ValidationResult,
    RepairStatus,
)
from .db import Database
from .probe_runner import execute_probe
from .change_detector import detect_changes
from .impact_mapper import map_change_impact
from .repair_planner import plan_repair
from .validation_runner import run_validation
from .repair_applier import RepairApplier
from .audit_logger import AuditLogger

# Determine workspace root
WORKSPACE_ROOT = os.path.abspath(
    os.environ.get("GUARDIAN_WORKSPACE_ROOT", os.path.join(os.path.dirname(__file__), "..", ".."))
)
CONFIG_FILE = os.path.join(WORKSPACE_ROOT, "dependency-guardian.yml")
DB_FILE = os.path.join(WORKSPACE_ROOT, "dependency_guardian.db")

app = FastAPI(
    title="Dependency Guardian Local Backend",
    version="1.1",
    description="Detecting, explaining, and safely adapting external dependency changes",
)

# Enable CORS for local extension webviews
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database(db_path=DB_FILE)
audit_logger = AuditLogger(db=db)
applier = RepairApplier(workspace_root=WORKSPACE_ROOT)


def get_config() -> GuardianConfig:
    if not os.path.exists(CONFIG_FILE):
        raise HTTPException(
            status_code=404,
            detail=f"Configuration file not found at: {CONFIG_FILE}. Please initialize project.",
        )
    try:
        return load_guardian_config(CONFIG_FILE)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Configuration validation failed: {str(e)}",
        )


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "product": "Dependency Guardian",
        "version": "1.1",
        "workspace_root": WORKSPACE_ROOT,
        "config_exists": os.path.exists(CONFIG_FILE),
    }


@app.post("/api/projects/initialize")
async def initialize_project():
    cfg = get_config()
    audit_logger.log("project_initialized", "project", cfg.project.name, {"config_path": CONFIG_FILE})
    return {
        "status": "initialized",
        "project_name": cfg.project.name,
        "validation_command": cfg.project.validation_command,
        "dependencies_count": len(cfg.dependencies),
        "workflows_count": len(cfg.workflows),
    }


@app.get("/api/services")
async def get_services():
    cfg = get_config()
    services_list = []
    for dep in cfg.dependencies:
        dep_data = {
            "id": dep.id,
            "name": dep.name,
            "base_url": dep.base_url,
            "probes": [p.model_dump() for p in dep.probes],
        }
        services_list.append(dep_data)
    return {"services": services_list}


@app.post("/api/baselines")
async def create_baselines():
    """Probes all configured endpoints and creates/preserves versioned baselines."""
    cfg = get_config()
    created_baselines = []
    created_at = datetime.now(timezone.utc).isoformat()

    for dep in cfg.dependencies:
        for probe in dep.probes:
            res = await execute_probe(dep, probe, cfg.settings)
            existing = db.get_latest_baseline(dep.id, probe.id)
            new_version = (existing["version"] + 1) if existing else 1

            baseline_record = {
                "id": f"base_{dep.id}_{probe.id}_v{new_version}",
                "dependency_id": dep.id,
                "probe_id": probe.id,
                "version": new_version,
                "fingerprint": res.fingerprint,
                "raw_response": {
                    "status_code": res.status_code,
                    "body": res.body,
                    "headers": res.headers,
                },
                "created_at": created_at,
                "created_by_action": "manual_baseline_creation",
            }
            db.save_baseline(baseline_record)
            created_baselines.append(baseline_record)

    audit_logger.log(
        "baseline_created",
        "baseline_group",
        f"v_{created_at}",
        {"count": len(created_baselines)},
    )
    return {"status": "success", "baselines": created_baselines}


@app.get("/api/baselines")
async def list_baselines():
    return {"baselines": db.list_baselines()}


@app.post("/api/scans")
async def run_scan():
    """Runs a manual scan across all services, compares with baselines, and maps impact."""
    cfg = get_config()
    scan_id = f"scan_{uuid.uuid4().hex[:8]}"
    start_time = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()

    detected_changes: List[ChangeItem] = []
    services_checked = len(cfg.dependencies)

    for dep in cfg.dependencies:
        for probe in dep.probes:
            obs = await execute_probe(dep, probe, cfg.settings)

            # Persist observation
            obs_record = {
                "id": f"obs_{uuid.uuid4().hex[:8]}",
                "dependency_id": dep.id,
                "probe_id": probe.id,
                "scan_id": scan_id,
                "status_code": obs.status_code,
                "normalized_fingerprint": obs.fingerprint,
                "safe_response_snapshot": obs.body,
                "latency_ms": obs.latency_ms,
                "observed_at": obs.observed_at,
            }
            db.save_observation(obs_record)

            # Fetch baseline for comparison
            baseline = db.get_latest_baseline(dep.id, probe.id)
            if not baseline:
                # No baseline yet; prompt baseline creation
                continue

            # Check for differences against baseline
            changes = detect_changes(scan_id, probe, baseline, obs)
            for chg in changes:
                db.save_change(chg.model_dump())
                detected_changes.append(chg)

                # Compute and persist impact
                impacts = map_change_impact(chg, cfg)
                for imp in impacts:
                    imp_record = {
                        "id": f"imp_{uuid.uuid4().hex[:8]}",
                        "change_id": chg.id,
                        "workflow_id": imp.workflow_id,
                        "workflow_name": imp.workflow_name,
                        "source_files": imp.source_files,
                        "tests": imp.tests,
                        "affected_fields": imp.affected_fields,
                        "reason": imp.reason,
                    }
                    db.save_impact(imp_record)

    duration_ms = (time.perf_counter() - start_time) * 1000.0

    scan_result = {
        "scan_id": scan_id,
        "status": "completed",
        "services_checked": services_checked,
        "changes_detected": len(detected_changes),
        "started_at": started_at,
        "duration_ms": round(duration_ms, 2),
    }
    db.save_scan(scan_result)

    audit_logger.log(
        "scan_completed",
        "scan",
        scan_id,
        {"services_checked": services_checked, "changes_detected": len(detected_changes)},
    )

    return ScanResult(
        scan_id=scan_id,
        status="completed",
        services_checked=services_checked,
        changes_detected=len(detected_changes),
        started_at=started_at,
        duration_ms=round(duration_ms, 2),
        changes=detected_changes,
    )


@app.get("/api/scans/{scan_id}")
async def get_scan_details(scan_id: str):
    scan = db.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    changes = db.list_changes(scan_id=scan_id)
    scan["changes"] = changes
    return scan


@app.get("/api/changes")
async def list_changes(scan_id: Optional[str] = None):
    return {"changes": db.list_changes(scan_id=scan_id)}


@app.get("/api/changes/{change_id}")
async def get_change_details(change_id: str):
    chg = db.get_change(change_id)
    if not chg:
        raise HTTPException(status_code=404, detail="Change not found")
    return chg


@app.get("/api/changes/{change_id}/impact")
async def get_change_impact(change_id: str):
    impacts = db.get_impacts_for_change(change_id)
    return {"impacts": impacts}


@app.post("/api/changes/{change_id}/repair-proposals")
async def create_repair_proposal(change_id: str):
    cfg = get_config()
    chg_data = db.get_change(change_id)
    if not chg_data:
        raise HTTPException(status_code=404, detail="Change not found")

    chg = ChangeItem(**chg_data)
    proposal = plan_repair(chg, cfg, WORKSPACE_ROOT)
    db.save_repair(proposal.model_dump())

    audit_logger.log(
        "repair_proposed",
        "repair",
        proposal.id,
        {"type": proposal.repair_type, "status": proposal.status.value},
    )

    return proposal


@app.get("/api/repairs/{repair_id}")
async def get_repair(repair_id: str):
    rep = db.get_repair(repair_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Repair not found")
    validations = db.get_validations_for_repair(repair_id)
    rep["validations"] = validations
    return rep


@app.post("/api/repairs/{repair_id}/validate")
async def validate_repair_proposal(repair_id: str):
    cfg = get_config()
    rep_data = db.get_repair(repair_id)
    if not rep_data:
        raise HTTPException(status_code=404, detail="Repair proposal not found")

    repair = RepairProposal(**rep_data)
    if repair.status == RepairStatus.BLOCKED_UNCERTAIN:
        raise HTTPException(
            status_code=400,
            detail="Cannot validate repair: Proposal is blocked due to semantic uncertainty.",
        )

    val_result = await asyncio.to_thread(run_validation, repair, cfg, WORKSPACE_ROOT)
    db.save_validation(val_result.model_dump())

    new_status = (
        RepairStatus.VALIDATION_PASSED
        if val_result.status == "passed"
        else RepairStatus.VALIDATION_FAILED
    )
    db.update_repair_status(repair.id, new_status.value)

    audit_logger.log(
        "validation_executed",
        "repair",
        repair.id,
        {"status": val_result.status, "exit_code": val_result.exit_code},
    )

    return val_result


@app.post("/api/repairs/{repair_id}/apply")
async def apply_repair_proposal(repair_id: str):
    rep_data = db.get_repair(repair_id)
    if not rep_data:
        raise HTTPException(status_code=404, detail="Repair proposal not found")

    repair = RepairProposal(**rep_data)

    # Safety Gating: Check status
    if repair.status == RepairStatus.BLOCKED_UNCERTAIN:
        raise HTTPException(
            status_code=400,
            detail="REPAIR BLOCKED: Cannot apply repair for uncertain semantic changes.",
        )
    if repair.status == RepairStatus.VALIDATION_FAILED:
        raise HTTPException(
            status_code=400,
            detail="REPAIR BLOCKED: Cannot apply repair when validation has failed.",
        )

    success, msg = applier.apply_repair(repair)
    if not success:
        db.update_repair_status(repair.id, RepairStatus.APPLY_FAILED.value, error_message=msg)
        raise HTTPException(status_code=400, detail=f"Apply failed: {msg}")

    db.update_repair_status(repair.id, RepairStatus.APPLIED.value)
    audit_logger.log("repair_applied", "repair", repair.id, {"target_file": repair.target_file})

    return {"status": "applied", "message": msg, "repair_id": repair.id}


@app.post("/api/repairs/{repair_id}/reject")
async def reject_repair_proposal(repair_id: str):
    rep_data = db.get_repair(repair_id)
    if not rep_data:
        raise HTTPException(status_code=404, detail="Repair proposal not found")

    db.update_repair_status(repair_id, RepairStatus.REJECTED.value)
    audit_logger.log("repair_rejected", "repair", repair_id, {})
    return {"status": "rejected", "repair_id": repair_id}


@app.post("/api/repairs/{repair_id}/rollback")
async def rollback_repair_proposal(repair_id: str):
    rep_data = db.get_repair(repair_id)
    if not rep_data:
        raise HTTPException(status_code=404, detail="Repair proposal not found")

    repair = RepairProposal(**rep_data)
    success, msg = applier.rollback_repair(repair)
    if not success:
        raise HTTPException(status_code=400, detail=f"Rollback failed: {msg}")

    db.update_repair_status(repair_id, RepairStatus.ROLLED_BACK.value)
    audit_logger.log("repair_rolled_back", "repair", repair_id, {"target_file": repair.target_file})
    return {"status": "rolled_back", "message": msg, "repair_id": repair_id}


@app.get("/api/audit-events")
async def list_audit_events():
    return {"audit_events": db.list_audit_events()}


# Demo control endpoints for seamless testing and VS Code interaction
@app.post("/api/demo/set-scenario")
async def set_demo_scenario(request: Request):
    """Convenience endpoint to configure simulator modes:
    - 'users_v2' (rename)
    - 'search_v2' (pagination)
    - 'payments_v2' (semantic uncertainty)
    - 'all_v1' (baseline / healthy)
    """
    data = await request.json()
    scenario = data.get("scenario", "all_v1")

    async with httpx.AsyncClient(timeout=3.0) as client:
        if scenario == "all_v1":
            for port in [8001, 8002, 8003, 8004]:
                try:
                    await client.post(f"http://127.0.0.1:{port}/reset")
                except Exception:
                    pass
        elif scenario == "users_v2":
            await client.post("http://127.0.0.1:8001/mode", json={"version": "v2"})
        elif scenario == "search_v2":
            await client.post("http://127.0.0.1:8003/mode", json={"version": "v2"})
        elif scenario == "payments_v2":
            await client.post("http://127.0.0.1:8002/mode", json={"version": "v2"})

    return {"status": "ok", "scenario": scenario}


@app.post("/api/demo/reset")
async def reset_demo():
    """Resets all simulator versions to v1 and restores clean demo app code."""
    async with httpx.AsyncClient(timeout=3.0) as client:
        for port in [8001, 8002, 8003, 8004]:
            try:
                await client.post(f"http://127.0.0.1:{port}/reset")
            except Exception:
                pass

    # Ensure demo source files are in original state
    clean_user_service = '''import httpx


def get_user_profile(user_id: str, base_url: str = "http://127.0.0.1:8001") -> dict:
    """Fetch user profile from Users API dependency.
    Expects 'name' and 'email' fields in response.
    """
    response = httpx.get(f"{base_url}/users/{user_id}", timeout=5.0)
    response.raise_for_status()
    data = response.json()
    return {
        "id": data["id"],
        "name": data["name"],
        "email": data["email"],
    }
'''
    with open(os.path.join(WORKSPACE_ROOT, "demo-app/src/services/user_service.py"), "w", encoding="utf-8") as f:
        f.write(clean_user_service)

    return {"status": "reset_completed", "message": "Simulators and code restored to clean baseline."}
