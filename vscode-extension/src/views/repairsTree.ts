import * as vscode from "vscode";
import { GuardianClient, RepairProposal } from "../api/guardianClient";

export class RepairsTreeProvider implements vscode.TreeDataProvider<RepairTreeItem> {
  private _onDidChangeTreeData: vscode.EventEmitter<RepairTreeItem | undefined | null | void> =
    new vscode.EventEmitter<RepairTreeItem | undefined | null | void>();
  readonly onDidChangeTreeData: vscode.Event<RepairTreeItem | undefined | null | void> =
    this._onDidChangeTreeData.event;

  private latestRepairs: RepairProposal[] = [];

  constructor(private client: GuardianClient) {}

  addRepair(repair: RepairProposal) {
    const existingIdx = this.latestRepairs.findIndex((r) => r.id === repair.id);
    if (existingIdx >= 0) {
      this.latestRepairs[existingIdx] = repair;
    } else {
      this.latestRepairs.unshift(repair);
    }
    this._onDidChangeTreeData.fire();
  }

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: RepairTreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(): Promise<RepairTreeItem[]> {
    if (this.latestRepairs.length === 0) {
      return [
        new RepairTreeItem(
          "No repair proposals yet",
          vscode.TreeItemCollapsibleState.None,
          "info"
        ),
      ];
    }

    return this.latestRepairs.map(
      (r) =>
        new RepairTreeItem(
          `${r.repair_type} (${r.status})`,
          vscode.TreeItemCollapsibleState.None,
          "repair",
          r
        )
    );
  }
}

export class RepairTreeItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState,
    public readonly contextValue: string,
    public readonly repair?: RepairProposal
  ) {
    super(label, collapsibleState);

    if (repair) {
      if (repair.status === "blocked_uncertain") {
        this.iconPath = new vscode.ThemeIcon("lock", new vscode.ThemeColor("charts.orange"));
        this.description = "[BLOCKED]";
      } else if (repair.status === "applied") {
        this.iconPath = new vscode.ThemeIcon("pass", new vscode.ThemeColor("charts.green"));
        this.description = "[APPLIED]";
      } else if (repair.status === "validation_passed") {
        this.iconPath = new vscode.ThemeIcon("check", new vscode.ThemeColor("charts.green"));
        this.description = "[VALIDATED]";
      } else if (repair.status === "validation_failed") {
        this.iconPath = new vscode.ThemeIcon("close", new vscode.ThemeColor("charts.red"));
        this.description = "[FAILED]";
      } else {
        this.iconPath = new vscode.ThemeIcon("tools", new vscode.ThemeColor("charts.blue"));
        this.description = `[${repair.status}]`;
      }

      this.command = {
        command: "dependencyGuardian.openDashboard",
        title: "View Repair in Dashboard",
        arguments: [repair.change_id],
      };
    } else {
      this.iconPath = new vscode.ThemeIcon("info");
    }
  }
}
