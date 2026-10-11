import * as http from 'http';
import * as https from 'https';
import * as vscode from 'vscode';
import { DetectionAgentRunner } from './agentRunner';
import { DetectionMode, DetectionResult } from './types';

let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
  const outputChannel = vscode.window.createOutputChannel('Dependency Guardian');
  context.subscriptions.push(outputChannel);

  const runner = new DetectionAgentRunner(context, outputChannel);

  // Status Bar Item
  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.command = 'dependencyGuardian.changeDetectionMode';
  context.subscriptions.push(statusBarItem);
  updateStatusBar();
  statusBarItem.show();

  // Listen to configuration changes to keep status bar synchronized
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('dependencyGuardian.detectionMode')) {
        updateStatusBar();
      }
    })
  );

  // Command 1: Change Detection Mode
  context.subscriptions.push(
    vscode.commands.registerCommand('dependencyGuardian.changeDetectionMode', async () => {
      const config = vscode.workspace.getConfiguration('dependencyGuardian');
      const currentMode = config.get<string>('detectionMode', 'algorithmic');

      const items: (vscode.QuickPickItem & { mode: DetectionMode })[] = [
        {
          label: '$(shield) Algorithmic',
          description: '(Default, Safe)',
          detail: 'Deterministic offline detection. Evaluates schemas without external API or AI dependencies.',
          mode: 'algorithmic',
          picked: currentMode === 'algorithmic',
        },
        {
          label: '$(sparkle) Hybrid',
          description: '(Recommended for deep triage)',
          detail: 'Combines authoritative deterministic findings with AI reasoning enrichment.',
          mode: 'hybrid',
          picked: currentMode === 'hybrid',
        },
        {
          label: '$(symbol-event) AI',
          description: '(Provider-assisted)',
          detail: 'AI-based semantic analysis through configured provider (mock, ollama, or hosted).',
          mode: 'ai',
          picked: currentMode === 'ai',
        },
      ];

      const selected = await vscode.window.showQuickPick(items, {
        placeHolder: `Select active detection mode (Current: ${currentMode})`,
        title: 'Dependency Guardian: Change Detection Mode',
      });

      if (!selected) {
        return;
      }

      if (selected.mode === 'ai' || selected.mode === 'hybrid') {
        const configuredProvider = config.get<string>('aiProvider', 'mock');
        vscode.window.showInformationMessage(
          `Switched to ${selected.mode} mode. Provider configured: '${configuredProvider}'. ` +
          `Ensure the provider is running or configure credentials in settings.`
        );
      }

      // Persist across reloads globally
      await config.update('detectionMode', selected.mode, vscode.ConfigurationTarget.Global);
      updateStatusBar();
      vscode.window.showInformationMessage(`Dependency Guardian mode set to '${selected.mode}'.`);
    })
  );

  // Command 2: Run Specification Detection
  context.subscriptions.push(
    vscode.commands.registerCommand('dependencyGuardian.runDetection', async () => {
      // 1. Pick baseline specification file
      const baselineUri = await vscode.window.showOpenDialog({
        canSelectFiles: true,
        canSelectFolders: false,
        canSelectMany: false,
        openLabel: 'Select Baseline OpenAPI Spec',
        filters: { 'OpenAPI Specifications': ['json', 'yaml', 'yml'] },
      });
      if (!baselineUri || baselineUri.length === 0) {
        return;
      }

      // 2. Pick current specification file
      const currentUri = await vscode.window.showOpenDialog({
        canSelectFiles: true,
        canSelectFolders: false,
        canSelectMany: false,
        openLabel: 'Select Current OpenAPI Spec',
        filters: { 'OpenAPI Specifications': ['json', 'yaml', 'yml'] },
      });
      if (!currentUri || currentUri.length === 0) {
        return;
      }

      const baselinePath = baselineUri[0].fsPath;
      const currentPath = currentUri[0].fsPath;

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: 'Dependency Guardian: Running Detection...',
          cancellable: true,
        },
        async (progress, token) => {
          progress.report({ increment: 10, message: 'Launching agent...' });

          try {
            const result: DetectionResult = await runner.executeDetection({
              baselinePath,
              currentPath,
              cancellationToken: token,
            });

            progress.report({ increment: 90, message: 'Processing findings...' });
            displayDetectionResult(result, outputChannel);
          } catch (err: unknown) {
            const errMsg = err instanceof Error ? err.message : String(err);
            vscode.window.showErrorMessage(`Detection failed: ${errMsg}`);
            outputChannel.appendLine(`[Error] Detection failed: ${errMsg}`);
          }
        }
      );
    })
  );

  // Command 3: Check Backend Connection
  context.subscriptions.push(
    vscode.commands.registerCommand('dependencyGuardian.checkBackendHealth', async () => {
      const config = vscode.workspace.getConfiguration('dependencyGuardian');
      const rawUrl = config.get<string>('backendUrl', 'http://127.0.0.1:8000/api/v1');
      const healthUrl = rawUrl.replace('/api/v1', '') + '/health';

      try {
        const isOk = await pingUrl(healthUrl);
        if (isOk) {
          vscode.window.showInformationMessage(`Dependency Guardian Backend is ONLINE at ${healthUrl}.`);
        } else {
          vscode.window.showWarningMessage(`Backend is not reachable at ${healthUrl}. Offline mode remains functional.`);
        }
      } catch (err) {
        vscode.window.showWarningMessage(`Backend connection check failed: ${err}`);
      }
    })
  );

  outputChannel.appendLine('[Dependency Guardian] Extension activated successfully.');
}

