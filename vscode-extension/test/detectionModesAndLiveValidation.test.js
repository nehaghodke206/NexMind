const test = require("node:test");
const assert = require("node:assert");
const path = require("node:path");

// Mock vscode module for node:test runner
const mockConfigStore = new Map([
  ["dependencyGuardian.detectionMode", "hybrid"],
  ["dependencyGuardian.liveValidationConfigPath", "dependency-guardian.yml"],
  ["dependencyGuardian.liveValidationTimeoutSeconds", 4.0],
  ["dependencyGuardian.liveValidationConcurrency", 2],
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
const Module = require("node:module");
const originalRequire = Module.prototype.require;
Module.prototype.require = function (id) {
  if (id === "vscode") return mockVscode;
  return originalRequire.apply(this, arguments);
};

// Load compiled extension components
const { DetectionService } = require("../dist/agents/detectionService");
const { AgentRunner } = require("../dist/agents/agentRunner");
const { getGuardianConfig, updateDetectionMode } = require("../dist/config");

test.describe("Detection Modes & External API Intelligence", () => {
  const workspaceRoot = path.resolve(__dirname, "..", "..");
  const outputChannel = mockVscode.window.createOutputChannel();

  test("1. Detection Mode configuration persistence", async () => {
    // Initial mode from mock
    let config = getGuardianConfig();
    assert.strictEqual(config.detectionMode, "hybrid");

    // Update to algorithmic
    await updateDetectionMode("algorithmic");
    assert.strictEqual(mockConfigStore.get("dependencyGuardian.detectionMode"), "algorithmic");
    assert.strictEqual(getGuardianConfig().detectionMode, "algorithmic");

    // Update to ai
    await updateDetectionMode("ai");
    assert.strictEqual(mockConfigStore.get("dependencyGuardian.detectionMode"), "ai");
    assert.strictEqual(getGuardianConfig().detectionMode, "ai");
  });

  test("2. AgentRunner builds correct CLI arguments for detection mode", () => {
    const runner = new AgentRunner(outputChannel);

    let capturedSpawn = null;
    runner.spawnProcess = (command, args, cwd) => {
      capturedSpawn = { command, args, cwd };
      return Promise.resolve({
        success: true,
        findings: [],
        summary: { total_findings: 0, breaking_count: 0 },
      });
    };

    return runner
      .runDetection(workspaceRoot, {
        baselineSpec: "/tmp/base.json",
        currentSpec: "/tmp/curr.json",
        mode: "ai",
      })
      .then(() => {
        assert.ok(capturedSpawn, "Spawn was executed");
        assert.ok(capturedSpawn.args.includes("--mode"), "CLI args include --mode");
        const modeIndex = capturedSpawn.args.indexOf("--mode");
        assert.strictEqual(capturedSpawn.args[modeIndex + 1], "ai", "CLI args mode value is 'ai'");
      });
  });

  test("3. AgentRunner codebase scan forwards detection mode", () => {
    const runner = new AgentRunner(outputChannel);

    let capturedSpawn = null;
    runner.spawnProcess = (command, args, cwd) => {
      capturedSpawn = { command, args, cwd };
      return Promise.resolve({
        metadata: { scanned_path: workspaceRoot },
        endpoints: [],
        dependencies: [],
        integrations: [],
        discrepancies: [],
        test_coverage: { coverage_percentage: 100 },
      });
    };

    return runner
      .runCodebaseScan(workspaceRoot, {
        repositoryPath: workspaceRoot,
        mode: "hybrid",
      })
      .then(() => {
        assert.ok(capturedSpawn, "Spawn was executed");
        assert.ok(capturedSpawn.args.includes("scan-repo"));
        assert.ok(capturedSpawn.args.includes("--mode"));
        const modeIndex = capturedSpawn.args.indexOf("--mode");
        assert.strictEqual(capturedSpawn.args[modeIndex + 1], "hybrid");
      });
  });

  test("4. AgentRunner live validation builds validate-api arguments and bounds", () => {
    const runner = new AgentRunner(outputChannel);

    let capturedSpawn = null;
    runner.spawnProcess = (command, args, cwd) => {
      capturedSpawn = { command, args, cwd };
      return Promise.resolve({
        total_probes: 2,
        reachable_count: 2,
        auth_failure_count: 0,
        client_error_count: 0,
        server_failure_count: 0,
        unreachable_count: 0,
        contract_mismatch_count: 0,
        security_blocked_count: 0,
        duration_seconds: 0.12,
        results: [],
        findings: [],
        mode: "algorithmic",
        ai_status: "skipped",
      });
    };

    return runner
      .runLiveValidation(workspaceRoot, {
        configPath: "dependency-guardian.yml",
        mode: "algorithmic",
        timeoutSeconds: 5.0,
        concurrency: 3,
      })
      .then((report) => {
        assert.ok(capturedSpawn, "Spawn was executed");
        assert.ok(capturedSpawn.args.includes("validate-api"));
        assert.ok(capturedSpawn.args.includes("--config"));
        const configIdx = capturedSpawn.args.indexOf("--config");
        assert.ok(capturedSpawn.args[configIdx + 1].endsWith("dependency-guardian.yml"));
        assert.ok(capturedSpawn.args.includes("--mode"));
        assert.strictEqual(capturedSpawn.args[capturedSpawn.args.indexOf("--mode") + 1], "algorithmic");
        assert.ok(capturedSpawn.args.includes("--timeout"));
        assert.strictEqual(capturedSpawn.args[capturedSpawn.args.indexOf("--timeout") + 1], "5");
        assert.ok(capturedSpawn.args.includes("--concurrency"));
        assert.strictEqual(capturedSpawn.args[capturedSpawn.args.indexOf("--concurrency") + 1], "3");

        assert.strictEqual(report.total_probes, 2);
        assert.strictEqual(report.reachable_count, 2);
      });
  });

  test("5. DetectionService mapFindingsToChanges preserves provenance and confidence", () => {
    const runner = new AgentRunner(outputChannel);
    const service = new DetectionService(workspaceRoot, outputChannel, runner);

    const findings = [
      {
        id: "finding-live-1",
        rule_id: "RULE-API-AUTH-FAILURE",
        path: "/api/secure-data",
        method: "GET",
        severity: "critical",
        compatibility: "breaking",
        message: "Live probe returned 401 Unauthorized",
        provenance: "live_probe",
        confidence: 0.98,
        recommended_action: "Refresh API token in environment",
        evidence: {
          status_code: 401,
          url: "https://api.example.com/api/secure-data",
          affected_files: ["src/services/secureClient.ts"],
        },
      },
      {
        id: "finding-diff-2",
        rule_id: "RULE-FIELD-TYPE-CHANGED",
        path: "/api/orders",
        method: "POST",
        severity: "high",
        compatibility: "breaking",
        message: "Field 'price' changed from number to string",
        provenance: "contract_diff",
        confidence: 0.90,
        recommended_action: "Cast price parameter",
        evidence: {
          baseline_value: "number",
          observed_value: "string",
          file: "src/api/orders.ts",
        },
      },
    ];

    const mapped = service.mapFindingsToChanges(findings, "order-service");
    assert.strictEqual(mapped.length, 2);

    // Verify finding 1
    const item1 = mapped[0];
    assert.strictEqual(item1.id, "finding-live-1");
    assert.strictEqual(item1.severity, "critical");
    assert.strictEqual(item1.evidence.provenance, "live_probe");
    assert.strictEqual(item1.evidence.confidence, 0.98);
    assert.strictEqual(item1.evidence.recommended_action, "Refresh API token in environment");
    assert.deepStrictEqual(item1.affected_files, ["src/services/secureClient.ts"]);

    // Verify finding 2
    const item2 = mapped[1];
    assert.strictEqual(item2.id, "finding-diff-2");
    assert.strictEqual(item2.severity, "high");
    assert.strictEqual(item2.evidence.provenance, "contract_diff");
    assert.strictEqual(item2.evidence.confidence, 0.90);
    assert.deepStrictEqual(item2.affected_files, ["src/api/orders.ts"]);
  });
});
