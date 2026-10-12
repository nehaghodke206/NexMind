const test = require("node:test");
const assert = require("node:assert");
const path = require("node:path");
const fs = require("node:fs");

// Mock config store for VS Code settings
const mockConfigStore = new Map([
  ["dependencyGuardian.detectionMode", "algorithmic"],
  ["dependencyGuardian.backendUrl", "http://127.0.0.1:8000/api/v1"],
  ["dependencyGuardian.autoSyncBackend", true],
  ["dependencyGuardian.projectId", ""],
  ["dependencyGuardian.dependencyId", ""],
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
const { GuardianClient } = require("../dist/api/guardianClient");

test.describe("Contract Drift Backend Synchronization & ID Resolution Suite", () => {
  const workspaceRoot = path.resolve(__dirname, "..", "..");
  const outputChannel = mockVscode.window.createOutputChannel();
  const baselineSpec = path.join(workspaceRoot, "demo", "sample-api", "contracts", "openapi-v1.json");
  const currentSpec = path.join(workspaceRoot, "demo", "sample-api", "contracts", "openapi-v2.json");

  test("1. Detection with sync disabled: omits sync flags and succeeds without IDs", async () => {
    mockConfigStore.set("dependencyGuardian.projectId", "");
    mockConfigStore.set("dependencyGuardian.dependencyId", "");

    const runner = new AgentRunner(outputChannel);
    let capturedArgs = null;
    runner.spawnProcess = (cmd, args) => {
      capturedArgs = args;
      return Promise.resolve({
        success: true,
        findings: [],
        summary: { total_findings: 0, breaking_count: 0 },
      });
    };

    const client = new GuardianClient("http://127.0.0.1:8000/api/v1");
    // Client should not be contacted when sync is false
    client.getProjects = () => Promise.reject(new Error("Should not be called"));

    const service = new DetectionService(runner, client, workspaceRoot, outputChannel);

    const result = await service.detectContractDrift({
      baselinePath: baselineSpec,
      currentPath: currentSpec,
      syncBackend: false,
    });

    assert.ok(result);
    assert.strictEqual(result.success, true);
    assert.ok(capturedArgs, "AgentRunner executed process");
    assert.ok(!capturedArgs.includes("--sync-backend"), "CLI args must NOT include --sync-backend");
    assert.ok(!capturedArgs.includes("--project-id"), "CLI args must NOT include --project-id");
    assert.ok(!capturedArgs.includes("--dependency-id"), "CLI args must NOT include --dependency-id");
  });

  test("2. Detection with sync enabled and valid explicit/persisted IDs: passes sync flags directly", async () => {
    const runner = new AgentRunner(outputChannel);
    let capturedArgs = null;
    runner.spawnProcess = (cmd, args) => {
      capturedArgs = args;
      return Promise.resolve({
        success: true,
        findings: [
          {
            id: "f1",
            rule_id: "RULE-BREAKING",
            severity: "high",
            compatibility: "breaking",
            path: "/api/v1/test",
            method: "POST",
            message: "Breaking change detected",
          },
        ],
        summary: { total_findings: 1, breaking_count: 1 },
      });
    };

    let ingestedPayload = null;
    const client = new GuardianClient("http://127.0.0.1:8000/api/v1");
    client.ingestScanRun = (projectId, payload) => {
      ingestedPayload = { projectId, payload };
      return Promise.resolve({ id: "scan-123" });
    };

    const service = new DetectionService(runner, client, workspaceRoot, outputChannel);

    const result = await service.detectContractDrift({
      baselinePath: baselineSpec,
      currentPath: currentSpec,
      syncBackend: true,
      projectId: "proj-explicit-123",
      dependencyId: "dep-explicit-456",
    });

    assert.ok(result);
    assert.strictEqual(result.success, true);
    assert.ok(capturedArgs.includes("--sync-backend"), "CLI args must include --sync-backend");
    const pIdx = capturedArgs.indexOf("--project-id");
    const dIdx = capturedArgs.indexOf("--dependency-id");
    assert.strictEqual(capturedArgs[pIdx + 1], "proj-explicit-123");
    assert.strictEqual(capturedArgs[dIdx + 1], "dep-explicit-456");

    assert.ok(ingestedPayload, "Backend ingestion occurred");
    assert.strictEqual(ingestedPayload.projectId, "proj-explicit-123");
  });

  test("3. Detection with sync enabled and missing IDs: discovers and persists from backend", async () => {
    mockConfigStore.set("dependencyGuardian.projectId", "");
    mockConfigStore.set("dependencyGuardian.dependencyId", "");

    const runner = new AgentRunner(outputChannel);
    let capturedArgs = null;
    runner.spawnProcess = (cmd, args) => {
      capturedArgs = args;
      return Promise.resolve({
        success: true,
        findings: [],
        summary: { total_findings: 0, breaking_count: 0 },
      });
    };

    const client = new GuardianClient("http://127.0.0.1:8000/api/v1");
    client.getProjects = () =>
      Promise.resolve([
        { id: "backend-proj-uuid-999", name: "demo-shop" },
      ]);
    client.getProjectDependencies = (pId) =>
      Promise.resolve([
        { id: "backend-dep-uuid-888", project_id: pId, name: "demo-api" },
      ]);
    client.ingestScanRun = () => Promise.resolve({ id: "scan-999" });

    const service = new DetectionService(runner, client, workspaceRoot, outputChannel);

    const result = await service.detectContractDrift({
      baselinePath: baselineSpec,
      currentPath: currentSpec,
      syncBackend: true,
    });

    assert.ok(result);
    assert.strictEqual(result.success, true);
    assert.ok(capturedArgs.includes("--sync-backend"));
    const pIdx = capturedArgs.indexOf("--project-id");
    const dIdx = capturedArgs.indexOf("--dependency-id");
    assert.strictEqual(capturedArgs[pIdx + 1], "backend-proj-uuid-999");
    assert.strictEqual(capturedArgs[dIdx + 1], "backend-dep-uuid-888");

    // IDs should now be persisted in configuration
    assert.strictEqual(mockConfigStore.get("dependencyGuardian.projectId"), "backend-proj-uuid-999");
    assert.strictEqual(mockConfigStore.get("dependencyGuardian.dependencyId"), "backend-dep-uuid-888");
  });

  test("4. Detection with sync enabled and empty backend: auto-registers project & dependency and persists IDs", async () => {
    mockConfigStore.set("dependencyGuardian.projectId", "");
    mockConfigStore.set("dependencyGuardian.dependencyId", "");

    const runner = new AgentRunner(outputChannel);
    let capturedArgs = null;
    runner.spawnProcess = (cmd, args) => {
      capturedArgs = args;
      return Promise.resolve({
        success: true,
        findings: [],
        summary: { total_findings: 0, breaking_count: 0 },
      });
    };

    let registeredProject = null;
    let registeredDep = null;
    const client = new GuardianClient("http://127.0.0.1:8000/api/v1");
    client.getProjects = () => Promise.resolve([]);
    client.createProject = (name, desc) => {
      registeredProject = { id: "created-proj-uuid-111", name };
      return Promise.resolve(registeredProject);
    };
    client.getProjectDependencies = () => Promise.resolve([]);
    client.createDependency = (pId, dep) => {
      registeredDep = { id: "created-dep-uuid-222", project_id: pId, name: dep.name };
      return Promise.resolve(registeredDep);
    };
    client.ingestScanRun = () => Promise.resolve({ id: "scan-111" });

    const service = new DetectionService(runner, client, workspaceRoot, outputChannel);

    const result = await service.detectContractDrift({
      baselinePath: baselineSpec,
      currentPath: currentSpec,
      syncBackend: true,
    });

    assert.ok(result);
    assert.ok(registeredProject, "Project was registered on backend");
    assert.ok(registeredDep, "Dependency was registered on backend");
    assert.strictEqual(mockConfigStore.get("dependencyGuardian.projectId"), "created-proj-uuid-111");
    assert.strictEqual(mockConfigStore.get("dependencyGuardian.dependencyId"), "created-dep-uuid-222");

    const pIdx = capturedArgs.indexOf("--project-id");
    const dIdx = capturedArgs.indexOf("--dependency-id");
    assert.strictEqual(capturedArgs[pIdx + 1], "created-proj-uuid-111");
    assert.strictEqual(capturedArgs[dIdx + 1], "created-dep-uuid-222");
  });

  test("5. Detection with sync enabled when backend is unreachable: honest actionable error, no fake IDs, no silent skip", async () => {
    mockConfigStore.set("dependencyGuardian.projectId", "");
    mockConfigStore.set("dependencyGuardian.dependencyId", "");

    const runner = new AgentRunner(outputChannel);
    let processSpawned = false;
    runner.spawnProcess = () => {
      processSpawned = true;
      return Promise.resolve({});
    };

    const client = new GuardianClient("http://127.0.0.1:8000/api/v1");
    client.getProjects = () => Promise.reject(new Error("ECONNREFUSED"));

    const service = new DetectionService(runner, client, workspaceRoot, outputChannel);

    await assert.rejects(
      async () => {
        await service.detectContractDrift({
          baselinePath: baselineSpec,
          currentPath: currentSpec,
          syncBackend: true,
        });
      },
      (err) => {
        assert.ok(
          err.message.includes("Backend synchronization requires valid Project ID and Dependency ID"),
          `Expected actionable message, got: ${err.message}`
        );
        assert.ok(err.message.includes("ECONNREFUSED"));
        return true;
      }
    );

    assert.strictEqual(processSpawned, false, "Must not spawn doomed detection process");
    assert.strictEqual(mockConfigStore.get("dependencyGuardian.projectId"), "", "Must not generate fake IDs");
  });

  test("6. AgentRunner fast-fails if syncBackend: true is passed with empty IDs", async () => {
    const runner = new AgentRunner(outputChannel);
    let processSpawned = false;
    runner.spawnProcess = () => {
      processSpawned = true;
      return Promise.resolve({});
    };

    await assert.rejects(
      async () => {
        await runner.runDetection(workspaceRoot, {
          baselinePath: baselineSpec,
          currentPath: currentSpec,
          syncBackend: true,
          projectId: "",
          dependencyId: "",
        });
      },
      (err) => {
        assert.ok(
          err.message.includes("Backend synchronization requested, but both Project ID and Dependency ID are required"),
          `Expected validation error, got: ${err.message}`
        );
        return true;
      }
    );

    assert.strictEqual(processSpawned, false, "Must not spawn CLI process without required sync IDs");
  });

  test("7. Workspace metadata extraction accurately extracts project & dependency from dependency-guardian.yml", () => {
    const runner = new AgentRunner(outputChannel);
    const client = new GuardianClient("http://127.0.0.1:8000/api/v1");
    const service = new DetectionService(runner, client, workspaceRoot, outputChannel);

    const meta = service.extractWorkspaceMetadata();
    assert.strictEqual(meta.projectName, "demo-shop");
    assert.ok(meta.dependencyName, "Should have discovered dependency name");
  });
});
