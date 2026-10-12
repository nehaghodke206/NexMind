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

  setRepairs(repairs: RepairProposal[]) {
    this.latestRepairs = repairs;
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
      try {
        const changes = await this.client.getChanges();
        const allProposals: RepairProposal[] = [];
        for (const c of changes) {
          const props = await this.client.getRepairProposals(c.id);
          allProposals.push(...props);
        }
        if (allProposals.length > 0) {
          this.latestRepairs = allProposals;
        }
      } catch {
        // Ignore network errors
      }
    }

    if (this.latestRepairs.length === 0) {
      return [
        new RepairTreeItem(
          "No repair proposals yet",
          vscode.TreeItemCollapsibleState.None,
          "info"
        ),
      ];
    }

    return this.latestRepairs.map((r) => {
      let ctx = "repair";
      if (r.status === "approved") ctx = "repair-approved";
      else if (r.status === "applied") ctx = "repair-applied";
      else if (r.status === "validated" || r.status === "validation_passed") ctx = "repair-validated";

      return new RepairTreeItem(
        `${r.repair_type || "repair"}: ${r.target_file || r.id}`,
        vscode.TreeItemCollapsibleState.None,
        ctx,
        r
      );
    });
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
      const st = (repair.status || "").toLowerCase();
      if (st === "applied") {
        this.iconPath = new vscode.ThemeIcon("pass-filled", new vscode.ThemeColor("charts.green"));
        this.description = "[APPLIED]";
      } else if (st === "approved") {
        this.iconPath = new vscode.ThemeIcon("verified", new vscode.ThemeColor("charts.green"));
        this.description = "[APPROVED]";
      } else if (st === "validated" || st === "validation_passed") {
        this.iconPath = new vscode.ThemeIcon("check", new vscode.ThemeColor("charts.green"));
        this.description = "[VALIDATED]";
      } else if (st === "validation_failed" || st === "failed") {
        this.iconPath = new vscode.ThemeIcon("close", new vscode.ThemeColor("charts.red"));
        this.description = "[FAILED]";
      } else if (st === "needs_review" || st === "blocked_uncertain" || st === "blocked") {
        this.iconPath = new vscode.ThemeIcon("shield", new vscode.ThemeColor("charts.orange"));
        this.description = "[NEEDS REVIEW]";
      } else {
        this.iconPath = new vscode.ThemeIcon("tools", new vscode.ThemeColor("charts.blue"));
        this.description = `[${repair.status.toUpperCase()}]`;
      }

      this.tooltip = `Repair: ${repair.id}\nTarget: ${repair.target_file || "N/A"}\nStatus: ${repair.status}\nClick to review diff`;

      this.command = {
        command: "dependencyGuardian.reviewRepair",
        title: "Review Repair Diff",
        arguments: [repair],
      };
    } else {
      this.iconPath = new vscode.ThemeIcon("info");
    }
  }
}
