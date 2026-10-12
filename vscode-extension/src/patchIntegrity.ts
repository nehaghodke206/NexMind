import * as crypto from "crypto";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { RepairProposal } from "./api/guardianClient";

export interface CanonicalFileChange {
  relativePath: string;
  proposedContent: string;
  originalContent?: string;
}

export interface ReviewedPatchRecord {
  proposalId: string;
  patchHash: string;
  reviewedAt: string;
  isDiffReviewed: boolean;
  fileChanges: CanonicalFileChange[];
  originalFileHashes: Record<string, string | null>;
  approvedPatchHash?: string;
  approvedAt?: string;
  appliedAt?: string;
}

export interface VerificationResult {
  ok: boolean;
  reason?: string;
  changes?: CanonicalFileChange[];
  approvedHash?: string;
}

export interface PathValidationResult {
  ok: boolean;
  fullPath?: string;
  canonicalPath?: string;
  reason?: string;
}

/**
 * Normalizes a relative or workspace-based file path to canonical relative posix path.
 */
export function normalizeRelativePath(workspaceRoot: string, rawPath: string): string {
  if (!rawPath) return "";
  let p = rawPath.trim();
  if (path.isAbsolute(p)) {
    p = path.relative(workspaceRoot, p);
  }
  // Convert backslashes to forward slashes and strip leading ./ or /
  p = p.replace(/\\/g, "/").replace(/^\.?\/+/, "");
  return path.normalize(p).replace(/\\/g, "/");
}

/**
 * Hardens workspace path validation against directory traversal and symlink-based escapes,
 * including new-file targets and existing parent directories.
 */
export function validateWorkspacePath(
  workspaceRoot: string,
  relativeOrRawPath: string
): PathValidationResult {
  if (!workspaceRoot) {
    return { ok: false, reason: "Security violation: Workspace root is empty or undefined." };
  }
  if (!relativeOrRawPath || !relativeOrRawPath.trim()) {
    return { ok: false, reason: "Security violation: Target file path is empty." };
  }

  let realWorkspace: string;
  try {
    if (!fs.existsSync(workspaceRoot)) {
      return { ok: false, reason: `Workspace directory does not exist on disk: ${workspaceRoot}` };
    }
    realWorkspace = fs.realpathSync(workspaceRoot);
  } catch (err: any) {
    return { ok: false, reason: `Failed to resolve workspace root: ${err.message}` };
  }

  const raw = relativeOrRawPath.trim();
  const fullPath = path.isAbsolute(raw)
    ? path.normalize(raw)
    : path.resolve(realWorkspace, raw);

  // 1. Lexical traversal check
  const lexicalRelative = path.relative(realWorkspace, fullPath);
  if (
    lexicalRelative.startsWith("..") ||
    path.isAbsolute(lexicalRelative) ||
    lexicalRelative === ""
  ) {
    return {
      ok: false,
      reason: `Security violation: Path traversal detected. Target path '${relativeOrRawPath}' escapes the workspace boundary.`,
    };
  }

  // 2. Step-by-step segment inspection for symlink directory escapes
  const segments = lexicalRelative.split(/[\\/]/).filter(Boolean);
  let currentCheckPath = realWorkspace;

  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i];
    currentCheckPath = path.join(currentCheckPath, seg);

    let exists = false;
    let isSymlink = false;
    try {
      const lstat = fs.lstatSync(currentCheckPath);
      exists = true;
      isSymlink = lstat.isSymbolicLink();
    } catch (err: any) {
      if (err.code === "ENOENT") {
        exists = false;
      } else {
        return {
          ok: false,
          reason: `Failed to inspect path segment '${currentCheckPath}': ${err.message}`,
        };
      }
    }

    if (exists) {
      let realSegmentTarget: string;
      try {
        realSegmentTarget = fs.realpathSync(currentCheckPath);
      } catch (err: any) {
        return {
          ok: false,
          reason: `Security violation: Broken or invalid link detected at '${currentCheckPath}': ${err.message}`,
        };
      }

      const relSegment = path.relative(realWorkspace, realSegmentTarget);
      if (relSegment.startsWith("..") || path.isAbsolute(relSegment)) {
        return {
          ok: false,
          reason: `Security violation: Symlink escape detected. Path '${relativeOrRawPath}' segment '${seg}' resolves outside workspace to '${realSegmentTarget}'.`,
        };
      }
    } else {
      // Path segment doesn't exist yet (new file or directory).
      // Since all existing parent directories were checked and confirmed within realWorkspace,
      // creating files under this directory will remain inside the workspace.
      break;
    }
  }

  // 3. Final canonical check on fullPath itself if it exists
  try {
    const lstat = fs.lstatSync(fullPath);
    const realFinal = fs.realpathSync(fullPath);
    const relFinal = path.relative(realWorkspace, realFinal);
    if (relFinal.startsWith("..") || path.isAbsolute(relFinal) || relFinal === "") {
      return {
        ok: false,
        reason: `Security violation: Symlink escape detected. Target '${relativeOrRawPath}' resolves outside workspace to '${realFinal}'.`,
      };
    }
    return { ok: true, fullPath, canonicalPath: realFinal };
  } catch (err: any) {
    if (err.code === "ENOENT") {
      return { ok: true, fullPath, canonicalPath: fullPath };
    }
    return { ok: false, reason: `Failed to verify target path '${fullPath}': ${err.message}` };
  }
}

