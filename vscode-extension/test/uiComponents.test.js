const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const Module = require("node:module");

// Setup lightweight vscode mock for Node test runner
const registeredCommands = new Map();
const executedCommands = [];

const mockVscode = {
  ViewColumn: {
    One: 1,
    Two: 2,
  },
  Uri: {
    file: (p) => ({ fsPath: p, toString: () => `file://${p}` }),
    parse: (u) => ({ fsPath: u, toString: () => u }),
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
    activeTextEditor: undefined,
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
    showInformationMessage: (msg, ...items) => Promise.resolve(items[0]),
    showWarningMessage: (msg, ...items) => Promise.resolve(items[0]),
    showErrorMessage: (msg, ...items) => Promise.resolve(items[0]),
    withProgress: (_options, task) => task({ report: () => {} }, {}),
    createOutputChannel: () => ({
      appendLine: () => {},
      show: () => {},
      dispose: () => {},
    }),
  },
  env: {
    clipboard: {
      writeText: () => Promise.resolve(),
    },
  },
};

const originalLoad = Module._load;
Module._load = function (request, parent, isMain) {
  if (request === "vscode") {
    return mockVscode;
  }
  return originalLoad.apply(this, arguments);
};

const { GuardianChatViewProvider } = require("../dist/views/chatView");
const { GuardianDashboardPanel } = require("../dist/webview/guardianPanel");

class MockGuardianClient {
  constructor(baseUrl = "http://localhost:8000/api/v1") {
    this.baseUrl = baseUrl;
    this.isHealthy = true;
    this.changes = [];
    this.repairs = [];
  }
  getBaseUrl() {
    return this.baseUrl;
  }
  setBaseUrl(u) {
    this.baseUrl = u;
  }
  async getHealth() {
    if (!this.isHealthy) throw new Error("Connection refused");
    return { status: "ok", version: "1.0.0" };
  }
  async getChanges() {
    return this.changes;
  }
  async getServices() {
    return [{ id: "srv_1", name: "Users API", version: "1.0.0" }];
  }
  async getChangeImpact(changeId) {
    return [
      {
        change_id: changeId,
        workflow_name: "User Authentication",
        impact_level: "high",
        affected_endpoints: ["/api/v1/users/login"],
      },
    ];
  }
  async getRepairProposals(changeId) {
    return this.repairs.filter((r) => r.change_id === changeId);
  }
  async getRepair(repairId) {
    return this.repairs.find((r) => r.id === repairId);
  }
  async createRepairProposal(changeId) {
    const prop = {
      id: `prop_${Date.now()}`,
      change_id: changeId,
      repair_type: "compatibility_adapter",
      target_file: "users_client.py",
      proposed_code_snippet: "user.get('name')",
      diff: "--- a/users_client.py\n+++ b/users_client.py\n@@ -1 +1 @@\n-user['name']\n+user.get('name')",
      confidence: 0.95,
      status: "proposed",
      created_at: new Date().toISOString(),
    };
    this.repairs.push(prop);
    return prop;
  }
}

