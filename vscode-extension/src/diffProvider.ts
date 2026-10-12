import * as vscode from "vscode";

export class RepairContentProvider implements vscode.TextDocumentContentProvider {
  public static readonly scheme = "dependency-guardian-repair";
  private _onDidChange = new vscode.EventEmitter<vscode.Uri>();
  readonly onDidChange = this._onDidChange.event;

  private contents = new Map<string, string>();

  public setContent(uri: vscode.Uri, content: string): void {
    this.contents.set(uri.toString(), content);
    this._onDidChange.fire(uri);
  }

  public provideTextDocumentContent(uri: vscode.Uri): string {
    return this.contents.get(uri.toString()) || "";
  }
}
