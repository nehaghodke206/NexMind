import * as vscode from "vscode";
import { GuardianClient, ChangeItem } from "../api/guardianClient";

export class ChangesTreeProvider implements vscode.TreeDataProvider<ChangeTreeItem> {
  private _onDidChangeTreeData: vscode.EventEmitter<ChangeTreeItem | undefined | null | void> =
    new vscode.EventEmitter<ChangeTreeItem | undefined | null | void>();
  readonly onDidChangeTreeData: vscode.Event<ChangeTreeItem | undefined | null | void> =
    this._onDidChangeTreeData.event;

  private latestChanges: ChangeItem[] = [];

  constructor(private client: GuardianClient) {}

  refresh(changes?: ChangeItem[]): void {
    if (changes) {
      this.latestChanges = changes;
    }
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: ChangeTreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(): Promise<ChangeTreeItem[]> {
    try {
      if (this.latestChanges.length === 0) {
        this.latestChanges = await this.client.getChanges();
      }

      if (this.latestChanges.length === 0) {
        return [
          new ChangeTreeItem(
            "No changes detected (Clean)",
            vscode.TreeItemCollapsibleState.None,
            "info"
          ),
        ];
      }

      return this.latestChanges.map(
        (c) =>
          new ChangeTreeItem(
            `${c.dependency_id}: ${c.change_type}`,
            vscode.TreeItemCollapsibleState.None,
            "change",
            c
          )
      );
    } catch {
      return [
        new ChangeTreeItem(
          "Run scan to detect changes",
          vscode.TreeItemCollapsibleState.None,
          "info"
        ),
      ];
    }
  }
}

export class ChangeTreeItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState,
    public readonly contextValue: string,
    public readonly change?: ChangeItem
  ) {
    super(label, collapsibleState);

    if (change) {
      if (change.severity === "blocked" || change.change_type === "semantic_uncertainty") {
        this.iconPath = new vscode.ThemeIcon("shield", new vscode.ThemeColor("charts.orange"));
        this.description = "[BLOCKED UNCERTAIN]";
      } else if (change.severity === "high") {
        this.iconPath = new vscode.ThemeIcon("error", new vscode.ThemeColor("charts.red"));
        this.description = "[HIGH RISK]";
      } else if (change.severity === "medium") {
        this.iconPath = new vscode.ThemeIcon("warning", new vscode.ThemeColor("charts.yellow"));
        this.description = "[MEDIUM]";
      } else {
        this.iconPath = new vscode.ThemeIcon("info", new vscode.ThemeColor("charts.blue"));
        this.description = "[LOW]";
      }

      this.command = {
        command: "dependencyGuardian.openDashboard",
        title: "Inspect in Guardian Dashboard",
        arguments: [change.id],
      };
    } else {
      this.iconPath = new vscode.ThemeIcon("check");
    }
  }
}
