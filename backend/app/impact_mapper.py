"""Impact analysis mapper linking detected changes to explicitly configured workflows, source files, and tests."""

import uuid
from typing import List, Dict, Any
from .models import ChangeItem, ImpactItem
from .config import GuardianConfig


def map_change_impact(change: ChangeItem, config: GuardianConfig) -> List[ImpactItem]:
    """Maps a change item to configured workflows, source files, and tests."""
    impacts: List[ImpactItem] = []

    # Identify fields involved in the change
    target_fields = set()
    ev = change.evidence
    if "removed_field" in ev:
        target_fields.add(ev["removed_field"])
    if "field" in ev:
        target_fields.add(ev["field"])
    if change.change_type == "pagination_contract_change":
        target_fields.update(["items", "page", "next_page", "results", "next_cursor"])

    for wf in config.workflows:
        if change.dependency_id in wf.dependencies:
            # Check field match or general dependency match
            matching_fields = [f for f in wf.fields if f in target_fields]
            
            if matching_fields or not target_fields:
                reason = (
                    f"Configured workflow '{wf.name}' depends on '{change.dependency_id}' "
                    f"and relies on changed field(s): {matching_fields if matching_fields else 'general contract'}."
                )
                impacts.append(
                    ImpactItem(
                        workflow_id=wf.id,
                        workflow_name=wf.name,
                        source_files=wf.source_files,
                        tests=wf.tests,
                        affected_fields=matching_fields if matching_fields else wf.fields,
                        reason=reason,
                    )
                )

    return impacts