/**
 * Computes SHA-256 hash of a file on disk, or null if file does not exist.
 */
export function computeFileHash(filePath: string): string | null {
  try {
    if (!fs.existsSync(filePath)) {
      return null;
    }
    const stat = fs.statSync(filePath);
    if (!stat.isFile()) {
      return null;
    }
    const buffer = fs.readFileSync(filePath);
    return crypto.createHash("sha256").update(buffer).digest("hex");
  } catch {
    return null;
  }
}

/**
 * Deterministically computes a cryptographic SHA-256 hash over a canonical representation
 * of an entire change set, ensuring stable ordering, normalized paths, and exact byte counts.
 */
export function computeCanonicalPatchHash(changes: CanonicalFileChange[]): string {
  if (!changes || changes.length === 0) {
    return crypto.createHash("sha256").update("EMPTY_CHANGE_SET").digest("hex");
  }

  // Stable sort by normalized relative path
  const sorted = [...changes].sort((a, b) => {
    if (a.relativePath < b.relativePath) return -1;
    if (a.relativePath > b.relativePath) return 1;
    return 0;
  });

  const hasher = crypto.createHash("sha256");
  for (const file of sorted) {
    const normPath = file.relativePath.replace(/\\/g, "/").replace(/^\.?\/+/, "");
    hasher.update(`FILE:${normPath}\n`);
    const contentBuffer = Buffer.from(file.proposedContent || "", "utf-8");
    hasher.update(`LENGTH:${contentBuffer.length}\n`);
    hasher.update(contentBuffer);
    hasher.update("\n---END_FILE---\n");
  }

  return hasher.digest("hex");
}

/**
 * Extracts complete list of canonical file changes from a RepairProposal.
 */
export function extractChangeSet(
  proposal: RepairProposal,
  workspaceRoot: string
): CanonicalFileChange[] {
  const result: CanonicalFileChange[] = [];
  const evidence = proposal.evidence || {};
  const fileChanges = evidence.file_changes;

  if (Array.isArray(fileChanges) && fileChanges.length > 0) {
    for (const fc of fileChanges) {
      const rawPath = fc.file_path || fc.path || "";
      if (!rawPath) continue;
      const relPath = normalizeRelativePath(workspaceRoot, rawPath);
      result.push({
        relativePath: relPath,
        proposedContent: fc.proposed_content !== undefined ? fc.proposed_content : "",
        originalContent: fc.original_content,
      });
    }
  }

  // Fallback to target_file and proposed_code_snippet if file_changes list was not provided
  if (result.length === 0 && (proposal.target_file || evidence.target_file)) {
    const targetFile = proposal.target_file || evidence.target_file || "";
    const relPath = normalizeRelativePath(workspaceRoot, targetFile);
    if (relPath) {
      result.push({
        relativePath: relPath,
        proposedContent:
          proposal.proposed_code_snippet !== undefined
            ? proposal.proposed_code_snippet
            : evidence.proposed_content || "",
        originalContent: proposal.original_code_snippet,
      });
    }
  }

  return result;
}

