const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const cp = require("node:child_process");
const EventEmitter = require("node:events");

// Mock vscode module for node:test runner
const mockVscode = {
  ViewColumn: { One: 1, Two: 2 },
  Uri: {
    file: (p) => ({ fsPath: p, toString: () => `file://${p}` }),
  },
  CancellationTokenSource: class {
    constructor() {
      this._emitter = new EventEmitter();
      this.token = {
        isCancellationRequested: false,
        onCancellationRequested: (fn) => {
          this._emitter.on("cancel", fn);
          return { dispose: () => this._emitter.off("cancel", fn) };
        },
      };
    }
    cancel() {
      this.token.isCancellationRequested = true;
      this._emitter.emit("cancel");
    }
    dispose() {
      this._emitter.removeAllListeners();
    }
  },
  EventEmitter: class {
    constructor() {
      this.listeners = [];
    }
    get event() {
      return (listener) => {
        this.listeners.push(listener);
        return {
          dispose: () => {
            const idx = this.listeners.indexOf(listener);
            if (idx >= 0) this.listeners.splice(idx, 1);
          },
        };
      };
    }
    fire(data) {
      for (const fn of [...this.listeners]) fn(data);
    }
  },
  workspace: {
    getConfiguration: () => ({
      get: (key, def) => def,
      update: () => Promise.resolve(),
    }),
    workspaceFolders: [{ uri: { fsPath: path.resolve(__dirname, "..") } }],
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
};

const Module = require("node:module");
const originalRequire = Module.prototype.require;
Module.prototype.require = function (id) {
  if (id === "vscode") return mockVscode;
  return originalRequire.apply(this, arguments);
};

const { AgentRunner } = require("../dist/agents/agentRunner");
const { DetectionService } = require("../dist/agents/detectionService");

class MockOutputChannel {
  constructor() {
    this.lines = [];
  }
  append(text) {
    this.lines.push(text);
  }
  appendLine(line) {
    this.lines.push(line);
  }
  show() {}
  dispose() {}
}

test("AgentRunner parses streaming progress events split across stderr chunks", async () => {
  const output = new MockOutputChannel();
  const runner = new AgentRunner(output);

  // We test spawnProcess streaming logic by stubbing cp.spawn
  const originalSpawn = cp.spawn;
  const progressEvents = [];

  const fakeChild = new EventEmitter();
  fakeChild.stdout = new EventEmitter();
  fakeChild.stderr = new EventEmitter();
  fakeChild.kill = () => {};

  cp.spawn = () => fakeChild;

  try {
    const promise = runner.spawnProcess(
      "fake-python",
      ["scan-repo"],
      process.cwd(),
      10,
      undefined,
      undefined,
      (prog) => progressEvents.push(prog)
    );

    // Emit standard stderr log line
    fakeChild.stderr.emit("data", Buffer.from("INFO: Initializing scanner\n"));

    // Emit chunk 1 of JSON line progress
    fakeChild.stderr.emit("data", Buffer.from('{"type": "progress", "phase": "discovering_files", "message": "Discovered '));
    // Emit chunk 2 completing the line
    fakeChild.stderr.emit("data", Buffer.from('42 files", "files_discovered": 42}\n'));

    // Emit next phase progress
    fakeChild.stderr.emit(
      "data",
      Buffer.from('{"type": "progress", "phase": "analyzing_source", "message": "AST scan", "files_processed": 10, "total_files": 42}\n')
    );

    // Emit final json stdout and close
    fakeChild.stdout.emit("data", Buffer.from(JSON.stringify({ metadata: { scanner_name: "test" }, endpoints: [] })));
    fakeChild.emit("close", 0);

    const result = await promise;

    assert.strictEqual(result.metadata.scanner_name, "test");
    assert.strictEqual(progressEvents.length, 2);
    assert.strictEqual(progressEvents[0].phase, "discovering_files");
    assert.strictEqual(progressEvents[0].message, "Discovered 42 files");
    assert.strictEqual(progressEvents[1].phase, "analyzing_source");
    assert.strictEqual(progressEvents[1].files_processed, 10);
    assert.strictEqual(progressEvents[1].total_files, 42);
    assert.strictEqual(typeof progressEvents[0].elapsedSeconds, "number");
  } finally {
    cp.spawn = originalSpawn;
  }
});

test("AgentRunner supports cancellation token and terminates child process", async () => {
  const output = new MockOutputChannel();
  const runner = new AgentRunner(output);
  const cts = new mockVscode.CancellationTokenSource();

  let killedWith = null;
  const fakeChild = new EventEmitter();
  fakeChild.stdout = new EventEmitter();
  fakeChild.stderr = new EventEmitter();
  fakeChild.kill = (sig) => {
    killedWith = sig;
  };

  const originalSpawn = cp.spawn;
  cp.spawn = () => fakeChild;

  try {
    const promise = runner.spawnProcess(
      "fake-python",
      ["scan-repo"],
      process.cwd(),
      10,
      cts.token
    );

    // Trigger cancellation
    cts.cancel();

    await assert.rejects(
      promise,
      /Agent process was cancelled by the user/
    );
    assert.strictEqual(killedWith, "SIGTERM");
  } finally {
    cp.spawn = originalSpawn;
    cts.dispose();
  }
});

test("AgentRunner terminates process on timeout", async () => {
  const output = new MockOutputChannel();
  const runner = new AgentRunner(output);

  let killedWith = null;
  const fakeChild = new EventEmitter();
  fakeChild.stdout = new EventEmitter();
  fakeChild.stderr = new EventEmitter();
  fakeChild.kill = (sig) => {
    killedWith = sig;
  };

  const originalSpawn = cp.spawn;
  cp.spawn = () => fakeChild;

  try {
    // 0.1 second timeout
    const promise = runner.spawnProcess(
      "fake-python",
      ["scan-repo"],
      process.cwd(),
      0.1
    );

    await assert.rejects(
      promise,
      /Agent process timed out after 0.1 seconds/
    );
    assert.strictEqual(killedWith, "SIGTERM");
  } finally {
    cp.spawn = originalSpawn;
  }
});

test("DetectionService lifecycle streams progress and notifies onDidChangeState", async () => {
  const output = new MockOutputChannel();
  const runner = new AgentRunner(output);
  const mockClient = {};
  const service = new DetectionService(runner, mockClient, process.cwd(), output);

  const stateEvents = [];
  service.onDidChangeState((e) => stateEvents.push(e));

  // Stub runner.runCodebaseScan to simulate progress events
  runner.runCodebaseScan = async (root, options) => {
    if (options.onProgress) {
      options.onProgress({
        phase: "discovering_files",
        message: "Inventorying source tree",
        filesDiscovered: 20,
        elapsedSeconds: 1,
      });
      options.onProgress({
        phase: "analyzing_source",
        message: "AST parsing",
        filesProcessed: 10,
        totalFiles: 20,
        elapsedSeconds: 2,
      });
    }
    return {
      metadata: { total_files_scanned: 20 },
      dependencies: [{ package_name: "httpx", is_used: true }],
      endpoints: [],
      integrations: [{ service_name: "user-service" }],
      discrepancies: [],
      test_coverage: { coverage_percentage: 100 },
    };
  };

  const inventory = await service.scanCodebase(process.cwd());

  assert.strictEqual(inventory.dependencies.length, 1);
  assert.strictEqual(inventory.integrations.length, 1);
  assert.strictEqual(service.getCodebaseState().state, "succeeded");

  // Verify state transitions:
  // 1: running (starting)
  // 2: running (discovering_files)
  // 3: running (analyzing_source)
  // 4: succeeded
  assert.ok(stateEvents.length >= 3);
  assert.strictEqual(stateEvents[0].state, "running");
  assert.strictEqual(stateEvents[stateEvents.length - 1].state, "succeeded");
  assert.strictEqual(stateEvents[stateEvents.length - 1].codebaseResult, inventory);
});

test("DetectionService.cancelCodebaseScan cancels active scan", async () => {
  const output = new MockOutputChannel();
  const runner = new AgentRunner(output);
  const mockClient = {};
  const service = new DetectionService(runner, mockClient, process.cwd(), output);

  runner.runCodebaseScan = async (root, options) => {
    return new Promise((resolve, reject) => {
      if (options.cancellationToken) {
        options.cancellationToken.onCancellationRequested(() => {
          reject(new Error("Agent process was cancelled by the user."));
        });
      }
    });
  };

  const scanPromise = service.scanCodebase(process.cwd());

  // Cancel immediately
  const didCancel = service.cancelCodebaseScan();
  assert.strictEqual(didCancel, true);

  await assert.rejects(scanPromise, /cancelled by the user/);
  assert.strictEqual(service.getCodebaseState().state, "canceled");
});
