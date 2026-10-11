import * as vscode from "vscode";
import { GuardianClient, DependencyService } from "../api/guardianClient";

export class ServicesTreeProvider implements vscode.TreeDataProvider<ServiceTreeItem> {
  private _onDidChangeTreeData: vscode.EventEmitter<ServiceTreeItem | undefined | null | void> =
    new vscode.EventEmitter<ServiceTreeItem | undefined | null | void>();
  readonly onDidChangeTreeData: vscode.Event<ServiceTreeItem | undefined | null | void> =
    this._onDidChangeTreeData.event;

  constructor(private client: GuardianClient) {}

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: ServiceTreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(element?: ServiceTreeItem): Promise<ServiceTreeItem[]> {
    if (!element) {
      try {
        const services = await this.client.getServices();
        return services.map(
          (s) =>
            new ServiceTreeItem(
              s.name,
              vscode.TreeItemCollapsibleState.Expanded,
              "service",
              s
            )
        );
      } catch (err) {
        return [
          new ServiceTreeItem(
            "Backend disconnected or loading...",
            vscode.TreeItemCollapsibleState.None,
            "error"
          ),
        ];
      }
    } else if (element.contextValue === "service" && element.service) {
      return element.service.probes.map(
        (p) =>
          new ServiceTreeItem(
            `${p.method} ${p.path}`,
            vscode.TreeItemCollapsibleState.None,
            "probe",
            undefined,
            p
          )
      );
    }
    return [];
  }
}

export class ServiceTreeItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState,
    public readonly contextValue: string,
    public readonly service?: DependencyService,
    public readonly probe?: any
  ) {
    super(label, collapsibleState);

    if (contextValue === "service") {
      this.iconPath = new vscode.ThemeIcon("server-process");
      this.description = service?.base_url;
    } else if (contextValue === "probe") {
      this.iconPath = new vscode.ThemeIcon("pulse");
      this.description = probe?.expected_contract ? `[${probe.expected_contract}]` : "";
    } else if (contextValue === "error") {
      this.iconPath = new vscode.ThemeIcon("warning");
    }
  }
}