/**
 * Store that securely binds human review and approval to the exact reviewed patch hash.
 */
export class PatchIntegrityStore {
  private records: Map<string, ReviewedPatchRecord> = new Map();
  private aliases: Map<string, string> = new Map();
  private appliedBackups: Map<string, { fullPath: string; relativePath: string; existed: boolean; content: Buffer | string | null }[]> = new Map();

  /**
   * Resolves any client alias ID (e.g. rep_...) to its canonical backend proposal UUID.
   */
  public resolveId(id: string): string {
    return this.aliases.get(id) || id;
  }

  /**
   * Registers an alias linking to a canonical proposal ID.
   */
  public registerAlias(aliasId: string, canonicalId: string): void {
    if (aliasId && canonicalId && aliasId !== canonicalId) {
      this.aliases.set(aliasId, canonicalId);
    }
  }

  /**
   * Records a user's explicit diff review of a proposal and snapshots disk baselines.
   */
  public recordReview(
    proposal: RepairProposal,
    workspaceRoot: string
  ): ReviewedPatchRecord {
    const changes = extractChangeSet(proposal, workspaceRoot);
    if (!changes || changes.length === 0) {
      throw new Error(`Proposal '${proposal.id}' contains no target files or changes to review.`);
    }

    // Path validation for all files in change set (detects path traversal and symlink escapes)
    for (const file of changes) {
      const validation = validateWorkspacePath(workspaceRoot, file.relativePath);
      if (!validation.ok) {
        throw new Error(validation.reason);
      }
    }

    const patchHash = computeCanonicalPatchHash(changes);

    const originalFileHashes: Record<string, string | null> = {};
    for (const file of changes) {
      const fullPath = path.resolve(workspaceRoot, file.relativePath);
      originalFileHashes[file.relativePath] = computeFileHash(fullPath);
    }

    // Register alias if present in proposal metadata
    const clientRepairId =
      proposal.proposed_changes?.client_repair_id ||
      proposal.proposed_changes?.repair_id;
    if (clientRepairId && clientRepairId !== proposal.id) {
      this.aliases.set(clientRepairId, proposal.id);
    }

    const canonicalId = this.resolveId(proposal.id);
    const existing = this.records.get(canonicalId);
    const record: ReviewedPatchRecord = {
      proposalId: canonicalId,
      patchHash,
      reviewedAt: new Date().toISOString(),
      isDiffReviewed: true,
      fileChanges: changes,
      originalFileHashes,
      approvedPatchHash:
        existing && existing.patchHash === patchHash
          ? existing.approvedPatchHash
          : undefined,
      approvedAt:
        existing && existing.patchHash === patchHash
          ? existing.approvedAt
          : undefined,
    };

    this.records.set(canonicalId, record);
    return record;
  }

  /**
   * Binds approval to the exact reviewed patch hash.
   * Requires an explicit successful diff review prior to granting approval.
   */
  public recordApproval(proposalId: string): string {
    const canonicalId = this.resolveId(proposalId);
    const record = this.records.get(canonicalId);
    if (!record || !record.isDiffReviewed) {
      throw new Error(
        `Proposal '${proposalId}' has not been reviewed yet. You must review the diff before granting approval.`
      );
    }

    record.approvedPatchHash = record.patchHash;
    record.approvedAt = new Date().toISOString();
    this.records.set(canonicalId, record);
    return record.approvedPatchHash;
  }

  /**
   * Revokes local approval for a proposal (e.g. when backend approval fails).
   */
  public revokeApproval(proposalId: string): void {
    const canonicalId = this.resolveId(proposalId);
    const record = this.records.get(canonicalId);
    if (record) {
      record.approvedPatchHash = undefined;
      record.approvedAt = undefined;
    }
  }

  /**
   * Retrieves the reviewed patch record if one exists.
   */
  public getRecord(proposalId: string): ReviewedPatchRecord | undefined {
    const canonicalId = this.resolveId(proposalId);
    return this.records.get(canonicalId);
  }

