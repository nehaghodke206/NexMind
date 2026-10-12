const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

// Mock vscode module for node:test runner
const registeredCommands = new Map();
const executedCommands = [];

const mockVscode = {
  ViewColumn: { One: 1, Two: 2 },
  Uri: {
    file: (p) => ({ fsPath: p, toString: () => `file://${p}` }),
    parse: (u) => ({ fsPath: u, toString: () => u }),
  },
  Position: class {
    constructor(line, character) {
      this.line = line;
      this.character = character;
    }
  },
  Selection: class {
    constructor(anchor, active) {
      this.anchor = anchor;
      this.active = active;
    }
  },
  Range: class {
    constructor(start, end) {
      this.start = start;
      this.end = end;
    }
  },
  TextEditorRevealType: { InCenter: 1 },
  CancellationTokenSource: class {
    constructor() {
      this.token = {
        isCancellationRequested: false,
        onCancellationRequested: (fn) => {
          this._listener = fn;
          return { dispose: () => {} };
        },
      };
    }
    cancel() {
      this.token.isCancellationRequested = true;
      if (this._listener) this._listener();
    }
  },
  EventEmitter: class {
    constructor() {
      this.listeners = [];
    }
    get event() {
      return (listener) => {
        this.listeners.push(listener);
        return { dispose: () => {} };
      };
    }
    fire(data) {
      for (const fn of this.listeners) fn(data);
    }
  },
  commands: {
    executeCommand: (cmd, ...args) => {
      executedCommands.push({ cmd, args });
      const handler = registeredCommands.get(cmd);
      if (handler) {
        return Promise.resolve(handler(...args));
      }
      return Promise.resolve(undefined);
    },
    registerCommand: (cmd, handler) => {
      registeredCommands.set(cmd, handler);
      return { dispose: () => registeredCommands.delete(cmd) };
    },
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
    showQuickPick: () => Promise.resolve(undefined),
    withProgress: (opts, task) => {
      const progress = { report: () => {} };
      const token = { isCancellationRequested: false, onCancellationRequested: () => ({ dispose: () => {} }) };
      return task(progress, token);
    },
    createStatusBarItem: () => ({
      text: "",
      tooltip: "",
      show: () => {},
      hide: () => {},
      dispose: () => {},
    }),
    createWebviewPanel: (viewType, title) => {
      let htmlContent = "";
      return {
        viewType,
        title,
        reveal: () => {},
        dispose: () => {},
        onDidDispose: () => ({ dispose: () => {} }),
        webview: {
          set html(val) { htmlContent = val; },
          get html() { return htmlContent; },
          postMessage: () => Promise.resolve(true),
          onDidReceiveMessage: () => ({ dispose: () => {} }),
        },
      };
    },
    registerTreeDataProvider: () => ({ dispose: () => {} }),
    registerWebviewViewProvider: () => ({ dispose: () => {} }),
  },
  workspace: {
    workspaceFolders: [{ uri: { fsPath: path.resolve(__dirname, "..", "..") } }],
    registerTextDocumentContentProvider: () => ({ dispose: () => {} }),
    openTextDocument: () => Promise.resolve({}),
    getConfiguration: () => ({
      get: (key, def) => def,
      update: () => Promise.resolve(),
    }),
  },
  ThemeIcon: class {
    constructor(id) { this.id = id; }
  },
  ThemeColor: class {
    constructor(id) { this.id = id; }
  },
  TreeItem: class {
    constructor(label) { this.label = label; }
  },
  TreeItemCollapsibleState: { None: 0, Collapsed: 1, Expanded: 2 },
  ProgressLocation: { Notification: 15 },
};

// Patch module loader to provide mock vscode
const Module = require("node:module");
const originalRequire = Module.prototype.require;
Module.prototype.require = function (id) {
  if (id === "vscode") return mockVscode;
  return originalRequire.apply(this, arguments);
};

// Load compiled extension components
const { DetectionService } = require("../dist/agents/detectionService");
const { AgentRunner } = require("../dist/agents/agentRunner");
const { GuardianClient } = require("../dist/api/guardianClient");
const { GuardianDashboardPanel } = require("../dist/webview/guardianPanel");

