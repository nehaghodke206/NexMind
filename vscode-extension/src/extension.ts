import * as vscode from "vscode";
import { GuardianClient } from "./api/guardianClient";
import { ServicesTreeProvider } from "./views/servicesTree";
import { ChangesTreeProvider } from "./views/changesTree";
import { WorkflowsTreeProvider } from "./views/workflowsTree";
import { RepairsTreeProvider } from "./views/repairsTree";
import { GuardianDashboardPanel } from "./webview/guardianPanel";
import { GuardianStatusBar } from "./statusBar";

export function activate(context: vscode.ExtensionContext) {
  const workspaceRoot =
    vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0
      ? vscode.workspace.workspaceFolders[0].uri.fsPath
      : process.cwd();

  const client = new GuardianClient("http://127.0.0.1:8765");
  const statusBar = new GuardianStatusBar();

  // Tree Providers
  const servicesTree = new ServicesTreeProvider(client);
  const changesTree = new ChangesTreeProvider(client);
  const workflowsTree = new WorkflowsTreeProvider(client, workspaceRoot);
  const repairsTree = new RepairsTreeProvider(client);

  vscode.window.registerTreeDataProvider("dependencyGuardian.services", servicesTree);
  vscode.window.registerTreeDataProvider("dependencyGuardian.changes", changesTree);
  vscode.window.registerTreeDataProvider("dependencyGuardian.workflows", workflowsTree);
  vscode.window.registerTreeDataProvider("dependencyGuardian.repairs", repairsTree);

  // Command: Open Dashboard
  const openDashboardCmd = vscode.commands.registerCommand(
    "dependencyGuardian.openDashboard",
    (changeId?: string) => {
      GuardianDashboardPanel.createOrShow(context.extensionUri, client, changeId);
    }
  );

  // Command: Initialize Project
  const initCmd = vscode.commands.registerCommand("dependencyGuardian.initialize", async () => {
    try {
      const res = await client.initializeProject();
      vscode.window.showInformationMessage(
        `Dependency Guardian initialized: ${res.dependencies_count} dependencies configured.`
      );
      servicesTree.refresh();
    } catch (err: any) {
      vscode.window.showErrorMessage(`Initialization failed: ${err.message}`);
    }
  });

  // Command: Create Baseline
  const createBaselineCmd = vscode.commands.registerCommand(
    "dependencyGuardian.createBaseline",
    async () => {
      try {
        await client.createBaseline();
        vscode.window.showInformationMessage("Known-good baselines captured and versioned.");
        statusBar.setHealthy();
        servicesTree.refresh();
      } catch (err: any) {
        vscode.window.showErrorMessage(`Baseline creation failed: ${err.message}`);
      }
    }
  );

  // Command: Scan Dependencies
  const scanCmd = vscode.commands.registerCommand(
    "dependencyGuardian.scanDependencies",
    async () => {
      try {
        statusBar.setScanning();
        const scan = await client.runScan();
        changesTree.refresh(scan.changes);

        if (scan.changes_detected > 0) {
          statusBar.setIssues(scan.changes_detected);
          // Auto-load impact for first change
          const firstChange = scan.changes[0];
          const impacts = await client.getChangeImpact(firstChange.id);
          workflowsTree.setImpacts(impacts);

          vscode.window.showWarningMessage(
            `Dependency Guardian: Detected ${scan.changes_detected} dependency change(s)!`
          );
        } else {
          statusBar.setHealthy();
          workflowsTree.setImpacts([]);
          vscode.window.showInformationMessage(
            "Dependency Guardian: Scan complete. All external dependencies match baseline contracts."
          );
        }
      } catch (err: any) {
        statusBar.setOffline();
        vscode.window.showErrorMessage(`Scan failed: ${err.message}`);
      }
    }
  );

  // Command: Reset Demo
  const resetCmd = vscode.commands.registerCommand("dependencyGuardian.resetDemo", async () => {
    try {
      await client.resetDemo();
      statusBar.setHealthy();
      servicesTree.refresh();
      changesTree.refresh([]);
      workflowsTree.setImpacts([]);
      repairsTree.refresh();
      vscode.window.showInformationMessage("Demo reset: All services restored to clean baseline v1.");
    } catch (err: any) {
      vscode.window.showErrorMessage(`Reset failed: ${err.message}`);
    }
  });

  context.subscriptions.push(
    statusBar,
    openDashboardCmd,
    initCmd,
    createBaselineCmd,
    scanCmd,
    resetCmd
  );

  // Initial check in background
  client
    .getHealth()
    .then(() => statusBar.setHealthy())
    .catch(() => statusBar.setOffline());
}

export function deactivate() {}
