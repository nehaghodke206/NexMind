"""Repair applier and rollback engine with file integrity checks."""

import os
import shutil
import hashlib
from typing import Dict, Any, Tuple
from .models import RepairProposal, RepairStatus


class RepairApplier:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.backup_dir = os.path.join(workspace_root, ".guardian_backups")
        os.makedirs(self.backup_dir, exist_ok=True)

    def _get_backup_path(self, repair_id: str, filename: str) -> str:
        safe_name = os.path.basename(filename)
        return os.path.join(self.backup_dir, f"{repair_id}_{safe_name}.bak")

    def apply_repair(self, repair: RepairProposal) -> Tuple[bool, str]:
        """Applies an approved and validated repair proposal to target source code."""
        if repair.status == RepairStatus.BLOCKED_UNCERTAIN:
            return False, "Cannot apply repair: proposal is blocked due to semantic uncertainty."

        if not repair.target_file:
            return False, "No target file specified in repair proposal."

        target_abs = os.path.join(self.workspace_root, repair.target_file)
        if not os.path.exists(target_abs):
            return False, f"Target file does not exist: {repair.target_file}"

        with open(target_abs, "r", encoding="utf-8") as f:
            current_content = f.read()

        # Check that original snippet is present
        if repair.original_code_snippet not in current_content:
            return False, "Target file has changed since repair preview was generated. Aborting apply."

        # Backup original file before modifying
        backup_path = self._get_backup_path(repair.id, repair.target_file)
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(current_content)

        # Apply modification
        patched_content = current_content.replace(
            repair.original_code_snippet,
            repair.proposed_code_snippet,
        )

        with open(target_abs, "w", encoding="utf-8") as f:
            f.write(patched_content)

        return True, f"Successfully applied repair to {repair.target_file}."

    def rollback_repair(self, repair: RepairProposal) -> Tuple[bool, str]:
        """Restores original file content from backup for a previously applied repair."""
        if not repair.target_file:
            return False, "No target file specified in repair proposal."

        backup_path = self._get_backup_path(repair.id, repair.target_file)
        if not os.path.exists(backup_path):
            return False, f"No backup found for repair {repair.id} at {backup_path}"

        target_abs = os.path.join(self.workspace_root, repair.target_file)
        with open(backup_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        with open(target_abs, "w", encoding="utf-8") as f:
            f.write(original_content)

        return True, f"Successfully rolled back changes in {repair.target_file}."