test.describe("Dependency Guardian Real Detector Agent Integration", () => {
  const workspaceRoot = path.resolve(__dirname, "..", "..");
  const outputChannel = mockVscode.window.createOutputChannel();
  const client = new GuardianClient("http://localhost:8000/api/v1");
  const agentRunner = new AgentRunner(outputChannel);

  // --------------------------------------------------------------------------
  // 1. Detection Service: Drift Findings Mapping
  // --------------------------------------------------------------------------
  test.it("DetectionService: Correctly maps contract findings into standard ChangeItems", () => {
    const service = new DetectionService(agentRunner, client, workspaceRoot, outputChannel);

    const findings = [
      {
        id: "RULE-ENUM-VALUE-REMOVED-/api/v1/payments",
        rule_id: "RULE-ENUM-VALUE-REMOVED",
        compatibility: "breaking",
        severity: "critical",
        path: "/api/v1/payments",
        method: "POST",
        message: "Enum values removed at requestBody: ['crypto']",
        evidence: {
          file: "demo/sample-api/versions/v1/routes/payments.py",
          baseline_value: ["card", "bank", "crypto"],
          observed_value: ["card", "bank"],
        },
      },
      {
        id: "RULE-FIELD-ADDED-OPTIONAL-/api/v1/users",
        rule_id: "RULE-FIELD-ADDED-OPTIONAL",
        compatibility: "non_breaking",
        severity: "low",
        path: "/api/v1/users",
        method: "GET",
        message: "New optional query parameter 'search' was added",
        evidence: {
          observed_value: { name: "search", in: "query", required: false },
        },
      },
    ];

    const changes = service.mapFindingsToChanges(findings, "sample-api");
    assert.strictEqual(changes.length, 2);

    // Verify breaking finding
    const c1 = changes[0];
    assert.strictEqual(c1.id, "RULE-ENUM-VALUE-REMOVED-/api/v1/payments");
    assert.strictEqual(c1.severity, "critical");
    assert.strictEqual(c1.status, "breaking");
    assert.strictEqual(c1.probe_id, "POST /api/v1/payments");
    assert.deepStrictEqual(c1.affected_files, ["demo/sample-api/versions/v1/routes/payments.py"]);

    // Verify non-breaking finding
    const c2 = changes[1];
    assert.strictEqual(c2.id, "RULE-FIELD-ADDED-OPTIONAL-/api/v1/users");
    assert.strictEqual(c2.severity, "low");
    assert.strictEqual(c2.status, "non_breaking");
    assert.strictEqual(c2.probe_id, "GET /api/v1/users");
  });

  // --------------------------------------------------------------------------
  // 2. Detection Service: Missing Files Error Handling
  // --------------------------------------------------------------------------
  test.it("DetectionService: Rejects missing contract specification files with descriptive error", async () => {
    const service = new DetectionService(agentRunner, client, workspaceRoot, outputChannel);

    await assert.rejects(
      async () => {
        await service.detectContractDrift({
          baselinePath: "/nonexistent/baseline.json",
          currentPath: "/nonexistent/current.json",
        });
      },
      (err) => {
        assert.match(err.message, /Baseline contract file not found/);
        return true;
      }
    );

    const state = service.getDriftState();
    assert.strictEqual(state.state, "failed");
    assert.ok(state.error);
  });

  test.it("DetectionService: Rejects missing repository scan path with descriptive error", async () => {
    const service = new DetectionService(agentRunner, client, workspaceRoot, outputChannel);

    await assert.rejects(
      async () => {
        await service.scanCodebase("/nonexistent/repo-path");
      },
      (err) => {
        assert.match(err.message, /Scanned directory does not exist/);
        return true;
      }
    );

    const state = service.getCodebaseState();
    assert.strictEqual(state.state, "failed");
    assert.ok(state.error);
  });

  // --------------------------------------------------------------------------
  // 3. Detection Service: Lifecycle State Event Notifications
  // --------------------------------------------------------------------------
  test.it("DetectionService: Emits state lifecycle events during execution", async () => {
    const service = new DetectionService(agentRunner, client, workspaceRoot, outputChannel);
    const events = [];

    service.onDidChangeState((e) => events.push(e));

    try {
      await service.scanCodebase("/nonexistent/target");
    } catch {}

    assert.strictEqual(events.length, 1);
    assert.strictEqual(events[0].capability, "codebase_scan");
    assert.strictEqual(events[0].state, "failed");
  });

  // --------------------------------------------------------------------------
  // 4. Command Manifest Verification
  // --------------------------------------------------------------------------
  test.it("Manifest: Declares both scanDependencies and scanCodebase commands", () => {
    const pkgPath = path.resolve(__dirname, "..", "package.json");
    const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
    const commands = pkg.contributes.commands.map((c) => c.command);

    assert.ok(commands.includes("dependencyGuardian.scanDependencies"), "scanDependencies must be declared");
    assert.ok(commands.includes("dependencyGuardian.scanCodebase"), "scanCodebase must be declared");
    assert.ok(commands.includes("dependencyGuardian.runDetection"), "runDetection must be declared");
    assert.ok(commands.includes("dependencyGuardian.openDashboard"), "openDashboard must be declared");
  });

  // --------------------------------------------------------------------------
  // 5. Dashboard HTML: Supports both Drift and Codebase Tabs
  // --------------------------------------------------------------------------
  test.it("Dashboard Panel: Renders tab switcher and sections for both capabilities", () => {
    const service = new DetectionService(agentRunner, client, workspaceRoot, outputChannel);
    GuardianDashboardPanel.createOrShow(
      mockVscode.Uri.file(path.resolve(__dirname, "..")),
      client,
      undefined,
      agentRunner,
      workspaceRoot,
      service
    );

    const html = GuardianDashboardPanel.currentPanel._panel.webview.html;

    // Tab buttons
    assert.match(html, /id="tabBtnDrift"/);
    assert.match(html, /id="tabBtnCodebase"/);
    assert.match(html, /switchTab\('drift'\)/);
    assert.match(html, /switchTab\('codebase'\)/);

    // Both capability sections
    assert.match(html, /id="tabDrift"/);
    assert.match(html, /id="tabCodebase"/);
    assert.match(html, /id="endpointsTableContainer"/);
    assert.match(html, /id="discrepanciesList"/);
    assert.match(html, /id="depsAndIntegrationsList"/);
    assert.match(html, /id="deliverablesList"/);

    // Metrics
    assert.match(html, /id="metricServices"/);
    assert.match(html, /id="metricEndpoints"/);
    assert.match(html, /id="metricChanges"/);
    assert.match(html, /id="metricBreaking"/);
    assert.match(html, /id="metricCoverage"/);

    // Status badges
    assert.match(html, /id="detectorStatusBadge"/);
    assert.match(html, /id="statusBadge"/);

    GuardianDashboardPanel.currentPanel.dispose();
  });
});