test.describe("Guardian UI Redesign & Restrained Theme Suite", () => {
  test.beforeEach(() => {
    executedCommands.length = 0;
  });

  // --------------------------------------------------------------------------
  // 1. Chat Provider Initialization & Auto-Dashboard Opening
  // --------------------------------------------------------------------------
  test.it("Chat Provider: Auto-opens main dashboard when view resolves", () => {
    const client = new MockGuardianClient();
    const provider = new GuardianChatViewProvider(mockVscode.Uri.file("/ext"), client);

    const mockWebviewView = {
      webview: {
        options: {},
        html: "",
        onDidReceiveMessage: () => ({ dispose: () => {} }),
        postMessage: () => Promise.resolve(true),
      },
      onDidChangeVisibility: () => ({ dispose: () => {} }),
      visible: true,
    };

    provider.resolveWebviewView(mockWebviewView, {}, {});

    // Must have executed openDashboard command
    const openCmd = executedCommands.find((c) => c.cmd === "dependencyGuardian.openDashboard");
    assert.ok(openCmd, "Opening sidebar container must trigger dependencyGuardian.openDashboard");

    const msgs = provider.getMessages();
    assert.strictEqual(msgs.length, 1);
    assert.match(msgs[0].content, /Guardian Assistant \(UI Preview\)/i);
  });

  // --------------------------------------------------------------------------
  // 2. Chat Empty Message Prevention
  // --------------------------------------------------------------------------
  test.it("Chat Provider: Prevents empty or whitespace-only messages", async () => {
    const client = new MockGuardianClient();
    const provider = new GuardianChatViewProvider(mockVscode.Uri.file("/ext"), client);
    const initialCount = provider.getMessages().length;

    await provider.handleUserMessage("");
    assert.strictEqual(provider.getMessages().length, initialCount);

    await provider.handleUserMessage("   ");
    assert.strictEqual(provider.getMessages().length, initialCount);

    await provider.handleUserMessage("\n\t  ");
    assert.strictEqual(provider.getMessages().length, initialCount);
  });

  // --------------------------------------------------------------------------
  // 3. Chat Honest Guidance
  // --------------------------------------------------------------------------
  test.it("Chat Provider: Returns genuine diagnostics without fake AI reasoning", async () => {
    const client = new MockGuardianClient();
    client.changes = [
      { id: "c1", dependency_id: "dep1", change_type: "field_rename", severity: "high", status: "detected" },
    ];
    const provider = new GuardianChatViewProvider(mockVscode.Uri.file("/ext"), client);

    await provider.handleUserMessage("status");
    const msgs = provider.getMessages();
    const assistantMsg = msgs[msgs.length - 1];

    assert.strictEqual(assistantMsg.role, "assistant");
    assert.match(assistantMsg.content, /Workspace Health Diagnostics/i);
    assert.match(assistantMsg.content, /Online/i);

    await provider.handleUserMessage("tell me a joke");
    const generalReply = provider.getMessages()[provider.getMessages().length - 1];
    assert.match(generalReply.content, /does not fabricate AI reasoning/i);
  });

  // --------------------------------------------------------------------------
  // 4. Main Guardian Dashboard Panel Creation & Theme
  // --------------------------------------------------------------------------
  test.it("Dashboard Panel: Creates Webview Panel with restrained theme & CSP", () => {
    const client = new MockGuardianClient();
    GuardianDashboardPanel.createOrShow(mockVscode.Uri.file("/ext"), client);

    assert.ok(GuardianDashboardPanel.currentPanel, "GuardianDashboardPanel must be instantiated");
    const html = GuardianDashboardPanel.currentPanel._panel.webview.html;

    // Strict Security CSP
    assert.match(html, /Content-Security-Policy/i);
    assert.match(html, /default-src 'none'/i);

    // Restrained Theme: Uses VS Code variables
    assert.match(html, /var\(--vscode-editor-background/);
    assert.match(html, /var\(--vscode-sideBar-background/);
    assert.match(html, /var\(--vscode-input-background/);
    assert.match(html, /var\(--vscode-widget-border/);
    assert.match(html, /var\(--vscode-button-background/);

    // No glowing box-shadows or neon candy gradients
    assert.doesNotMatch(html, /box-shadow:\s*0\s*0\s*\d+px/i);

    // Key Dashboard Elements
    assert.match(html, /id="statusBadge"/);
    assert.match(html, /id="offlineNotice"/);
    assert.match(html, /id="metricServices"/);
    assert.match(html, /id="metricChanges"/);
    assert.match(html, /id="metricBreaking"/);
    assert.match(html, /id="metricRepairs"/);
    assert.match(html, /id="metricApproved"/);
    assert.match(html, /id="incidentsList"/);
    assert.match(html, /id="detailsContainer"/);

    // Primary Actions
    assert.match(html, /onclick="runDetection\(\)"/);
    assert.match(html, /onclick="triggerScan\(\)"/);
    assert.match(html, /onclick="createBaseline\(\)"/);
    assert.match(html, /onclick="refreshDashboard\(\)"/);

    GuardianDashboardPanel.currentPanel.dispose();
  });

  // --------------------------------------------------------------------------
  // 5. Package Manifest Layout Structure
  // --------------------------------------------------------------------------
  test.it("Manifest (package.json): Correctly configures layout with no redundant sidebar dashboard", () => {
    const pkgPath = path.resolve(__dirname, "..", "package.json");
    const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));

    const sidebarViews = pkg.contributes.views["dependency-guardian-sidebar"];
    assert.ok(Array.isArray(sidebarViews));

    // Confirm no redundant dashboard in sidebar
    const redundantDash = sidebarViews.find((v) => v.id === "dependencyGuardian.dashboardView");
    assert.strictEqual(redundantDash, undefined, "Redundant dashboardView must not be in sidebar");

    // Confirm secondary views sit in sidebar
    const chatView = sidebarViews.find((v) => v.id === "dependencyGuardian.chatView");
    assert.ok(chatView, "chatView must be in sidebar");

    const changesView = sidebarViews.find((v) => v.id === "dependencyGuardian.changes");
    assert.ok(changesView, "changesView must be in sidebar");

    const repairsView = sidebarViews.find((v) => v.id === "dependencyGuardian.repairs");
    assert.ok(repairsView, "repairsView must be in sidebar");

    // Confirm primary openDashboard command
    const commands = pkg.contributes.commands.map((c) => c.command);
    assert.ok(commands.includes("dependencyGuardian.openDashboard"));
    assert.ok(commands.includes("dependencyGuardian.openChat"));
    assert.ok(commands.includes("dependencyGuardian.runDetection"));
    assert.ok(commands.includes("dependencyGuardian.reviewRepair"));
    assert.ok(commands.includes("dependencyGuardian.approveRepair"));
    assert.ok(commands.includes("dependencyGuardian.applyRepair"));

    // Activation events
    assert.ok(pkg.activationEvents.includes("onView:dependencyGuardian.chatView"));
    assert.ok(pkg.activationEvents.includes("onView:dependencyGuardian.changes"));
  });
});
