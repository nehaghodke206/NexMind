import * as vscode from "vscode";
import {
  GuardianClient,
  ChangeItem,
  ImpactItem,
  RepairProposal,
  ValidationResult,
} from "../api/guardianClient";

export class GuardianDashboardPanel {
  public static currentPanel: GuardianDashboardPanel | undefined;
  private readonly _panel: vscode.WebviewPanel;
  private readonly _extensionUri: vscode.Uri;
  private _disposables: vscode.Disposable[] = [];

  public static createOrShow(extensionUri: vscode.Uri, client: GuardianClient, changeId?: string) {
    const column = vscode.window.activeTextEditor
      ? vscode.window.activeTextEditor.viewColumn
      : undefined;

    if (GuardianDashboardPanel.currentPanel) {
      GuardianDashboardPanel.currentPanel._panel.reveal(column);
      if (changeId) {
        GuardianDashboardPanel.currentPanel.selectChange(changeId);
      }
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      "guardianDashboard",
      "Dependency Guardian Dashboard",
      column || vscode.ViewColumn.One,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
      }
    );

    GuardianDashboardPanel.currentPanel = new GuardianDashboardPanel(panel, extensionUri, client);
    if (changeId) {
      GuardianDashboardPanel.currentPanel.selectChange(changeId);
    }
  }

  private constructor(
    panel: vscode.WebviewPanel,
    extensionUri: vscode.Uri,
    private client: GuardianClient
  ) {
    this._panel = panel;
    this._extensionUri = extensionUri;

    this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

    this._panel.webview.onDidReceiveMessage(
      async (message) => {
        try {
          switch (message.command) {
            case "refresh":
              await this.loadInitialData();
              break;
            case "scan":
              await this.handleScan();
              break;
            case "createBaseline":
              await this.handleCreateBaseline();
              break;
            case "setScenario":
              await this.handleSetScenario(message.scenario);
              break;
            case "resetDemo":
              await this.handleResetDemo();
              break;
            case "selectChange":
              await this.loadChangeDetails(message.changeId);
              break;
            case "proposeRepair":
              await this.handleProposeRepair(message.changeId);
              break;
            case "validateRepair":
              await this.handleValidateRepair(message.repairId);
              break;
            case "applyRepair":
              await this.handleApplyRepair(message.repairId);
              break;
            case "rollbackRepair":
              await this.handleRollbackRepair(message.repairId);
              break;
          }
        } catch (err: any) {
          vscode.window.showErrorMessage(`Guardian Action Failed: ${err.message}`);
          this.sendMessage("actionError", { error: err.message });
        }
      },
      null,
      this._disposables
    );

    this._panel.webview.html = this._getHtmlForWebview();
    this.loadInitialData();
  }

  private sendMessage(type: string, payload: any) {
    this._panel.webview.postMessage({ type, ...payload });
  }

  public async selectChange(changeId: string) {
    await this.loadChangeDetails(changeId);
  }

  private async loadInitialData() {
    try {
      const health = await this.client.getHealth();
      const services = await this.client.getServices();
      const changes = await this.client.getChanges();
      this.sendMessage("initialData", { health, services, changes });
    } catch (err: any) {
      this.sendMessage("backendOffline", { error: err.message });
    }
  }

  private async handleScan() {
    vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: "Scanning external dependencies...",
        cancellable: false,
      },
      async () => {
        const result = await this.client.runScan();
        this.sendMessage("scanCompleted", { result });
        vscode.window.showInformationMessage(
          `Scan complete: Checked ${result.services_checked} services, found ${result.changes_detected} change(s).`
        );
      }
    );
  }

  private async handleCreateBaseline() {
    await this.client.createBaseline();
    vscode.window.showInformationMessage("Known-good baseline captured and versioned in SQLite.");
    await this.loadInitialData();
  }

  private async handleSetScenario(scenario: string) {
    await this.client.setScenario(scenario);
    vscode.window.showInformationMessage(`Simulator scenario updated: ${scenario}`);
    await this.handleScan();
  }

  private async handleResetDemo() {
    await this.client.resetDemo();
    vscode.window.showInformationMessage("Demo reset: all services restored to v1 baseline.");
    await this.loadInitialData();
  }

  private async loadChangeDetails(changeId: string) {
    const changes = await this.client.getChanges();
    const change = changes.find((c) => c.id === changeId);
    if (!change) return;

    const impacts = await this.client.getChangeImpact(changeId);
    this.sendMessage("changeSelected", { change, impacts });
  }

  private async handleProposeRepair(changeId: string) {
    const proposal = await this.client.createRepairProposal(changeId);
    this.sendMessage("repairProposed", { proposal });
  }

  private async handleValidateRepair(repairId: string) {
    vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: "Running contract & regression validation...",
        cancellable: false,
      },
      async () => {
        const result = await this.client.validateRepair(repairId);
        const repair = await this.client.getRepair(repairId);
        this.sendMessage("validationCompleted", { result, repair });
        if (result.status === "passed") {
          vscode.window.showInformationMessage("Validation Passed! Repair is ready for approval.");
        } else {
          vscode.window.showWarningMessage("Validation Failed! Review test output.");
        }
      }
    );
  }

  private async handleApplyRepair(repairId: string) {
    const result = await this.client.applyRepair(repairId);
    const repair = await this.client.getRepair(repairId);
    this.sendMessage("repairApplied", { result, repair });
    vscode.window.showInformationMessage("Repair applied! Dependent workflow restored.");
  }

  private async handleRollbackRepair(repairId: string) {
    const result = await this.client.rollbackRepair(repairId);
    const repair = await this.client.getRepair(repairId);
    this.sendMessage("repairRolledBack", { result, repair });
    vscode.window.showInformationMessage("Repair rolled back! Original code restored.");
  }

  public dispose() {
    GuardianDashboardPanel.currentPanel = undefined;
    this._panel.dispose();
    while (this._disposables.length) {
      const x = this._disposables.pop();
      if (x) x.dispose();
    }
  }

  private _getHtmlForWebview(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dependency Guardian Dashboard</title>
  <style>
    :root {
      --bg: #09090b;
      --card-bg: #111113;
      --card-border: #27272a;
      --card-hover: #18181b;
      --text: #f4f4f5;
      --text-muted: #71717a;
      --text-dim: #52525b;
      --accent: #ffffff;
      --success: #22c55e;
      --success-bg: rgba(34, 197, 94, 0.12);
      --success-border: rgba(34, 197, 94, 0.3);
      --warning: #eab308;
      --warning-bg: rgba(234, 179, 8, 0.12);
      --warning-border: rgba(234, 179, 8, 0.3);
      --danger: #ef4444;
      --danger-bg: rgba(239, 68, 68, 0.14);
      --danger-border: rgba(239, 68, 68, 0.35);
      --blocked: #c084fc;
      --blocked-bg: rgba(168, 85, 247, 0.14);
      --blocked-border: rgba(168, 85, 247, 0.35);
      --code-bg: #040406;
      --code-border: #27272a;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      padding: 24px;
      line-height: 1.5;
    }

    .container {
      max-width: 1320px;
      margin: 0 auto;
    }

    /* Header */
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 24px;
    }

    .logo-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .logo-icon {
      width: 36px;
      height: 36px;
      background: #18181b;
      border: 1px solid #3f3f46;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .logo-icon svg {
      width: 20px;
      height: 20px;
      stroke: #f4f4f5;
      fill: none;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    .title-group h1 {
      font-size: 19px;
      font-weight: 700;
      color: #ffffff;
      letter-spacing: -0.3px;
    }

    .title-group p {
      font-size: 13px;
      color: var(--text-muted);
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: var(--success-bg);
      border: 1px solid var(--success-border);
      color: #4ade80;
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
    }

    .status-badge.warning {
      background: var(--warning-bg);
      border-color: var(--warning-border);
      color: #fde047;
    }

    .status-badge.danger {
      background: var(--danger-bg);
      border-color: var(--danger-border);
      color: #f87171;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: currentColor;
    }

    /* Simulation Bar */
    .scenario-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }

    .scenario-title {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      color: var(--text-muted);
      margin-right: 6px;
    }

    .scenario-btn {
      background: #18181b;
      border: 1px solid var(--card-border);
      color: #e4e4e7;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .scenario-btn:hover {
      background: #27272a;
      border-color: #3f3f46;
      color: #ffffff;
    }

    .scenario-btn.reset {
      background: rgba(34, 197, 94, 0.08);
      border-color: rgba(34, 197, 94, 0.25);
      color: #4ade80;
    }

    .scenario-btn.reset:hover {
      background: rgba(34, 197, 94, 0.16);
      border-color: rgba(34, 197, 94, 0.4);
      color: #86efac;
    }

    /* Controls Bar */
    .controls-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 14px 20px;
      margin-bottom: 24px;
    }

    .btn-group {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }

    .btn {
      background: #18181b;
      color: #f4f4f5;
      border: 1px solid var(--card-border);
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }

    .btn:hover {
      background: #27272a;
      border-color: #3f3f46;
    }

    .btn.btn-primary {
      background: #ffffff;
      color: #09090b;
      border: 1px solid #ffffff;
    }

    .btn.btn-primary:hover {
      background: #e4e4e7;
      border-color: #e4e4e7;
    }

    .btn.btn-success {
      background: #16a34a;
      color: #ffffff;
      border: 1px solid #16a34a;
    }

    .btn.btn-success:hover {
      background: #15803d;
      border-color: #15803d;
    }

    .btn.btn-danger {
      background: rgba(239, 68, 68, 0.12);
      color: #f87171;
      border: 1px solid rgba(239, 68, 68, 0.3);
    }

    .btn.btn-danger:hover {
      background: rgba(239, 68, 68, 0.2);
      border-color: #f87171;
    }

    /* Grid Layout */
    .grid {
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 24px;
    }

    /* Left Card: Changes */
    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 20px;
    }

    .card-header {
      font-size: 13px;
      font-weight: 700;
      color: #e4e4e7;
      margin-bottom: 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      text-transform: uppercase;
      letter-spacing: 0.6px;
    }

    .change-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .change-item {
      background: #18181b;
      border: 1px solid var(--card-border);
      border-radius: 6px;
      padding: 12px 14px;
      cursor: pointer;
      transition: all 0.15s ease;
    }

    .change-item:hover {
      border-color: #3f3f46;
      background: #27272a;
    }

    .change-item.active {
      border-color: #52525b;
      background: #27272a;
      box-shadow: 0 0 0 1px #52525b;
    }

    .change-item-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;
    }

    .dep-name {
      font-weight: 600;
      font-size: 13px;
      color: #ffffff;
    }

    .severity-pill {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      padding: 2px 8px;
      border-radius: 4px;
      letter-spacing: 0.4px;
    }

    .severity-pill.high { background: var(--danger-bg); color: #f87171; border: 1px solid var(--danger-border); }
    .severity-pill.medium { background: var(--warning-bg); color: #fbbf24; border: 1px solid var(--warning-border); }
    .severity-pill.low { background: rgba(113, 113, 122, 0.2); color: #d4d4d8; border: 1px solid rgba(113, 113, 122, 0.4); }
    .severity-pill.blocked { background: var(--blocked-bg); color: #c084fc; border: 1px solid var(--blocked-border); }

    .change-desc {
      font-size: 12px;
      color: var(--text-muted);
      font-family: Consolas, monospace;
    }

    /* Right Details View */
    .details-view {
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .section-box {
      background: #16161a;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
    }

    .section-title {
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 12px;
      color: #e4e4e7;
      text-transform: uppercase;
      letter-spacing: 0.6px;
    }

    .evidence-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }

    .panel-header-badge {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }

    .panel-label {
      font-size: 12px;
      font-weight: 700;
      color: #e4e4e7;
    }

    .panel-pill {
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      padding: 2px 6px;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }

    .panel-pill.base {
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.35);
      color: #93c5fd;
    }

    .panel-pill.observed {
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.35);
      color: #fbbf24;
    }

    /* Code Viewer & Syntax Highlighting */
    .code-viewer {
      background: var(--code-bg);
      border: 1px solid var(--code-border);
      border-radius: 6px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      font-size: 12px;
      line-height: 1.7;
      overflow-x: auto;
      max-height: 240px;
      padding: 6px 0;
    }

    .json-line {
      display: flex;
      align-items: center;
      padding: 1px 12px;
      white-space: pre;
    }

    .json-line.removed-line {
      background: rgba(239, 68, 68, 0.16);
      border-left: 3px solid #ef4444;
      color: #fca5a5;
    }

    .json-line.added-line {
      background: rgba(34, 197, 94, 0.16);
      border-left: 3px solid #22c55e;
      color: #86efac;
    }

    .json-line.changed-line {
      background: rgba(168, 85, 247, 0.18);
      border-left: 3px solid #a855f7;
      color: #d8b4fe;
    }

    .diff-badge {
      font-size: 9px;
      font-weight: 800;
      letter-spacing: 0.5px;
      padding: 1px 5px;
      border-radius: 3px;
      margin-right: 8px;
      text-transform: uppercase;
      user-select: none;
    }

    .diff-badge.removed {
      background: #dc2626;
      color: #ffffff;
    }

    .diff-badge.added {
      background: #16a34a;
      color: #ffffff;
    }

    .diff-badge.changed {
      background: #9333ea;
      color: #ffffff;
    }

    .json-key {
      color: #93c5fd; /* Soft cyan/blue for keys */
      font-weight: 600;
    }

    .json-key.key-removed {
      color: #f87171; /* Highlight missing key in red */
      font-weight: 700;
    }

    .json-key.key-added {
      color: #4ade80; /* Highlight added key in green */
      font-weight: 700;
    }

    .json-key.key-changed {
      color: #c084fc; /* Highlight shifted key in purple */
      font-weight: 700;
    }

    .json-string {
      color: #fde047; /* Yellow/amber for string values */
    }

    .json-string.str-removed {
      color: #fca5a5;
    }

    .json-string.str-added {
      color: #86efac;
    }

    .json-string.str-changed {
      color: #e9d5ff;
      font-weight: 700;
    }

    .json-number {
      color: #fb923c; /* Orange for numbers */
    }

    .json-bool {
      color: #c084fc; /* Purple for booleans */
      font-weight: 600;
    }

    .json-null {
      color: #f87171;
    }

    .json-punct {
      color: #71717a; /* Muted zinc for punctuation */
    }

    /* Summary Diff Strip */
    .diff-summary-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
      padding-bottom: 12px;
      border-bottom: 1px solid #27272a;
    }

    .summary-pill {
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 4px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    .summary-pill.missing {
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.35);
      color: #f87171;
    }

    .summary-pill.added {
      background: rgba(34, 197, 94, 0.15);
      border: 1px solid rgba(34, 197, 94, 0.35);
      color: #4ade80;
    }

    .summary-pill.changed {
      background: rgba(168, 85, 247, 0.15);
      border: 1px solid rgba(168, 85, 247, 0.35);
      color: #c084fc;
    }

    .summary-pill.neutral {
      background: #18181b;
      border: 1px solid #27272a;
      color: #a1a1aa;
    }

    .diff-block {
      background: var(--code-bg);
      border: 1px solid var(--code-border);
      border-radius: 6px;
      padding: 14px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      font-size: 12px;
      line-height: 1.6;
      white-space: pre-wrap;
      max-height: 250px;
      overflow-y: auto;
      color: #f4f4f5;
    }

    .diff-add { color: #4ade80; background: rgba(34, 197, 94, 0.12); display: block; padding: 1px 6px; border-radius: 3px; }
    .diff-del { color: #f87171; background: rgba(239, 68, 68, 0.12); display: block; padding: 1px 6px; border-radius: 3px; }

    /* Policy Safety Alert */
    .safety-alert {
      background: var(--danger-bg);
      border: 1px solid var(--danger-border);
      border-left: 4px solid #ef4444;
      border-radius: 6px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .safety-alert.blocked {
      background: var(--blocked-bg);
      border-color: var(--blocked-border);
      border-left: 4px solid #a855f7;
    }

    .safety-alert-content h4 {
      font-size: 13px;
      font-weight: 700;
      color: #f87171;
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }

    .safety-alert.blocked .safety-alert-content h4 {
      color: #c084fc;
    }

    .safety-alert-content p {
      font-size: 12px;
      color: #d4d4d8;
      line-height: 1.5;
    }

    .workflow-tag {
      background: var(--code-bg);
      border: 1px solid var(--card-border);
      padding: 12px 14px;
      border-radius: 6px;
      margin-bottom: 8px;
      font-size: 12px;
    }

    .workflow-tag strong {
      color: #ffffff;
    }

    .empty-state {
      text-align: center;
      padding: 40px;
      color: var(--text-muted);
      font-size: 13px;
    }
  </style>
</head>
<body>
  <div class="container">
    <!-- Top Header -->
    <div class="header">
      <div class="logo-group">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            <path d="M9 12l2 2 4-4"/>
          </svg>
        </div>
        <div class="title-group">
          <h1>Dependency Guardian</h1>
          <p>Automated drift detection, impact analysis, and guided compatibility repair</p>
        </div>
      </div>
      <div id="statusBadge" class="status-badge">
        <div class="status-dot"></div>
        <span id="statusText">System Baseline Intact</span>
      </div>
    </div>

    <!-- Live Simulation Controls -->
    <div class="scenario-bar">
      <span class="scenario-title">Simulation Controls:</span>
      <button class="scenario-btn" onclick="setScenario('users_v2')">Users API: Field Rename (name -&gt; display_name)</button>
      <button class="scenario-btn" onclick="setScenario('search_v2')">Search API: Cursor Pagination Contract</button>
      <button class="scenario-btn" onclick="setScenario('payments_v2')">Payments API: Semantic Shift (Blocks Repair)</button>
      <button class="scenario-btn reset" onclick="resetDemo()">Reset All to Baseline v1</button>
    </div>

    <!-- Controls Bar -->
    <div class="controls-bar">
      <div class="btn-group">
        <button class="btn btn-primary" onclick="triggerScan()">Scan Dependencies</button>
        <button class="btn" onclick="createBaseline()">Capture Baseline</button>
      </div>
      <div class="btn-group">
        <button class="btn" onclick="refreshDashboard()">Refresh State</button>
      </div>
    </div>

    <!-- Main View Grid -->
    <div class="grid">
      <!-- Left Column: Detected Changes -->
      <div class="card">
        <div class="card-header">
          <span>Detected Changes</span>
          <span id="changesCount" style="font-size:12px; font-weight:normal; color:var(--text-muted);">0 found</span>
        </div>
        <div id="changesList" class="change-list">
          <div class="empty-state">No changes detected. Run a scan or select a simulation above.</div>
        </div>
      </div>

      <!-- Right Column: Inspector & Repair Studio -->
      <div class="card" id="detailsCard">
        <div class="empty-state" id="noSelectionMsg">
          Select a detected change on the left or run a scan to inspect findings.
        </div>
        <div id="activeDetails" class="details-view" style="display:none;">
          <!-- Content populated via JavaScript -->
        </div>
      </div>
    </div>
  </div>

  <script>
    const vscode = acquireVsCodeApi();
    let state = {
      services: [],
      changes: [],
      selectedChange: null,
      impacts: [],
      currentRepair: null,
      validation: null
    };

    function triggerScan() {
      vscode.postMessage({ command: 'scan' });
    }

    function createBaseline() {
      vscode.postMessage({ command: 'createBaseline' });
    }

    function setScenario(scenario) {
      vscode.postMessage({ command: 'setScenario', scenario });
    }

    function resetDemo() {
      vscode.postMessage({ command: 'resetDemo' });
    }

    function refreshDashboard() {
      vscode.postMessage({ command: 'refresh' });
    }

    function selectChange(changeId) {
      vscode.postMessage({ command: 'selectChange', changeId });
    }

    function proposeRepair(changeId) {
      vscode.postMessage({ command: 'proposeRepair', changeId });
    }

    function validateRepair(repairId) {
      vscode.postMessage({ command: 'validateRepair', repairId });
    }

    function applyRepair(repairId) {
      vscode.postMessage({ command: 'applyRepair', repairId });
    }

    function rollbackRepair(repairId) {
      vscode.postMessage({ command: 'rollbackRepair', repairId });
    }

    function escapeHtml(str) {
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    // JSON syntax highlighting and missing/added field diff renderer
    function formatHighlightedJson(data, highlights, mode) {
      if (!data || typeof data !== 'object') {
        return '<div class="json-line"><span class="json-string">' + escapeHtml(String(data)) + '</span></div>';
      }

      const removedKeys = new Set(highlights.removed || []);
      const addedKeys = new Set(highlights.added || []);
      const changedKeys = new Set(highlights.changed || []);

      const keys = Object.keys(data);
      let lines = [];
      lines.push('<div class="json-line"><span class="json-punct">{</span></div>');

      keys.forEach((k, idx) => {
        const val = data[k];
        const isLast = idx === keys.length - 1;
        const comma = isLast ? '' : '<span class="json-punct">,</span>';

        let lineClass = 'json-line';
        let keyClass = 'json-key';
        let badgeHtml = '';
        let valClass = '';

        if (mode === 'baseline') {
          if (removedKeys.has(k)) {
            lineClass += ' removed-line';
            keyClass += ' key-removed';
            valClass = 'str-removed';
            badgeHtml = '<span class="diff-badge removed">REMOVED</span>';
          } else if (changedKeys.has(k)) {
            lineClass += ' changed-line';
            keyClass += ' key-changed';
            valClass = 'str-changed';
            badgeHtml = '<span class="diff-badge changed">BASE EXPECTATION</span>';
          }
        } else if (mode === 'observed') {
          if (addedKeys.has(k)) {
            lineClass += ' added-line';
            keyClass += ' key-added';
            valClass = 'str-added';
            badgeHtml = '<span class="diff-badge added">ADDED</span>';
          } else if (changedKeys.has(k)) {
            lineClass += ' changed-line';
            keyClass += ' key-changed';
            valClass = 'str-changed';
            badgeHtml = '<span class="diff-badge changed">SHIFTED</span>';
          }
        }

        let valHtml = '';
        if (typeof val === 'string') {
          valHtml = '<span class="json-string ' + valClass + '">"' + escapeHtml(val) + '"</span>';
        } else if (typeof val === 'number') {
          valHtml = '<span class="json-number">' + val + '</span>';
        } else if (typeof val === 'boolean') {
          valHtml = '<span class="json-bool">' + val + '</span>';
        } else if (val === null) {
          valHtml = '<span class="json-null">null</span>';
        } else if (Array.isArray(val)) {
          valHtml = '<span class="json-punct">[</span>' + escapeHtml(JSON.stringify(val)) + '<span class="json-punct">]</span>';
        } else {
          valHtml = '<span class="json-punct">{</span>' + escapeHtml(JSON.stringify(val)) + '<span class="json-punct">}</span>';
        }

        lines.push(
          '<div class="' + lineClass + '">' +
            badgeHtml + '  <span class="' + keyClass + '">"' + escapeHtml(k) + '"</span><span class="json-punct">:</span> ' + valHtml + comma +
          '</div>'
        );
      });

      lines.push('<div class="json-line"><span class="json-punct">}</span></div>');
      return lines.join('');
    }

    window.addEventListener('message', event => {
      const msg = event.data;
      switch (msg.type) {
        case 'initialData':
          state.services = msg.services;
          state.changes = msg.changes;
          renderChangesList();
          break;
        case 'scanCompleted':
          state.changes = msg.result.changes;
          renderChangesList();
          if (state.changes.length > 0) {
            selectChange(state.changes[0].id);
          }
          break;
        case 'changeSelected':
          state.selectedChange = msg.change;
          state.impacts = msg.impacts;
          state.currentRepair = null;
          state.validation = null;
          renderDetails();
          break;
        case 'repairProposed':
          state.currentRepair = msg.proposal;
          renderDetails();
          break;
        case 'validationCompleted':
          state.validation = msg.result;
          state.currentRepair = msg.repair;
          renderDetails();
          break;
        case 'repairApplied':
        case 'repairRolledBack':
          state.currentRepair = msg.repair;
          renderDetails();
          break;
        case 'backendOffline':
          const badge = document.getElementById('statusBadge');
          badge.className = 'status-badge danger';
          document.getElementById('statusText').innerText = 'Backend Offline (127.0.0.1:8765)';
          break;
      }
    });

    function renderChangesList() {
      const listEl = document.getElementById('changesList');
      const countEl = document.getElementById('changesCount');
      const statusBadge = document.getElementById('statusBadge');
      const statusText = document.getElementById('statusText');

      countEl.innerText = state.changes.length + ' detected';

      if (state.changes.length === 0) {
        listEl.innerHTML = '<div class="empty-state">No changes detected. System matches known-good baselines.</div>';
        statusBadge.className = 'status-badge';
        statusText.innerText = 'System Baseline Intact';
        return;
      }

      statusBadge.className = 'status-badge warning';
      statusText.innerText = state.changes.length + ' Behavioral Drift(s) Detected';

      listEl.innerHTML = state.changes.map(c => {
        const isAct = state.selectedChange && state.selectedChange.id === c.id;
        const sevClass = c.severity === 'blocked' ? 'blocked' : (c.severity || 'high');
        return \`
          <div class="change-item \${isAct ? 'active' : ''}" onclick="selectChange('\${c.id}')">
            <div class="change-item-header">
              <span class="dep-name">\${c.dependency_id}</span>
              <span class="severity-pill \${sevClass}">\${c.severity}</span>
            </div>
            <div class="change-desc">\${c.change_type}</div>
          </div>
        \`;
      }).join('');
    }

    function renderDetails() {
      const c = state.selectedChange;
      if (!c) {
        document.getElementById('noSelectionMsg').style.display = 'block';
        document.getElementById('activeDetails').style.display = 'none';
        return;
      }

      document.getElementById('noSelectionMsg').style.display = 'none';
      const detailsEl = document.getElementById('activeDetails');
      detailsEl.style.display = 'flex';

      const isBlocked = c.change_type === 'semantic_uncertainty' || c.severity === 'blocked';

      // Build highlights map for diff coloring
      const highlights = {
        removed: [],
        added: [],
        changed: []
      };

      let diffSummaryPills = [];

      if (c.change_type === 'field_rename_candidate') {
        if (c.evidence.removed_field) highlights.removed.push(c.evidence.removed_field);
        if (c.evidence.added_field) highlights.added.push(c.evidence.added_field);
        diffSummaryPills.push('<span class="summary-pill missing">- Missing Field: ' + c.evidence.removed_field + '</span>');
        diffSummaryPills.push('<span class="summary-pill added">+ Added Field: ' + c.evidence.added_field + '</span>');
        diffSummaryPills.push('<span class="summary-pill changed">Candidate Mapping: Values Match ("' + c.evidence.observed_value + '")</span>');
      } else if (c.change_type === 'pagination_contract_change') {
        highlights.removed.push('items', 'page', 'next_page');
        highlights.added.push('results', 'next_cursor');
        diffSummaryPills.push('<span class="summary-pill missing">- Removed Keys: items, page, next_page</span>');
        diffSummaryPills.push('<span class="summary-pill added">+ Added Keys: results, next_cursor</span>');
        diffSummaryPills.push('<span class="summary-pill changed">Contract: Offset -&gt; Cursor Pagination</span>');
      } else if (c.change_type === 'semantic_uncertainty') {
        const fld = c.evidence.field || 'status';
        highlights.changed.push(fld);
        diffSummaryPills.push('<span class="summary-pill missing">Expected Status: "' + (c.evidence.expected_value || 'paid') + '"</span>');
        diffSummaryPills.push('<span class="summary-pill changed">Observed Status: "' + (c.evidence.observed_value || 'processing_escrow') + '"</span>');
        diffSummaryPills.push('<span class="summary-pill missing">Safety: Automatic Repair Prohibited</span>');
      } else if (c.change_type === 'field_removed') {
        if (c.evidence.removed_field) highlights.removed.push(c.evidence.removed_field);
        diffSummaryPills.push('<span class="summary-pill missing">- Missing Field: ' + c.evidence.removed_field + '</span>');
      } else if (c.change_type === 'field_added') {
        if (c.evidence.added_field) highlights.added.push(c.evidence.added_field);
        diffSummaryPills.push('<span class="summary-pill added">+ Added Field: ' + c.evidence.added_field + '</span>');
      } else if (c.change_type === 'type_mismatch') {
        if (c.evidence.field) highlights.changed.push(c.evidence.field);
        diffSummaryPills.push('<span class="summary-pill changed">Type Mismatch: ' + c.evidence.field + '</span>');
      }

      let html = \`
        <div style="display:flex; justify-content:space-between; align-items:center; padding-bottom:12px; border-bottom:1px solid #27272a;">
          <div>
            <h2 style="font-size:16px; font-weight:700; color:#ffffff;">\${c.dependency_id}: \${c.change_type}</h2>
            <p style="color:var(--text-muted); font-size:12px;">Probe: \${c.probe_id} | Identifier: \${c.id}</p>
          </div>
          <span class="severity-pill \${isBlocked ? 'blocked' : c.severity}">\${c.severity}</span>
        </div>
      \`;

      // Safety policy notice for semantic uncertainty
      if (isBlocked) {
        html += \`
          <div class="safety-alert blocked">
            <div class="safety-alert-content">
              <h4>Safety Restriction: Automatic Repair Prohibited</h4>
              <p>\${c.evidence.reason || 'Semantic equivalence cannot be established deterministically. Manual human review is required.'}</p>
            </div>
          </div>
        \`;
      }

      // Evidence Section with Syntax Highlighting and Diff Markers
      const baseData = c.evidence.baseline_sample || c.evidence.baseline_value || { status: 'paid' };
      const currData = c.evidence.current_sample || c.evidence.observed_value || { status: c.evidence.observed_value };

      const baseFormatted = formatHighlightedJson(baseData, highlights, 'baseline');
      const currFormatted = formatHighlightedJson(currData, highlights, 'observed');

      html += \`
        <div class="section-box">
          <div class="section-title">Observed Evidence vs Baseline</div>
          
          <div class="diff-summary-strip">
            \${diffSummaryPills.join('')}
          </div>

          <div class="evidence-grid">
            <div>
              <div class="panel-header-badge">
                <span class="panel-label">Baseline Response:</span>
                <span class="panel-pill base">Known-Good Contract</span>
              </div>
              <div class="code-viewer">\${baseFormatted}</div>
            </div>
            <div>
              <div class="panel-header-badge">
                <span class="panel-label">Observed Response:</span>
                <span class="panel-pill observed">Current Probe</span>
              </div>
              <div class="code-viewer">\${currFormatted}</div>
            </div>
          </div>
          \${c.evidence.limitation_note ? \`
            <p style="font-size:11px; color:#71717a; margin-top:8px; font-style:italic;">
              Limitation: \${c.evidence.limitation_note}
            </p>
          \` : ''}
        </div>
      \`;

      // Affected Workflows
      html += \`
        <div class="section-box">
          <div class="section-title">Configured Affected Workflows</div>
          \${state.impacts.length > 0 ? state.impacts.map(imp => \`
            <div class="workflow-tag">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <strong>\${imp.workflow_name}</strong>
                <span class="summary-pill missing" style="font-size:10px;">Missing field: \${imp.affected_fields.join(', ')}</span>
              </div>
              <div style="color:var(--text-muted); margin-bottom:6px;">\${imp.reason}</div>
              <div style="display:flex; gap:12px; font-size:11px; color:#a1a1aa; flex-wrap:wrap;">
                <div><span style="color:#71717a;">Source:</span> <code style="background:#27272a; padding:1px 5px; border-radius:3px; color:#e4e4e7;">\${imp.source_files.join(', ')}</code></div>
                <div><span style="color:#71717a;">Tests:</span> <code style="background:#27272a; padding:1px 5px; border-radius:3px; color:#e4e4e7;">\${imp.tests.join(', ')}</code></div>
              </div>
            </div>
          \`).join('') : '<p style="color:var(--text-muted); font-size:12px;">No workflows explicitly mapped.</p>'}
        </div>
      \`;

      // Repair Proposal Section
      html += \`
        <div class="section-box">
          <div class="section-title">Repair Studio &amp; Safety Verification</div>
      \`;

      if (isBlocked) {
        html += \`
          <p style="color:#c084fc; font-size:13px; font-weight:600;">
            Automatic repair generation is disabled for uncertain business semantics.
          </p>
        \`;
      } else if (!state.currentRepair) {
        html += \`
          <p style="color:var(--text-muted); font-size:13px; margin-bottom:12px;">
            A deterministic compatibility adapter can be generated for this change.
          </p>
          <button class="btn btn-primary" onclick="proposeRepair('\${c.id}')">Generate Repair Proposal</button>
        \`;
      } else {
        const rep = state.currentRepair;
        html += \`
          <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <span style="font-size:13px; font-weight:600; color:#ffffff;">Adapter Type: \${rep.repair_type}</span>
            <span style="font-size:12px; color:var(--text-muted);">Confidence: \${Math.round(rep.confidence * 100)}% | Target: \${rep.target_file}</span>
          </div>

          <p style="font-size:12px; font-weight:600; color:var(--text-muted); margin-bottom:6px;">Proposed Unified Diff:</p>
          <div class="diff-block">\${rep.diff ? rep.diff.split('\\n').map(line => {
            if (line.startsWith('+')) return '<span class="diff-add">' + escapeHtml(line) + '</span>';
            if (line.startsWith('-')) return '<span class="diff-del">' + escapeHtml(line) + '</span>';
            return ' ' + escapeHtml(line);
          }).join('\\n') : escapeHtml(rep.proposed_code_snippet)}</div>

          <div style="margin-top:10px; font-size:12px; color:var(--text-muted);">
            <strong>Assumptions:</strong> \${rep.assumptions.join(' ')}
          </div>
        \`;

        // Validation Results
        if (state.validation) {
          const val = state.validation;
          const isPassed = val.status === 'passed';
          html += \`
            <div style="margin-top:14px; padding:12px; border-radius:6px; background:\${isPassed ? 'var(--success-bg)' : 'var(--danger-bg)'}; border:1px solid \${isPassed ? 'var(--success-border)' : 'var(--danger-border)'};">
              <div style="font-weight:700; font-size:13px; color:\${isPassed ? '#4ade80' : '#f87171'};">
                \${isPassed ? 'Validation Passed' : 'Validation Failed'} (\${val.duration_ms}ms)
              </div>
              <pre class="diff-block" style="margin-top:8px; max-height:100px;">\${escapeHtml(val.output_summary)}</pre>
            </div>
          \`;
        }

        // Action Buttons
        html += \`
          <div style="display:flex; gap:10px; margin-top:16px;">
            <button class="btn" onclick="validateRepair('\${rep.id}')">Run Validation</button>
            <button class="btn btn-success" \${(rep.status !== 'validation_passed' && rep.status !== 'applied') ? 'disabled style="opacity:0.4; cursor:not-allowed;"' : ''} onclick="applyRepair('\${rep.id}')">
              \${rep.status === 'applied' ? 'Applied' : 'Apply Approved Repair'}
            </button>
            \${rep.status === 'applied' ? \`
              <button class="btn btn-danger" onclick="rollbackRepair('\${rep.id}')">Roll Back Repair</button>
            \` : ''}
          </div>
        \`;
      }

      html += '</div>';
      detailsEl.innerHTML = html;
    }
  </script>
</body>
</html>`;
  }
}
