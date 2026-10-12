import * as vscode from "vscode";

export class GuardianStatusBar {
  private statusBarItem: vscode.StatusBarItem;

  constructor() {
    this.statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      100
    );
    this.statusBarItem.command = "dependencyGuardian.openDashboard";
    this.setHealthy();
    this.statusBarItem.show();
  }

  setHealthy() {
    this.statusBarItem.text = "$(shield) Guardian: Healthy";
    this.statusBarItem.tooltip = "All configured external dependencies match baselines.";
    this.statusBarItem.backgroundColor = undefined;
  }

  setScanning() {
    this.statusBarItem.text = "$(sync~spin) Guardian: Scanning...";
    this.statusBarItem.tooltip = "Probing external endpoints and comparing contracts...";
  }

  setIssues(count: number) {
    this.statusBarItem.text = `$(warning) Guardian: ${count} Issue${count > 1 ? "s" : ""}`;
    this.statusBarItem.tooltip = `${count} external dependency behavioral shift(s) detected. Click to review.`;
    this.statusBarItem.backgroundColor = new vscode.ThemeColor(
      "statusBarItem.warningBackground"
    );
  }

  setOffline(url?: string) {
    this.statusBarItem.text = "$(error) Guardian: Offline";
    this.statusBarItem.tooltip = `Dependency Guardian backend is not responding (${url || "offline"}).`;
    this.statusBarItem.backgroundColor = new vscode.ThemeColor(
      "statusBarItem.errorBackground"
    );
  }

  dispose() {
    this.statusBarItem.dispose();
  }
}
