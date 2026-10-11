"""Deterministic change detector comparing observations against known-good baselines."""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from .models import ChangeItem, ChangeSeverity, ProbeResult
from .config import ProbeConfig


def detect_changes(
    scan_id: str,
    probe_cfg: ProbeConfig,
    baseline: Dict[str, Any],
    current: ProbeResult,
) -> List[ChangeItem]:
    """Compares current probe result against baseline and returns detected changes."""
    changes: List[ChangeItem] = []
    created_at = datetime.now(timezone.utc).isoformat()

    # 1. Connection / Probe Error Check
    if current.error or current.status_code == 0:
        changes.append(
            ChangeItem(
                id=f"chg_{uuid.uuid4().hex[:8]}",
                scan_id=scan_id,
                dependency_id=current.dependency_id,
                probe_id=current.probe_id,
                change_type="endpoint_unreachable",
                severity=ChangeSeverity.HIGH,
                evidence={
                    "error": current.error,
                    "status_code": current.status_code,
                    "baseline_status": baseline.get("raw_response", {}).get("status_code", 200),
                },
                status="detected",
                created_at=created_at,
            )
        )
        return changes

    # 2. HTTP Status Code Difference
    baseline_raw = baseline.get("raw_response", {})
    baseline_status = baseline_raw.get("status_code", 200) if isinstance(baseline_raw, dict) and "status_code" in baseline_raw else 200
    if current.status_code != baseline_status:
        changes.append(
            ChangeItem(
                id=f"chg_{uuid.uuid4().hex[:8]}",
                scan_id=scan_id,
                dependency_id=current.dependency_id,
                probe_id=current.probe_id,
                change_type="status_code_changed",
                severity=ChangeSeverity.HIGH,
                evidence={
                    "baseline_status": baseline_status,
                    "current_status": current.status_code,
                },
                status="detected",
                created_at=created_at,
            )
        )

    # Extract payloads
    base_body = baseline_raw.get("body") if (isinstance(baseline_raw, dict) and "body" in baseline_raw) else baseline_raw
    curr_body = current.body

    if not isinstance(base_body, dict) or not isinstance(curr_body, dict):
        # Fallback comparison if not dict
        if base_body != curr_body:
            changes.append(
                ChangeItem(
                    id=f"chg_{uuid.uuid4().hex[:8]}",
                    scan_id=scan_id,
                    dependency_id=current.dependency_id,
                    probe_id=current.probe_id,
                    change_type="payload_content_mismatch",
                    severity=ChangeSeverity.MEDIUM,
                    evidence={"baseline": base_body, "current": curr_body},
                    status="detected",
                    created_at=created_at,
                )
            )
        return changes

    base_keys = set(base_body.keys())
    curr_keys = set(curr_body.keys())

    removed_keys = base_keys - curr_keys
    added_keys = curr_keys - base_keys
    common_keys = base_keys & curr_keys

    # 3. Pagination Contract Change Check
    is_base_pagination = ("page" in base_keys or "next_page" in base_keys) and "items" in base_keys
    is_curr_cursor = "next_cursor" in curr_keys or "cursor" in curr_keys
    if is_base_pagination and is_curr_cursor:
        changes.append(
            ChangeItem(
                id=f"chg_{uuid.uuid4().hex[:8]}",
                scan_id=scan_id,
                dependency_id=current.dependency_id,
                probe_id=current.probe_id,
                change_type="pagination_contract_change",
                severity=ChangeSeverity.HIGH,
                evidence={
                    "description": "API switched from page-based pagination to cursor-based pagination.",
                    "baseline_pagination_keys": [k for k in ["items", "page", "next_page"] if k in base_keys],
                    "current_pagination_keys": [k for k in ["results", "next_cursor"] if k in curr_keys],
                    "baseline_sample": base_body,
                    "current_sample": curr_body,
                },
                status="detected",
                created_at=created_at,
            )
        )
        return changes

    # 4. Known-Value Expectations and Semantic Uncertainty
    if probe_cfg.known_values:
        for k_field, k_expected in probe_cfg.known_values.items():
            if k_field in curr_body and curr_body[k_field] != k_expected:
                # Semantic change detected!
                changes.append(
                    ChangeItem(
                        id=f"chg_{uuid.uuid4().hex[:8]}",
                        scan_id=scan_id,
                        dependency_id=current.dependency_id,
                        probe_id=current.probe_id,
                        change_type="semantic_uncertainty",
                        severity=ChangeSeverity.BLOCKED,
                        evidence={
                            "field": k_field,
                            "expected_value": k_expected,
                            "observed_value": curr_body[k_field],
                            "baseline_value": base_body.get(k_field),
                            "reason": (
                                f"Field '{k_field}' changed value from '{base_body.get(k_field)}' to "
                                f"'{curr_body[k_field]}'. Semantic equivalence cannot be established automatically. "
                                f"Automatic repair is blocked to prevent corrupting application business logic."
                            ),
                        },
                        status="blocked_uncertain",
                        created_at=created_at,
                    )
                )
                return changes

    # 5. Candidate Rename Detection
    # Look for removed single field and added single field with matching value and type
    if len(removed_keys) == 1 and len(added_keys) == 1:
        rem_field = list(removed_keys)[0]
        add_field = list(added_keys)[0]
        rem_val = base_body[rem_field]
        add_val = curr_body[add_field]

        if type(rem_val) == type(add_val) and rem_val == add_val:
            changes.append(
                ChangeItem(
                    id=f"chg_{uuid.uuid4().hex[:8]}",
                    scan_id=scan_id,
                    dependency_id=current.dependency_id,
                    probe_id=current.probe_id,
                    change_type="field_rename_candidate",
                    severity=ChangeSeverity.HIGH,
                    evidence={
                        "removed_field": rem_field,
                        "added_field": add_field,
                        "observed_value": add_val,
                        "type": type(rem_val).__name__,
                        "baseline_sample": base_body,
                        "current_sample": curr_body,
                        "limitation_note": "Matching value in fixture is candidate evidence, not guaranteed universal semantic equivalence.",
                    },
                    status="detected",
                    created_at=created_at,
                )
            )
            return changes

    # 6. General Removed Keys (Breaking structural change)
    for rem in removed_keys:
        changes.append(
            ChangeItem(
                id=f"chg_{uuid.uuid4().hex[:8]}",
                scan_id=scan_id,
                dependency_id=current.dependency_id,
                probe_id=current.probe_id,
                change_type="field_removed",
                severity=ChangeSeverity.HIGH,
                evidence={
                    "removed_field": rem,
                    "previous_value": base_body[rem],
                    "previous_type": type(base_body[rem]).__name__,
                },
                status="detected",
                created_at=created_at,
            )
        )

    # 7. Type Mismatches in common keys
    for k in common_keys:
        v_base = base_body[k]
        v_curr = curr_body[k]
        if type(v_base) != type(v_curr) and v_base is not None and v_curr is not None:
            changes.append(
                ChangeItem(
                    id=f"chg_{uuid.uuid4().hex[:8]}",
                    scan_id=scan_id,
                    dependency_id=current.dependency_id,
                    probe_id=current.probe_id,
                    change_type="type_mismatch",
                    severity=ChangeSeverity.HIGH,
                    evidence={
                        "field": k,
                        "baseline_type": type(v_base).__name__,
                        "current_type": type(v_curr).__name__,
                        "baseline_value": v_base,
                        "current_value": v_curr,
                    },
                    status="detected",
                    created_at=created_at,
                )
            )

    # 8. Added Keys (Informational)
    for add in added_keys:
        changes.append(
            ChangeItem(
                id=f"chg_{uuid.uuid4().hex[:8]}",
                scan_id=scan_id,
                dependency_id=current.dependency_id,
                probe_id=current.probe_id,
                change_type="field_added",
                severity=ChangeSeverity.LOW,
                evidence={
                    "added_field": add,
                    "observed_value": curr_body[add],
                    "observed_type": type(curr_body[add]).__name__,
                },
                status="detected",
                created_at=created_at,
            )
        )

    return changes