  /**
   * Verifies all security and integrity invariants before applying a patch.
   */
  public verifyBeforeApplication(
    proposal: RepairProposal,
    workspaceRoot: string
  ): VerificationResult {
    const canonicalId = this.resolveId(proposal.id);
    const record = this.records.get(canonicalId);
    if (!record || !record.isDiffReviewed) {
      return {
        ok: false,
        reason: `Repair proposal '${proposal.id}' has not been reviewed in this session. Review the diff first.`,
      };
    }

    if (!record.approvedPatchHash) {
      return {
        ok: false,
        reason: `Repair proposal '${proposal.id}' has not received human approval for the reviewed patch.`,
      };
    }

    // Invariant: Verify current proposal changes match the approved patch hash exactly
    const currentChanges = extractChangeSet(proposal, workspaceRoot);
    const currentHash = computeCanonicalPatchHash(currentChanges);

    if (currentHash !== record.approvedPatchHash) {
      return {
        ok: false,
        reason: `Integrity failure: The current proposed changes (${currentHash.slice(0, 8)}) differ from the patch you reviewed and approved (${record.approvedPatchHash.slice(0, 8)}). Please re-review the diff.`,
      };
    }

    if (record.fileChanges.length === 0) {
      return {
        ok: false,
        reason: `Proposal contains no target files or proposed content to apply.`,
      };
    }

    // Invariant: Path traversal & symlink escape prevention
    for (const file of record.fileChanges) {
      const pathCheck = validateWorkspacePath(workspaceRoot, file.relativePath);
      if (!pathCheck.ok) {
        return {
          ok: false,
          reason: pathCheck.reason,
        };
      }
    }

    // Invariant: Detect original file modifications since review
    for (const file of record.fileChanges) {
      const fullPath = path.resolve(workspaceRoot, file.relativePath);
      const currentDiskHash = computeFileHash(fullPath);
      const expectedDiskHash = record.originalFileHashes[file.relativePath];

      if (currentDiskHash !== expectedDiskHash) {
        return {
          ok: false,
          reason: `Conflict detected: Original workspace file '${file.relativePath}' was modified on disk after the repair was reviewed. Application aborted to protect your changes. Please review the updated diff again.`,
        };
      }
    }

    return {
      ok: true,
      changes: record.fileChanges,
      approvedHash: record.approvedPatchHash,
    };
  }

