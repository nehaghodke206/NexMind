const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");

// Setup mock vscode for node:test runner
const registeredCommands = new Map();
const mockConfig = new Map();

const mockVscode = {
  ViewColumn: { One: 1, Two: 2 },
  Uri: {
    file: (p) => ({ fsPath: p, toString: () => `file://${p}` }),
    parse: (u) => ({ fsPath: u, toString: () => u }),
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
  commands: {
    executeCommand: (cmd, ...args) => {
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
  },
  workspace: {
    workspaceFolders: [{ uri: { fsPath: path.resolve(__dirname, "..", "..") } }],
    getConfiguration: (section) => ({
      get: (key, def) => {
        const fullKey = section ? `${section}.${key}` : key;
        return mockConfig.has(fullKey) ? mockConfig.get(fullKey) : def;
      },
      update: (key, val) => {
        const fullKey = section ? `${section}.${key}` : key;
        mockConfig.set(fullKey, val);
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

// Load compiled agent runner
const { AgentRunner } = require("../dist/agents/agentRunner");

function createTempDir(prefix = "guardian-test-") {
  return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

test.describe("Dependency Guardian Agent and Python Resolution Suite", () => {
  const outputChannel = mockVscode.window.createOutputChannel();
  let runner;

  test.beforeEach(() => {
    mockConfig.clear();
    runner = new AgentRunner(outputChannel);
    delete process.env.DEPENDENCY_GUARDIAN_AGENT_PATH;
    delete process.env.DEPENDENCY_GUARDIAN_ROOT;
    delete process.env.PYTHON_PATH;
  });

  // --------------------------------------------------------------------------
  // 1. Agent Root Discovery with Foreign Target Workspace
  // --------------------------------------------------------------------------
  test.it("Test 1: Resolves agent paths correctly when target workspace is an external repository", () => {
    const foreignWorkspace = createTempDir("foreign-repo-");
    try {
      const paths = runner.resolveAgentPaths(foreignWorkspace);

      // Detection directory should be located in HackWave even though workspaceRoot is foreign
      assert.ok(paths.detectionDir, "Must discover detection directory");
      assert.ok(fs.existsSync(paths.detectionDir), "Discovered detection directory must exist on disk");
      assert.ok(
        fs.existsSync(path.join(paths.detectionDir, "dependency_guardian")),
        "Detection directory must contain dependency_guardian package"
      );
      assert.notStrictEqual(
        paths.detectionDir,
        path.join(foreignWorkspace, "agents", "detection"),
        "Must NOT assume detection directory is inside foreign workspace"
      );

      // Process environment must have PYTHONPATH pointing to detection directory
      const env = runner.buildProcessEnv(foreignWorkspace);
      assert.ok(env.PYTHONPATH, "PYTHONPATH must be set");
      assert.ok(
        env.PYTHONPATH.includes(paths.detectionDir),
        "PYTHONPATH must include genuine detection directory"
      );
    } finally {
      fs.rmSync(foreignWorkspace, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // 2. Explicit Agent Path Configuration
  // --------------------------------------------------------------------------
  test.it("Test 2: Respects explicit dependencyGuardian.agentPath configuration", () => {
    const customAgentDir = createTempDir("custom-agent-");
    const customDetDir = path.join(customAgentDir, "dependency_guardian");
    fs.mkdirSync(customDetDir, { recursive: true });

    try {
      mockConfig.set("dependencyGuardian.agentPath", customAgentDir);

      const paths = runner.resolveAgentPaths("/tmp/any-repo");
      assert.strictEqual(paths.detectionDir, customAgentDir);
    } finally {
      fs.rmSync(customAgentDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // 3. Priority 1: Configured Python Path
  // --------------------------------------------------------------------------
  test.it("Test 3A: Configured pythonPath that does not exist throws actionable error", async () => {
    mockConfig.set("dependencyGuardian.pythonPath", "/nonexistent/bin/python3");

    await assert.rejects(
      async () => {
        await runner.resolveAndValidatePython("/tmp/test-workspace");
      },
      (err) => {
        assert.match(err.message, /Configured Python interpreter does not exist/i);
        assert.match(err.message, /dependencyGuardian\.pythonPath/);
        return true;
      }
    );
  });

  test.it("Test 3B: Configured pythonPath that fails module import produces actionable diagnostics", async () => {
    // Point to system python with an environment that cannot find dependency_guardian
    mockConfig.set("dependencyGuardian.pythonPath", "/usr/bin/python3");
    // Override resolveAgentPaths temporarily to simulate isolated environment
    const origResolveAgentPaths = runner.resolveAgentPaths.bind(runner);
    runner.resolveAgentPaths = () => ({});

    try {
      await assert.rejects(
        async () => {
          await runner.resolveAndValidatePython("/tmp/test-workspace");
        },
        (err) => {
          assert.match(err.message, /failed validation/i);
          assert.match(err.message, /Cannot import 'dependency_guardian'/i);
          assert.match(err.message, /Actionable fix/i);
          assert.match(err.message, /pip install -e/i);
          return true;
        }
      );
    } finally {
      runner.resolveAgentPaths = origResolveAgentPaths;
    }
  });

  // --------------------------------------------------------------------------
  // 4. Priority 2: Virtual Environment Resolution
  // --------------------------------------------------------------------------
  test.it("Test 4: Discovers and validates virtual environment over unvalidated fallback", async () => {
    const foreignWorkspace = createTempDir("foreign-repo-");
    try {
      const res = await runner.resolveAndValidatePython(foreignWorkspace);
      assert.ok(res.pythonPath, "Must resolve a python binary");
      assert.ok(fs.existsSync(res.pythonPath), "Resolved binary must exist");
      assert.strictEqual(res.canImportDetection, true, "Must be capable of importing dependency_guardian");
      assert.ok(res.major >= 3 && res.minor >= 11, "Python version must be >= 3.11");
      // Must be virtualenv or system python that can import detection
      assert.ok(res.source === "virtualenv" || res.source === "system");
    } finally {
      fs.rmSync(foreignWorkspace, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // 5. Missing Agent Package & Missing Virtualenv
  // --------------------------------------------------------------------------
  test.it("Test 5: Missing agent package and missing virtualenv produces complete actionable diagnostic", async () => {
    const isolatedRunner = new AgentRunner(outputChannel);
    isolatedRunner.resolveAgentPaths = () => ({});
    isolatedRunner.findVirtualEnvCandidates = () => [];
    isolatedRunner.findSystemPythonCandidates = () => ["/usr/bin/python3"];

    await assert.rejects(
      async () => {
        await isolatedRunner.resolveAndValidatePython("/home/user/foreign_project");
      },
      (err) => {
        assert.match(err.message, /Failed to locate a Python environment/i);
        assert.match(err.message, /Target Workspace:\s+\/home\/user\/foreign_project/);
        assert.match(err.message, /Agent Directory:\s+Not found/);
        assert.match(err.message, /dependencyGuardian\.agentPath/);
        assert.match(err.message, /dependencyGuardian\.pythonPath/);
        assert.match(err.message, /pip install -e/i);
        return true;
      }
    );
  });

  // --------------------------------------------------------------------------
  // 6. Paths Containing Spaces
  // --------------------------------------------------------------------------
  test.it("Test 6: Handles workspaces and repository paths containing spaces safely", () => {
    const spaceWorkspace = createTempDir("workspace with space-");
    try {
      const env = runner.buildProcessEnv(spaceWorkspace);
      assert.ok(env.PYTHONPATH);

      // Verify that the path with spaces is in PYTHONPATH intact
      const parts = env.PYTHONPATH.split(path.delimiter);
      assert.ok(parts.some((p) => p === spaceWorkspace));

      // Test virtualenv discovery within spaces folder does not crash
      const candidates = runner.findVirtualEnvCandidates(spaceWorkspace);
      assert.ok(Array.isArray(candidates));
    } finally {
      fs.rmSync(spaceWorkspace, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // 7. Successful Scan Result Parsing & Fallback File
  // --------------------------------------------------------------------------
  test.it("Test 7: Correctly parses valid repository inventory and uses fallback file if needed", async () => {
    const tempDir = createTempDir("scan-test-");
    const invFile = path.join(tempDir, "repository-inventory.json");
    const mockInventory = {
      metadata: {
        scanner_name: "Dependency Guardian Repository Intelligence",
        scanner_version: "0.2.0",
        scanned_path: tempDir,
        scan_timestamp: new Date().toISOString(),
        languages_detected: ["Python"],
        frameworks_detected: ["FastAPI"],
        total_files_scanned: 10,
        openapi_specs_found: [],
      },
      dependencies: [{ name: "fastapi", version: "0.100.0", is_used: true }],
      unused_dependencies: [],
      integrations: [],
      endpoints: [{ method: "GET", path: "/health", line_number: 12 }],
      discrepancies: [],
      test_coverage: {
        total_endpoints: 1,
        tested_endpoints: 1,
        untested_endpoints: 0,
        coverage_percentage: 100,
        endpoint_coverage_map: {},
        integration_tests_found: [],
      },
    };
    fs.writeFileSync(invFile, JSON.stringify(mockInventory), "utf-8");

    try {
      // Test fallback file loader in spawnProcess
      // Call spawnProcess with a dummy echo that outputs non-json stdout
      const result = await runner["spawnProcess"](
        "/bin/echo",
        ["Logging preamble without json output"],
        tempDir,
        10,
        undefined,
        invFile
      );

      assert.strictEqual(result.metadata.scanner_name, "Dependency Guardian Repository Intelligence");
      assert.strictEqual(result.dependencies.length, 1);
      assert.strictEqual(result.endpoints[0].path, "/health");
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  // --------------------------------------------------------------------------
  // 8. Cancellation Token & Timeout Handling
  // --------------------------------------------------------------------------
  test.it("Test 8A: Cancellation token immediately aborts running agent process", async () => {
    const cts = new mockVscode.CancellationTokenSource();
    const tempDir = createTempDir("cancel-test-");

    try {
      const processPromise = runner["spawnProcess"](
        "/bin/sleep",
        ["30"],
        tempDir,
        15,
        cts.token
      );

      // Trigger cancellation shortly after starting
      setTimeout(() => cts.cancel(), 50);

      await assert.rejects(
        processPromise,
        (err) => {
          assert.match(err.message, /cancelled by the user/i);
          return true;
        }
      );
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test.it("Test 8B: Process timeout triggers rejection after specified duration", async () => {
    const tempDir = createTempDir("timeout-test-");

    try {
      await assert.rejects(
        runner["spawnProcess"](
          "/bin/sleep",
          ["10"],
          tempDir,
          1 // 1 second timeout
        ),
        (err) => {
          assert.match(err.message, /timed out after 1 seconds/i);
          return true;
        }
      );
    } finally {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
  });
});
