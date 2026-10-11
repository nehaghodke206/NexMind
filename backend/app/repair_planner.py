"""Repair planner proposing safe, previewable compatibility adapters or blocking uncertain changes."""

import os
import uuid
import difflib
from datetime import datetime, timezone
from typing import Optional, List
from .models import ChangeItem, RepairProposal, RepairStatus, ChangeSeverity
from .config import GuardianConfig


def create_unified_diff(original: str, modified: str, filename: str) -> str:
    """Generates standard unified diff representation."""
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )
    return "".join(diff)


def plan_repair(change: ChangeItem, config: GuardianConfig, workspace_root: str) -> RepairProposal:
    """Plans a repair proposal for a detected change or blocks it if uncertain."""
    repair_id = f"rep_{uuid.uuid4().hex[:8]}"
    created_at = datetime.now(timezone.utc).isoformat()

    # Case 1: Semantic Uncertainty -> BLOCK REPAIR
    if change.change_type == "semantic_uncertainty" or change.severity == ChangeSeverity.BLOCKED:
        return RepairProposal(
            id=repair_id,
            change_id=change.id,
            repair_type="blocked_semantic_uncertainty",
            target_file="demo-app/src/services/payment_service.py",
            original_code_snippet="",
            proposed_code_snippet="",
            diff="",
            evidence=change.evidence,
            assumptions=[
                "Semantic change detected in business-critical field.",
                "Automated mapping between distinct business states ('paid' vs 'processing_escrow') is unsafe.",
                "Developer domain knowledge is required before altering status verification logic.",
            ],
            confidence=0.0,
            status=RepairStatus.BLOCKED_UNCERTAIN,
            created_at=created_at,
            error_message=(
                "REPAIR BLOCKED: The observed change alters domain semantics (payment status). "
                "Dependency Guardian safety rules prohibit automatic repair synthesis for uncertain business semantics."
            ),
        )

    # Case 2: Field Rename Candidate (Users API: name -> display_name)
    if change.change_type == "field_rename_candidate":
        target_rel = "demo-app/src/services/user_service.py"
        target_abs = os.path.join(workspace_root, target_rel)
        
        if not os.path.exists(target_abs):
            raise FileNotFoundError(f"Target file for repair not found: {target_abs}")

        with open(target_abs, "r", encoding="utf-8") as f:
            original_content = f.read()

        orig_snippet = '''    return {
        "id": data["id"],
        "name": data["name"],
        "email": data["email"],
    }'''

        proposed_snippet = '''    # Adapted for field rename compatibility: 'name' -> 'display_name'
    resolved_name = data.get("name") if "name" in data else data.get("display_name", "")
    return {
        "id": data["id"],
        "name": resolved_name,
        "email": data["email"],
    }'''

        if orig_snippet in original_content:
            modified_content = original_content.replace(orig_snippet, proposed_snippet)
        else:
            # Fallback simple replacement if formatting slightly differs
            modified_content = original_content.replace(
                '"name": data["name"]',
                '"name": data.get("name", data.get("display_name", ""))'
            )

        diff = create_unified_diff(original_content, modified_content, target_rel)

        return RepairProposal(
            id=repair_id,
            change_id=change.id,
            repair_type="field_rename_adapter",
            target_file=target_rel,
            original_code_snippet=orig_snippet,
            proposed_code_snippet=proposed_snippet,
            diff=diff,
            evidence=change.evidence,
            assumptions=[
                "Field 'display_name' is the backward-compatible substitute for 'name'.",
                "Calling code expects 'name' attribute in the returned dictionary.",
                "Both v1 ('name') and v2 ('display_name') payloads remain compatible through fallback.",
            ],
            confidence=0.88,
            status=RepairStatus.PROPOSED,
            created_at=created_at,
        )

    # Case 3: Pagination Contract Change (Search API)
    if change.change_type == "pagination_contract_change":
        target_rel = "demo-app/src/services/search_service.py"
        target_abs = os.path.join(workspace_root, target_rel)

        if not os.path.exists(target_abs):
            raise FileNotFoundError(f"Target file for repair not found: {target_abs}")

        with open(target_abs, "r", encoding="utf-8") as f:
            original_content = f.read()

        orig_snippet = '''    return {
        "items": data["items"],
        "page": data["page"],
        "next_page": data["next_page"],
    }'''

        proposed_snippet = '''    # Adapted for pagination contract: supports legacy page items and cursor results
    items = data.get("items", data.get("results", []))
    page_num = data.get("page", 1)
    next_page = data.get("next_page") or (2 if "next_cursor" in data else None)
    return {
        "items": items,
        "page": page_num,
        "next_page": next_page,
    }'''

        if orig_snippet in original_content:
            modified_content = original_content.replace(orig_snippet, proposed_snippet)
        else:
            modified_content = original_content.replace(
                '"items": data["items"]',
                '"items": data.get("items", data.get("results", []))'
            )

        diff = create_unified_diff(original_content, modified_content, target_rel)

        return RepairProposal(
            id=repair_id,
            change_id=change.id,
            repair_type="pagination_adapter",
            target_file=target_rel,
            original_code_snippet=orig_snippet,
            proposed_code_snippet=proposed_snippet,
            diff=diff,
            evidence=change.evidence,
            assumptions=[
                "Caller requires 'items', 'page', and 'next_page' fields.",
                "Search API response with 'results' maps to 'items'.",
                "Presence of 'next_cursor' indicates a subsequent page is available.",
            ],
            confidence=0.82,
            status=RepairStatus.PROPOSED,
            created_at=created_at,
        )

    # Generic unhandled change
    return RepairProposal(
        id=repair_id,
        change_id=change.id,
        repair_type="manual_review_required",
        target_file="",
        original_code_snippet="",
        proposed_code_snippet="",
        diff="",
        evidence=change.evidence,
        assumptions=["Automated adapter generation is not supported for this change type."],
        confidence=0.0,
        status=RepairStatus.BLOCKED_UNCERTAIN,
        created_at=created_at,
        error_message="No automated adapter template available for this change type.",
    )