  /**
   * Applies the approved change set with immediate pre-write revalidation and robust rollback protection.
   * If any file write fails, all changes are restored to their previous state.
   * If any restoration fails, failure is reported with affected paths and recoverable backups preserved.
   */
  public applyApprovedChangesSafely(
    changes: CanonicalFileChange[],
    workspaceRoot: string,
    proposalId?: string
  ): string[] {
    // Immediate pre-write revalidation phase to minimize TOCTOU window
    if (proposalId) {
      const canonicalId = this.resolveId(proposalId);
      const record = this.records.get(canonicalId);
      if (!record || !record.isDiffReviewed) {
        throw new Error(
          `Pre-write check failed: Repair proposal '${proposalId}' has not been reviewed.`
        );
      }
      if (!record.approvedPatchHash) {
        throw new Error(
          `Pre-write check failed: Repair proposal '${proposalId}' has not been approved.`
        );
      }

      const currentHash = computeCanonicalPatchHash(changes);
      if (currentHash !== record.approvedPatchHash) {
        throw new Error(
          `Pre-write integrity failure: Current proposed changes (${currentHash.slice(0, 8)}) do not match the approved patch hash (${record.approvedPatchHash.slice(0, 8)}). Application aborted.`
        );
      }

      for (const file of changes) {
        const pathCheck = validateWorkspacePath(workspaceRoot, file.relativePath);
        if (!pathCheck.ok) {
          throw new Error(`Pre-write security check failed: ${pathCheck.reason}`);
        }
        const fullPath = pathCheck.fullPath!;
        const currentDiskHash = computeFileHash(fullPath);
        const expectedDiskHash = record.originalFileHashes[file.relativePath];

        if (currentDiskHash !== expectedDiskHash) {
          throw new Error(
            `Pre-write conflict detected: Original workspace file '${file.relativePath}' was modified on disk after review. Current hash does not match review baseline. Application aborted.`
          );
        }
      }
    } else {
      for (const file of changes) {
        const pathCheck = validateWorkspacePath(workspaceRoot, file.relativePath);
        if (!pathCheck.ok) {
          throw new Error(`Pre-write security check failed: ${pathCheck.reason}`);
        }
      }
    }

    interface BackupEntry {
      fullPath: string;
      relativePath: string;
      existed: boolean;
      content: Buffer | null;
    }

    const backups: BackupEntry[] = [];
    const writtenFiles: string[] = [];

    // Phase 1: Snapshot backups of all target files before modifying anything
    for (const file of changes) {
      const fullPath = path.resolve(workspaceRoot, file.relativePath);
      let existed = false;
      let content: Buffer | null = null;
      try {
        if (fs.existsSync(fullPath)) {
          const stat = fs.statSync(fullPath);
          if (stat.isFile()) {
            existed = true;
            content = fs.readFileSync(fullPath);
          }
        }
      } catch {
        // If unreadable or directory, leave existed=false
      }
      backups.push({ fullPath, relativePath: file.relativePath, existed, content });
    }

    if (proposalId) {
      const canonicalId = this.resolveId(proposalId);
      this.appliedBackups.set(canonicalId, [...backups]);
      if (canonicalId !== proposalId) {
        this.appliedBackups.set(proposalId, [...backups]);
      }
    }

    // Phase 2: Perform atomic application with persistent disk backups
    try {
      for (const backup of backups) {
        if (backup.existed && backup.content !== null) {
          try {
            fs.writeFileSync(`${backup.fullPath}.guardian.bak`, backup.content, "utf-8");
          } catch {}
        }
      }

      for (const file of changes) {
        const fullPath = path.resolve(workspaceRoot, file.relativePath);
        fs.mkdirSync(path.dirname(fullPath), { recursive: true });
        fs.writeFileSync(fullPath, file.proposedContent, "utf-8");
        writtenFiles.push(fullPath);
      }
    } catch (writeErr: any) {
      // Phase 3: Rollback on any failure with restoration failure tracking and backup preservation
      interface FailedRollback {
        path: string;
        error: string;
        preservedBackupPath?: string;
      }
      const failedRollbacks: FailedRollback[] = [];
      const restoredPaths: string[] = [];

      for (const backup of backups) {
        try {
          if (backup.existed && backup.content !== null) {
            fs.writeFileSync(backup.fullPath, backup.content);
            restoredPaths.push(backup.relativePath);
          } else if (!backup.existed && writtenFiles.includes(backup.fullPath) && fs.existsSync(backup.fullPath)) {
            fs.unlinkSync(backup.fullPath);
            restoredPaths.push(backup.relativePath);
          }
        } catch (rollbackErr: any) {
          let preservedPath: string | undefined;
          if (backup.content !== null) {
            try {
              const recoveryFile = `${backup.fullPath}.guardian-backup-${Date.now()}`;
              fs.writeFileSync(recoveryFile, backup.content);
              preservedPath = recoveryFile;
            } catch {
              try {
                const tmpRecovery = path.join(
                  os.tmpdir(),
                  `guardian-recovery-${path.basename(backup.fullPath)}-${Date.now()}`
                );
                fs.writeFileSync(tmpRecovery, backup.content);
                preservedPath = tmpRecovery;
              } catch {
                // Disk write failed
              }
            }
          }
          failedRollbacks.push({
            path: backup.relativePath,
            error: rollbackErr.message,
            preservedBackupPath: preservedPath,
          });
        }
      }

      if (failedRollbacks.length > 0) {
        const failureDetails = failedRollbacks
          .map(
            (f) =>
              `'${f.path}' (error: ${f.error}${
                f.preservedBackupPath ? `, backup preserved at: ${f.preservedBackupPath}` : ", NO backup preserved"
              })`
          )
          .join("; ");
        throw new Error(
          `Failed to apply patch file (${writeErr.message}), and ROLLBACK FAILED for ${failedRollbacks.length} file(s): [${failureDetails}]. Manual intervention is required.`
        );
      }

      throw new Error(
        `Failed to apply patch file (${writeErr.message}). All files successfully rolled back to original state.`
      );
    }

    return writtenFiles;
  }

