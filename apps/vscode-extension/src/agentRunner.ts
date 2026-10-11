import * as cp from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import { DetectionResult, DetectionRunOptions } from './types';

export class DetectionAgentRunner {
  private outputChannel: vscode.OutputChannel;
  private extensionUri: vscode.Uri;

  constructor(context: vscode.ExtensionContext, outputChannel: vscode.OutputChannel) {
    this.extensionUri = context.extensionUri;
    this.outputChannel = outputChannel;
  }

  /**
   * Resolve executable path with the defined precedence:
   * 1. Explicit setting: dependencyGuardian.agentPath
   * 2. Bundled standalone binary inside extension bin/ directory
   * 3. System command: dependency-guardian in PATH
   * 4. Python module fallback: python -m dependency_guardian.cli
   */
  public resolveAgentCommand(): { command: string; argsPrefix: string[]; isPythonFallback: boolean } {
    const config = vscode.workspace.getConfiguration('dependencyGuardian');
    const customAgentPath = config.get<string>('agentPath', '').trim();

    if (customAgentPath && fs.existsSync(customAgentPath)) {
      return { command: customAgentPath, argsPrefix: [], isPythonFallback: false };
    }

    // Check bundled binary inside extension/bin/
    const isWindows = process.platform === 'win32';
    const binaryName = isWindows ? 'dependency-guardian.exe' : 'dependency-guardian';
    const bundledPath = path.join(this.extensionUri.fsPath, 'bin', binaryName);

    if (fs.existsSync(bundledPath)) {
      return { command: bundledPath, argsPrefix: [], isPythonFallback: false };
    }

    // Python fallback
    const pythonCmd = config.get<string>('pythonPath', 'python').trim() || 'python';
    return {
      command: pythonCmd,
      argsPrefix: ['-m', 'dependency_guardian.cli'],
      isPythonFallback: true,
    };
  }

  /**
   * Execute detection agent asynchronously with cancellation and timeout support.
   */
  public async executeDetection(options: DetectionRunOptions): Promise<DetectionResult> {
    const config = vscode.workspace.getConfiguration('dependencyGuardian');
    const activeMode = options.mode || config.get<string>('detectionMode', 'algorithmic');
    const activeProvider = options.provider || config.get<string>('aiProvider', 'mock');
    const backendUrl = options.backendUrl || config.get<string>('backendUrl', 'http://127.0.0.1:8000/api/v1');

    const agentResolution = this.resolveAgentCommand();
    const args: string[] = [...agentResolution.argsPrefix];

    args.push('--baseline', options.baselinePath);
    args.push('--current', options.currentPath);
    args.push('--mode', activeMode);
    args.push('--format', 'json');

    if (activeMode !== 'algorithmic') {
      args.push('--provider', activeProvider);
    }

    if (options.backendUrl || backendUrl) {
      args.push('--backend-url', backendUrl);
    }
    if (options.projectId) {
      args.push('--project-id', options.projectId);
    }
    if (options.dependencyId) {
      args.push('--dependency-id', options.dependencyId);
    }

    // Log command safely (redact any sensitive keys)
    const safeCommandStr = `${agentResolution.command} ${args.join(' ')}`;
    this.outputChannel.appendLine(`[AgentRunner] Executing: ${safeCommandStr}`);

    return new Promise<DetectionResult>((resolve, reject) => {
      const timeoutMs = (options.timeoutSeconds || 45) * 1000;
      let isSettled = false;

      const child = cp.spawn(agentResolution.command, args, {
        cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd(),
        shell: false,
      });

      let stdout = '';
      let stderr = '';

      const timer = setTimeout(() => {
        if (!isSettled) {
          isSettled = true;
          child.kill('SIGTERM');
          this.outputChannel.appendLine(`[AgentRunner] Process timed out after ${timeoutMs}ms.`);
          reject(new Error(`Detection agent execution timed out after ${options.timeoutSeconds || 45} seconds.`));
        }
      }, timeoutMs);

      if (options.cancellationToken) {
        options.cancellationToken.onCancellationRequested(() => {
          if (!isSettled) {
            isSettled = true;
            clearTimeout(timer);
            child.kill('SIGTERM');
            this.outputChannel.appendLine('[AgentRunner] Process cancelled by user.');
            reject(new Error('Detection agent execution was cancelled by the user.'));
          }
        });
      }

      child.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      child.stderr.on('data', (data) => {
        stderr += data.toString();
        this.outputChannel.append(`[Agent Stderr] ${data.toString()}`);
      });

      child.on('error', (err) => {
        if (!isSettled) {
          isSettled = true;
          clearTimeout(timer);
          this.outputChannel.appendLine(`[AgentRunner] Spawn error: ${err.message}`);
          reject(new Error(`Failed to launch detection agent (${agentResolution.command}): ${err.message}`));
        }
      });

      child.on('close', (code) => {
        if (!isSettled) {
          isSettled = true;
          clearTimeout(timer);

          if (!stdout.trim()) {
            this.outputChannel.appendLine(`[AgentRunner] Agent returned no stdout output. Exit code: ${code}. Stderr: ${stderr}`);
            return reject(new Error(`Detection agent exited with code ${code} and produced no output. Details: ${stderr}`));
          }

          try {
            // Find JSON start if logs preceded it
            const jsonStartIndex = stdout.indexOf('{');
            if (jsonStartIndex === -1) {
              throw new Error(`Output does not contain valid JSON: ${stdout}`);
            }
            const jsonStr = stdout.slice(jsonStartIndex);
            const parsed = JSON.parse(jsonStr) as DetectionResult;
            resolve(parsed);
          } catch (parseErr) {
            this.outputChannel.appendLine(`[AgentRunner] JSON parse failure: ${parseErr}. Raw stdout: ${stdout}`);
            reject(new Error(`Failed to parse detection agent JSON response: ${parseErr}`));
          }
        }
      });
    });
  }
}

