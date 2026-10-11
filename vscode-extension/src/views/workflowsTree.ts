import * as vscode from "vscode";
import * as path from "path";
import { GuardianClient, ImpactItem } from "../api/guardianClient";

export class WorkflowsTreeProvider implements vscode.TreeDataProvider<WorkflowTreeItem> {
  private _onDidChangeTreeData: vscode.EventEmitter<WorkflowTreeItem | undefined | null | void> =
    new vscode.EventEmitter<WorkflowTreeItem | undefined | null | void>();
  readonly onDidChangeTreeData: vscode.Event<WorkflowTreeItem | undefined | null | void> =
    this._onDidChangeTreeData.event;

  private currentImpacts: ImpactItem[] = [];

  constructor(private client: GuardianClient, private workspaceRoot: string) {}

  setImpacts(impacts: ImpactItem[]) {
    this.currentImpacts = impacts;
    this._onDidChangeTreeData.fire();
  }

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: WorkflowTreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(element?: WorkflowTreeItem): Promise<WorkflowTreeItem[]> {
    if (!element) {
      if (this.currentImpacts.length === 0) {
        return [
          new WorkflowTreeItem(
            "No affected workflows identified",
            vscode.TreeItemCollapsibleState.None,
            "info"
          ),
        ];
      }

      return this.currentImpacts.map(
        (imp) =>
          new WorkflowTreeItem(
            imp.workflow_name,
            vscode.TreeItemCollapsibleState.Expanded,
            "workflow",
            imp
          )
      );
    } else if (element.contextValue === "workflow" && element.impact) {
      const items: WorkflowTreeItem[] = [];

      for (const src of element.impact.source_files) {
        const fullPath = path.isAbsolute(src) ? src : path.join(this.workspaceRoot, src);
        const item = new WorkflowTreeItem(
          `Source: ${path.basename(src)}`,
          vscode.TreeItemCollapsibleState.None,
          "file",
          element.impact,
          fullPath
        );
        item.command = {
          command: "vscode.open",
          title: "Open Source File",
          arguments: [vscode.Uri.file(fullPath)],
        };
        items.push(item);
      }

      for (const test of element.impact.tests) {
        const fullPath = path.isAbsolute(test) ? test : path.join(this.workspaceRoot, test);
        const item = new WorkflowTreeItem(
          `Test: ${path.basename(test)}`,
          vscode.TreeItemCollapsibleState.None,
          "test",
          element.impact,
          fullPath
        );
        item.command = {
          command: "vscode.open",
          title: "Open Test File",
          arguments: [vscode.Uri.file(fullPath)],
        };
        items.push(item);
      }

      return items;
    }
    return [];
  }
}

export class WorkflowTreeItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState,
    public readonly contextValue: string,
    public readonly impact?: ImpactItem,
    public readonly filePath?: string
  ) {
    super(label, collapsibleState);

    if (contextValue === "workflow") {
      this.iconPath = new vscode.ThemeIcon("circuit-board");
      this.description = `Fields: [${impact?.affected_fields.join(", ")}]`;
      this.tooltip = impact?.reason;
    } else if (contextValue === "file") {
      this.iconPath = new vscode.ThemeIcon("file-code");
      this.description = filePath ? path.relative(process.cwd(), filePath) : "";
    } else if (contextValue === "test") {
      this.iconPath = new vscode.ThemeIcon("beaker");
      this.description = filePath ? path.relative(process.cwd(), filePath) : "";
    } else {
      this.iconPath = new vscode.ThemeIcon("info");
    }
  }
}
