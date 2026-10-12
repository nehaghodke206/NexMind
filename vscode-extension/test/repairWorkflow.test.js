const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");

const {
  patchIntegrityStore,
  validateWorkspacePath,
  computeCanonicalPatchHash,
  computeFileHash,
  extractChangeSet,
} = require("../dist/patchIntegrity");

function createTempDir(prefix = "guardian-test-") {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

test.describe("Dependency Guardian Repair Workflow Hardening", () => {
  test.beforeEach(() => {
    patchIntegrityStore.clear();
  });

  // --------------------------------------------------------------------------
  // 1. Unreviewed Approval
  // --------------------------------------------------------------------------
  test.it("Test 1: Unreviewed approval must be rejected", () => {
    const tempDir = createTempDir("unreviewed-");
    try {
      const proposal = {
        id: "prop_unreviewed_001",
        change_id: "chg_01",
        repair_type: "compatibility_adapter",
        target_file: "service.py",
        original_code_snippet: "item['stock']",
        proposed_code_snippet: "item.get('stock', 0)",
        diff: "--- a/service.py\n+++ b/service.py\n@@ -1 +1 @@\n-item['stock']\n+item.get('stock', 0)",
        evidence: {},
        assumptions: [],
        confidence: 0.95,
        status: "validated",
        created_at: new Date().toISOString(),
      };

      // Attempting to approve without prior recordReview must throw
      assert.throws(
        () => {
          patchIntegrityStore.recordApproval(proposal.id);
        },
        (err) => {
          assert.match(err.message, /has not been reviewed yet/i);
          return true;
        }
      );

      // Verify that getRecord is undefined and verifyBeforeApplication fails
      const verification = patchIntegrityStore.verifyBeforeApplication(proposal, tempDir);
      assert.strictEqual(verification.ok, false);
      assert.match(verification.reason, /has not been reviewed/i);
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // 2. Tampered Patches
  // --------------------------------------------------------------------------
  test.it("Test 2: Tampered patch content after approval must be rejected", () => {
    const tempDir = createTempDir("tamper-");
    try {
      const targetFile = path.join(tempDir, "client.py");
      fs.writeFileSync(targetFile, "def run():\n    return item['stock']\n", "utf-8");

      const proposal = {
        id: "prop_tamper_002",
        change_id: "chg_02",
        repair_type: "compatibility_adapter",
        target_file: "client.py",
        original_code_snippet: "item['stock']",
        proposed_code_snippet: "def run():\n    return item.get('stock', 0)\n",
        diff: "diff",
        evidence: {
          file_changes: [
            {
              file_path: "client.py",
              proposed_content: "def run():\n    return item.get('stock', 0)\n",
              original_content: "def run():\n    return item['stock']\n",
            },
          ],
        },
        assumptions: [],
        confidence: 0.95,
        status: "validated",
        created_at: new Date().toISOString(),
      };

      // Review and approve valid patch
      patchIntegrityStore.recordReview(proposal, tempDir);
      const approvedHash = patchIntegrityStore.recordApproval(proposal.id);
      assert.ok(approvedHash);

      // Verification succeeds with unmodified proposal
      const validCheck = patchIntegrityStore.verifyBeforeApplication(proposal, tempDir);
      assert.strictEqual(validCheck.ok, true);

      // Tamper proposal's proposed content
      const tamperedProposal = JSON.parse(JSON.stringify(proposal));
      tamperedProposal.evidence.file_changes[0].proposed_content =
        "def run():\n    # Injected malicious modification\n    return evil()\n";

      // verifyBeforeApplication must reject tampered content
      const tamperedCheck = patchIntegrityStore.verifyBeforeApplication(tamperedProposal, tempDir);
      assert.strictEqual(tamperedCheck.ok, false);
      assert.match(tamperedCheck.reason, /Integrity failure/i);

      // applyApprovedChangesSafely must also reject tampered content immediately
      const tamperedChanges = extractChangeSet(tamperedProposal, tempDir);
      assert.throws(
        () => {
          patchIntegrityStore.applyApprovedChangesSafely(tamperedChanges, tempDir, proposal.id);
        },
        (err) => {
          assert.match(err.message, /integrity failure/i);
          return true;
        }
      );
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // 3. Source Files Changed After Review
  // --------------------------------------------------------------------------
  test.it("Test 3: Source file modified on disk after review must trigger conflict abort", () => {
    const tempDir = createTempDir("conflict-");
    try {
      const targetFile = path.join(tempDir, "service.py");
      fs.writeFileSync(targetFile, "original_content = 1\n", "utf-8");

      const proposal = {
        id: "prop_conflict_003",
        change_id: "chg_03",
        repair_type: "compatibility_adapter",
        target_file: "service.py",
        evidence: {
          file_changes: [
            {
              file_path: "service.py",
              proposed_content: "original_content = 2\n",
              original_content: "original_content = 1\n",
            },
          ],
        },
        status: "validated",
        created_at: new Date().toISOString(),
      };

      // Review and approve
      patchIntegrityStore.recordReview(proposal, tempDir);
      patchIntegrityStore.recordApproval(proposal.id);

      // Now developer modifies service.py on disk before applying
      fs.writeFileSync(targetFile, "original_content = 1\n# Local edit made by developer\n", "utf-8");

      // verifyBeforeApplication must flag conflict
      const check = patchIntegrityStore.verifyBeforeApplication(proposal, tempDir);
      assert.strictEqual(check.ok, false);
      assert.match(check.reason, /Conflict detected/i);

      // applyApprovedChangesSafely pre-write check must throw and NOT overwrite local edit
      const changes = extractChangeSet(proposal, tempDir);
      assert.throws(
        () => {
          patchIntegrityStore.applyApprovedChangesSafely(changes, tempDir, proposal.id);
        },
        (err) => {
          assert.match(err.message, /conflict detected/i);
          return true;
        }
      );

      // File on disk must remain untouched with developer's edits
      assert.strictEqual(
        fs.readFileSync(targetFile, "utf-8"),
        "original_content = 1\n# Local edit made by developer\n"
      );
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // 4. Path Traversal
  // --------------------------------------------------------------------------
  test.it("Test 4: Path traversal outside workspace boundary must be rejected", () => {
    const tempDir = createTempDir("traversal-");
    try {
      // 1. Direct lexical traversal with ../
      const res1 = validateWorkspacePath(tempDir, "../../etc/shadow");
      assert.strictEqual(res1.ok, false);
      assert.match(res1.reason, /Path traversal detected/i);

      // 2. Absolute path outside workspace
      const res2 = validateWorkspacePath(tempDir, "/etc/passwd");
      assert.strictEqual(res2.ok, false);
      assert.match(res2.reason, /Path traversal detected/i);

      // 3. Traversal inside proposal change set
      const proposal = {
        id: "prop_traversal_004",
        change_id: "chg_04",
        repair_type: "compatibility_adapter",
        evidence: {
          file_changes: [
            {
              file_path: "../../evil.py",
              proposed_content: "malicious = True\n",
            },
          ],
        },
        status: "validated",
        created_at: new Date().toISOString(),
      };

      assert.throws(
        () => {
          patchIntegrityStore.recordReview(proposal, tempDir);
        },
        (err) => {
          assert.match(err.message, /Path traversal detected/i);
          return true;
        }
      );
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // 5. Symlink Escapes (Existing File, Parent Directory, and Internal Links)
  // --------------------------------------------------------------------------
  test.it("Test 5A: Existing file that is a symlink pointing outside workspace must be rejected", () => {
    const tempDir = createTempDir("symlink-file-");
    const outsideDir = createTempDir("symlink-outside-");
    try {
      const outsideSecret = path.join(outsideDir, "secret.py");
      fs.writeFileSync(outsideSecret, "API_KEY = 'secret'\n", "utf-8");

      // Create symlink inside workspace pointing to outside file
      const linkInsideWorkspace = path.join(tempDir, "link_file.py");
      fs.symlinkSync(outsideSecret, linkInsideWorkspace);

      const res = validateWorkspacePath(tempDir, "link_file.py");
      assert.strictEqual(res.ok, false);
      assert.match(res.reason, /Symlink escape detected/i);

      const proposal = {
        id: "prop_symlink_file",
        change_id: "chg_05a",
        evidence: {
          file_changes: [
            {
              file_path: "link_file.py",
              proposed_content: "API_KEY = 'hacked'\n",
            },
          ],
        },
        status: "validated",
        created_at: new Date().toISOString(),
      };

      assert.throws(
        () => {
          patchIntegrityStore.recordReview(proposal, tempDir);
        },
        (err) => {
          assert.match(err.message, /Symlink escape detected/i);
          return true;
        }
      );
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
      fs.rmSync(outsideDir, { recursive: true, force: true });
    }
  });

  test.it("Test 5B: New-file target whose parent directory is an existing symlink pointing outside workspace must be rejected", () => {
    const tempDir = createTempDir("symlink-dir-");
    const outsideDir = createTempDir("symlink-dir-outside-");
    try {
      // Create symlink directory inside workspace pointing outside
      const symlinkDir = path.join(tempDir, "external_dir");
      fs.symlinkSync(outsideDir, symlinkDir, "dir");

      // Target path: external_dir/new_file.py (new_file.py does NOT exist yet)
      const res = validateWorkspacePath(tempDir, "external_dir/new_file.py");
      assert.strictEqual(res.ok, false);
      assert.match(res.reason, /Symlink escape detected/i);

      const proposal = {
        id: "prop_symlink_new_file",
        change_id: "chg_05b",
        evidence: {
          file_changes: [
            {
              file_path: "external_dir/new_file.py",
              proposed_content: "evil = 1\n",
            },
          ],
        },
        status: "validated",
        created_at: new Date().toISOString(),
      };

      assert.throws(
        () => {
          patchIntegrityStore.recordReview(proposal, tempDir);
        },
        (err) => {
          assert.match(err.message, /Symlink escape detected/i);
          return true;
        }
      );
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
      fs.rmSync(outsideDir, { recursive: true, force: true });
    }
  });

  test.it("Test 5C: Legitimate internal symlink inside workspace remains accepted", () => {
    const tempDir = createTempDir("symlink-internal-");
    try {
      const realSubDir = path.join(tempDir, "real_sub");
      fs.mkdirSync(realSubDir);
      const internalLink = path.join(tempDir, "link_sub");
      fs.symlinkSync(realSubDir, internalLink, "dir");

      const res = validateWorkspacePath(tempDir, "link_sub/file.py");
      assert.strictEqual(res.ok, true);
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // 6. Write Failures & Rollback
  // --------------------------------------------------------------------------
  test.it("Test 6: Write failure triggers complete rollback and restores modified files", () => {
    const tempDir = createTempDir("write-fail-");
    try {
      const file1 = path.join(tempDir, "file1.py");
      fs.writeFileSync(file1, "file1_original = True\n", "utf-8");

      // Create a directory where file2 would be, so writing to file2 throws EISDIR
      const file2AsDir = path.join(tempDir, "file2.py");
      fs.mkdirSync(file2AsDir);

      const proposal = {
        id: "prop_write_fail",
        change_id: "chg_06",
        evidence: {
          file_changes: [
            {
              file_path: "file1.py",
              proposed_content: "file1_modified = True\n",
              original_content: "file1_original = True\n",
            },
            {
              file_path: "file2.py",
              proposed_content: "file2_content = True\n",
            },
          ],
        },
        status: "validated",
        created_at: new Date().toISOString(),
      };

      patchIntegrityStore.recordReview(proposal, tempDir);
      patchIntegrityStore.recordApproval(proposal.id);

      const changes = extractChangeSet(proposal, tempDir);

      assert.throws(
        () => {
          patchIntegrityStore.applyApprovedChangesSafely(changes, tempDir, proposal.id);
        },
        (err) => {
          // Must report rollback to original state
          assert.match(err.message, /All files successfully rolled back to original state/i);
          return true;
        }
      );

      // Verify file1.py was rolled back to original content
      assert.strictEqual(fs.readFileSync(file1, "utf-8"), "file1_original = True\n");
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // 7. Rollback Failures (Failure Reporting & Preserving Recoverable Backups)
  // --------------------------------------------------------------------------
  test.it("Test 7: Rollback failure reports affected paths and preserves recoverable backups", () => {
    const tempDir = createTempDir("rollback-fail-");
    try {
      const file1 = path.join(tempDir, "file1.py");
      fs.writeFileSync(file1, "file1_pre_patch = 'critical_data'\n", "utf-8");

      const file2AsDir = path.join(tempDir, "file2.py");
      fs.mkdirSync(file2AsDir);

      const proposal = {
        id: "prop_rollback_fail",
        change_id: "chg_07",
        evidence: {
          file_changes: [
            {
              file_path: "file1.py",
              proposed_content: "file1_new = True\n",
              original_content: "file1_pre_patch = 'critical_data'\n",
            },
            {
              file_path: "file2.py",
              proposed_content: "file2_new = True\n",
            },
          ],
        },
        status: "validated",
        created_at: new Date().toISOString(),
      };

      patchIntegrityStore.recordReview(proposal, tempDir);
      patchIntegrityStore.recordApproval(proposal.id);

      const changes = extractChangeSet(proposal, tempDir);

      // Simulate a rollback failure on file1.py by making writeFileSync fail during rollback
      const realWriteFileSync = fs.writeFileSync;
      let hasWrittenFile1 = false;
      let simulateRollbackError = false;

      fs.writeFileSync = function (targetPath, data, options) {
        if (targetPath === file1 && hasWrittenFile1 && simulateRollbackError) {
          throw new Error("EACCES: permission denied during rollback restoration");
        }
        if (targetPath === file1 && !hasWrittenFile1) {
          hasWrittenFile1 = true;
          simulateRollbackError = true;
        }
        return realWriteFileSync.call(fs, targetPath, data, options);
      };

      try {
        assert.throws(
          () => {
            patchIntegrityStore.applyApprovedChangesSafely(changes, tempDir, proposal.id);
          },
          (err) => {
            // NEVER claim complete rollback
            assert.doesNotMatch(err.message, /All files successfully rolled back/i);
            // Must report ROLLBACK FAILED and list affected path
            assert.match(err.message, /ROLLBACK FAILED for 1 file\(s\)/i);
            assert.match(err.message, /file1\.py/i);
            // Must report preserved backup location
            assert.match(err.message, /backup preserved at:/i);
            return true;
          }
        );
      } finally {
        fs.writeFileSync = realWriteFileSync;
      }

      // Verify that a backup file was indeed preserved on disk
      const filesInDir = fs.readdirSync(tempDir);
      const backupFile = filesInDir.find((f) => f.includes("guardian-backup-"));
      assert.ok(backupFile, "A recoverable backup file must exist in directory");
      const backupContent = fs.readFileSync(path.join(tempDir, backupFile), "utf-8");
      assert.strictEqual(
        backupContent,
        "file1_pre_patch = 'critical_data'\n",
        "Preserved backup must match original data"
      );
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // 8. Backend Approval Failure & Status Invariants
  // --------------------------------------------------------------------------
  test.it("Test 8: Backend approval failure revokes local approval and blocks apply", async () => {
    const tempDir = createTempDir("backend-fail-");
    try {
      const file1 = path.join(tempDir, "app.py");
      fs.writeFileSync(file1, "version = 1\n", "utf-8");

      const proposal = {
        id: "prop_backend_fail_008",
        change_id: "chg_08",
        repair_type: "compatibility_adapter",
        target_file: "app.py",
        evidence: {
          file_changes: [
            {
              file_path: "app.py",
              proposed_content: "version = 2\n",
              original_content: "version = 1\n",
            },
          ],
        },
        status: "validated",
        created_at: new Date().toISOString(),
      };

      // Review proposal
      patchIntegrityStore.recordReview(proposal, tempDir);

      // Simulate client approval workflow
      const mockClient = {
        approveRepair: async () => {
          throw new Error("HTTP 500: Database transaction deadlocked");
        },
        getRepair: async (id) => {
          return { ...proposal, status: "validated" }; // Still unapproved on backend
        },
      };

      // In the extension approve command:
      let approvalSucceeded = false;
      try {
        await mockClient.approveRepair(proposal.id);
        patchIntegrityStore.recordApproval(proposal.id);
        approvalSucceeded = true;
      } catch (err) {
        // Backend approval failed: revoke any local approval state
        patchIntegrityStore.revokeApproval(proposal.id);
        approvalSucceeded = false;
      }

      assert.strictEqual(approvalSucceeded, false);

      // Verify store has NO approved patch hash
      const record = patchIntegrityStore.getRecord(proposal.id);
      assert.strictEqual(record.approvedPatchHash, undefined);

      // Attempting to apply must fail because proposal is not approved
      const verification = patchIntegrityStore.verifyBeforeApplication(proposal, tempDir);
      assert.strictEqual(verification.ok, false);
      assert.match(verification.reason, /has not received human approval/i);

      // Backend status requirement check: if proposal status is "validated", applying is rejected
      const liveProposal = await mockClient.getRepair(proposal.id);
      assert.notStrictEqual(liveProposal.status, "approved");
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });
});