  /**
   * Marks a proposal as applied in the store.
   */
  public recordApplied(proposalId: string): void {
    const canonicalId = this.resolveId(proposalId);
    const record = this.records.get(canonicalId);
    if (record) {
      record.appliedAt = new Date().toISOString();
    }
  }

  /**
   * Rolls back an applied repair proposal by restoring original file contents from backup.
   */
  public rollbackAppliedChanges(
    workspaceRoot: string,
    proposalId?: string
  ): string[] {
    const canonicalId = proposalId ? this.resolveId(proposalId) : undefined;
    const key = canonicalId || "latest";
    let backups = this.appliedBackups.get(key);
    if (!backups && proposalId) {
      backups = this.appliedBackups.get(proposalId);
    }
    const restoredPaths: string[] = [];

    if (backups && backups.length > 0) {
      for (const backup of backups) {
        try {
          if (backup.existed && backup.content !== null) {
            fs.writeFileSync(backup.fullPath, backup.content, "utf-8");
            restoredPaths.push(backup.relativePath);
          } else if (!backup.existed && fs.existsSync(backup.fullPath)) {
            fs.unlinkSync(backup.fullPath);
            restoredPaths.push(backup.relativePath);
          }
          const bakFile = `${backup.fullPath}.guardian.bak`;
          if (fs.existsSync(bakFile)) {
            try { fs.unlinkSync(bakFile); } catch {}
          }
        } catch (err: any) {
          throw new Error(`Failed to restore file '${backup.relativePath}': ${err.message}`);
        }
      }
      this.appliedBackups.delete(key);
      if (proposalId && proposalId !== key) {
        this.appliedBackups.delete(proposalId);
      }
    } else if (canonicalId) {
      // Disk fallback using persistent .guardian.bak files
      const record = this.records.get(canonicalId);
      if (record) {
        for (const file of record.fileChanges) {
          const fullPath = path.resolve(workspaceRoot, file.relativePath);
          const bakFile = `${fullPath}.guardian.bak`;
          if (fs.existsSync(bakFile)) {
            const content = fs.readFileSync(bakFile, "utf-8");
            fs.writeFileSync(fullPath, content, "utf-8");
            try { fs.unlinkSync(bakFile); } catch {}
            restoredPaths.push(file.relativePath);
          } else if (file.originalContent !== undefined && file.originalContent !== null) {
            fs.writeFileSync(fullPath, file.originalContent, "utf-8");
            restoredPaths.push(file.relativePath);
          }
        }
      }
    }

    if (canonicalId) {
      const record = this.records.get(canonicalId);
      if (record) {
        record.appliedAt = undefined;
      }
    }

    return restoredPaths;
  }

  /**
   * Checks whether the proposal's target files have changed on disk since the diff review.
   */
  public checkProposalStaleness(
    proposal: RepairProposal,
    workspaceRoot: string
  ): { isStale: boolean; reason?: string } {
    const canonicalId = this.resolveId(proposal.id);
    const record = this.records.get(canonicalId);
    if (!record) {
      return { isStale: false };
    }
    for (const file of record.fileChanges) {
      const fullPath = path.resolve(workspaceRoot, file.relativePath);
      const currentDiskHash = computeFileHash(fullPath);
      const expectedDiskHash = record.originalFileHashes[file.relativePath];
      if (currentDiskHash !== expectedDiskHash) {
        return {
          isStale: true,
          reason: `Original workspace file '${file.relativePath}' was modified on disk after diff review. Proposal is stale.`,
        };
      }
    }
    return { isStale: false };
  }

  /**
   * Clears all records (useful for test resets).
   */
  public clear(): void {
    this.records.clear();
    this.aliases.clear();
    this.appliedBackups.clear();
  }
}

export const patchIntegrityStore = new PatchIntegrityStore();