function updateStatusBar() {
  if (!statusBarItem) {
    return;
  }
  const config = vscode.workspace.getConfiguration('dependencyGuardian');
  const mode = config.get<string>('detectionMode', 'algorithmic');

  let icon = '$(shield)';
  if (mode === 'hybrid') {
    icon = '$(sparkle)';
  } else if (mode === 'ai') {
    icon = '$(symbol-event)';
  }

  const capitalized = mode.charAt(0).toUpperCase() + mode.slice(1);
  statusBarItem.text = `${icon} DG: ${capitalized}`;
  statusBarItem.tooltip = `Dependency Guardian Detection Mode: ${capitalized}\nClick to change mode.`;
}

function displayDetectionResult(result: DetectionResult, channel: vscode.OutputChannel) {
  channel.clear();
  channel.appendLine('========================================================================');
  channel.appendLine(' Dependency Guardian Detection Results');
  channel.appendLine(` Mode: ${result.mode.toUpperCase()} | Execution Time: ${result.execution_time_ms}ms`);
  channel.appendLine('========================================================================');
  channel.appendLine(`Total Findings: ${result.summary.total_findings}`);
  channel.appendLine(`  - Breaking:             ${result.summary.breaking_count}`);
  channel.appendLine(`  - Potentially Breaking: ${result.summary.potentially_breaking_count}`);
  channel.appendLine(`  - Non-Breaking:         ${result.summary.non_breaking_count}`);
  channel.appendLine(`  - Unknown:              ${result.summary.unknown_count}`);

  if (result.findings.length > 0) {
    channel.appendLine('------------------------------------------------------------------------');
    for (const f of result.findings) {
      const methodStr = f.method || '*';
      channel.appendLine(`[${f.compatibility.toUpperCase()}] ${f.rule_id} -> ${methodStr} ${f.path}`);
      channel.appendLine(`  Location: ${f.schema_location}`);
      channel.appendLine(`  Message:  ${f.message}`);
      if (f.ai_reasoning) {
        channel.appendLine(`  AI Note:  ${f.ai_reasoning}`);
      }
    }
  }
  channel.appendLine('========================================================================');
  channel.show(true);

  if (result.summary.breaking_count > 0) {
    vscode.window.showWarningMessage(
      `Detected ${result.summary.breaking_count} breaking change(s) across specifications! Check Output channel for details.`,
      'View Findings'
    ).then((selection) => {
      if (selection === 'View Findings') {
        channel.show(true);
      }
    });
  } else {
    vscode.window.showInformationMessage(
      `Detection complete: ${result.summary.total_findings} finding(s), 0 breaking changes.`
    );
  }
}

function pingUrl(urlStr: string): Promise<boolean> {
  return new Promise((resolve) => {
    try {
      const url = new URL(urlStr);
      const client = url.protocol === 'https:' ? https : http;
      const req = client.get(urlStr, { timeout: 3000 }, (res) => {
        resolve(res.statusCode === 200);
      });
      req.on('error', () => resolve(false));
      req.on('timeout', () => {
        req.destroy();
        resolve(false);
      });
    } catch {
      resolve(false);
    }
  });
}

export function deactivate() {
  if (statusBarItem) {
    statusBarItem.dispose();
  }
}

