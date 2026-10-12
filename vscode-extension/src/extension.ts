import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import {
  GuardianClient,
  ChangeItem,
  RepairProposal,
} from "./api/guardianClient";
import { getGuardianConfig, updateDetectionMode } from "./config";
import { AgentRunner } from "./agents/agentRunner";
import { DetectionService } from "./agents/detectionService";
import { RepairContentProvider } from "./diffProvider";
import { ServicesTreeProvider } from "./views/servicesTree";
import { ChangesTreeProvider, ChangeTreeItem } from "./views/changesTree";
import { WorkflowsTreeProvider } from "./views/workflowsTree";
import { RepairsTreeProvider, RepairTreeItem } from "./views/repairsTree";
import { GuardianDashboardPanel } from "./webview/guardianPanel";
import { GuardianStatusBar } from "./statusBar";
import {
  patchIntegrityStore,
  extractChangeSet,
  validateWorkspacePath,
} from "./patchIntegrity";
import { GuardianChatViewProvider } from "./views/chatView";

/**
 * Safely resolves a relative or absolute file path against workspaceRoot.
 * Prevents path traversal vulnerabilities and symlink escapes.
 */
function resolveWorkspaceFile(workspaceRoot: string, filePath: string): string | null {
  if (!filePath) return null;
  const res = validateWorkspacePath(workspaceRoot, filePath);
  return res.ok && res.fullPath ? res.fullPath : null;
}

export function activate(context: vscode.ExtensionContext) {
  const workspaceRoot =
    vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0
      ? vscode.workspace.workspaceFolders[0].uri.fsPath
      : process.cwd();

  const outputChannel = vscode.window.createOutputChannel("Dependency Guardian");
  context.subscriptions.push(outputChannel);

  const initialConfig = getGuardianConfig();
  const client = new GuardianClient(initialConfig.backendUrl);
  const agentRunner = new AgentRunner(outputChannel);
  const detectionService = new DetectionService(agentRunner, client, workspaceRoot, outputChannel);
  const statusBar = new GuardianStatusBar();
  const diffProvider = new RepairContentProvider();

  context.subscriptions.push(
    detectionService.onDidChangeState((evt) => {
      if (evt.state === "running") {
        statusBar.setScanning();
      } else if (evt.state === "succeeded") {
        if (evt.driftResult) {
          const breaking = evt.driftResult.summary.breaking_count;
          if (breaking > 0) {
            statusBar.setIssues(breaking);
          } else {
            statusBar.setHealthy();
          }
        }
      }
    })
  );

  // Register virtual document diff provider
  context.subscriptions.push(
    vscode.workspace.registerTextDocumentContentProvider(
      RepairContentProvider.scheme,
      diffProvider
    )
  );

  // Tree Providers
  const servicesTree = new ServicesTreeProvider(client);
  const changesTree = new ChangesTreeProvider(client);
  const workflowsTree = new WorkflowsTreeProvider(client, workspaceRoot);
  const repairsTree = new RepairsTreeProvider(client);

  vscode.window.registerTreeDataProvider("dependencyGuardian.services", servicesTree);
  vscode.window.registerTreeDataProvider("dependencyGuardian.changes", changesTree);
  vscode.window.registerTreeDataProvider("dependencyGuardian.workflows", workflowsTree);
  vscode.window.registerTreeDataProvider("dependencyGuardian.repairs", repairsTree);

  // Webview View Provider for Guardian Assistant in Sidebar
  const chatViewProvider = new GuardianChatViewProvider(context.extensionUri, client, agentRunner);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      GuardianChatViewProvider.viewType,
      chatViewProvider
    )
  );

  async function checkBackendHealth() {
    try {
      await client.getHealth();
      statusBar.setHealthy();
      return true;
    } catch {
      statusBar.setOffline(client.getBaseUrl());
      return false;
    }
  }

  // Command: Refresh
  const refreshCmd = vscode.commands.registerCommand("dependencyGuardian.refresh", async () => {
    const cfg = getGuardianConfig();
    client.setBaseUrl(cfg.backendUrl);
    await checkBackendHealth();
    GuardianDashboardPanel.currentPanel?.refresh();
    servicesTree.refresh();
    changesTree.refresh();
    repairsTree.refresh();
    vscode.window.showInformationMessage("Dependency Guardian views refreshed.");
  });

  // Command: Open Guardian Assistant (Chat)
  const openChatCmd = vscode.commands.registerCommand(
    "dependencyGuardian.openChat",
    () => {
      vscode.commands.executeCommand("dependencyGuardian.chatView.focus");
    }
  );

  // Command: Setup & Environment Check
  const setupEnvCmd = vscode.commands.registerCommand(
    "dependencyGuardian.setupEnvironment",
    async () => {
      outputChannel.show(true);
      outputChannel.appendLine("[Environment Check] Testing Python environment and agent modules...");
      const result = await agentRunner.checkEnvironment(workspaceRoot);
      outputChannel.appendLine(result.message);

      if (result.ok) {
        vscode.window.showInformationMessage(
          `Dependency Guardian Environment Ready!\nPython: ${result.pythonVersion} (${result.pythonPath})`
        );
      } else {
        const action = await vscode.window.showErrorMessage(
          `Agent Environment Issue: ${result.message}`,
          "Configure Python Path",
          "Dismiss"
        );
        if (action === "Configure Python Path") {
          vscode.commands.executeCommand(
            "workbench.action.openSettings",
            "dependencyGuardian.pythonPath"
          );
        }
      }
    }
  );

  // Command: Open Dashboard
  const openDashboardCmd = vscode.commands.registerCommand(
    "dependencyGuardian.openDashboard",
    (changeId?: string) => {
      GuardianDashboardPanel.createOrShow(
        context.extensionUri,
        client,
        changeId,
        agentRunner,
        workspaceRoot,
        detectionService
      );
    }
  );

  // Command: Open API Dependency Graph
  const openDependencyGraphCmd = vscode.commands.registerCommand(
    "dependencyGuardian.openDependencyGraph",
    () => {
      GuardianDashboardPanel.createOrShow(
        context.extensionUri,
        client,
        undefined,
        agentRunner,
        workspaceRoot,
        detectionService
      );
      GuardianDashboardPanel.currentPanel?.showDependencyGraph();
    }
  );

  // Command: Initialize Project
  const initCmd = vscode.commands.registerCommand("dependencyGuardian.initialize", async () => {
    try {
      const res = await client.initializeProject();
      vscode.window.showInformationMessage(
        `Dependency Guardian initialized: ${res.dependencies_count || 1} dependency configured.`
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
        const inv = detectionService.getLastInventory();
        let contracts: Record<string, any> = {};
        const openapiCandidate = path.join(workspaceRoot, "reports", "repository-inventory", "openapi.enriched.json");
        const demoCandidate = path.join(workspaceRoot, "demo", "sample-api", "contracts", "openapi-v1.json");
        if (fs.existsSync(openapiCandidate)) {
          try { contracts = JSON.parse(fs.readFileSync(openapiCandidate, "utf-8")); } catch {}
        } else if (fs.existsSync(demoCandidate)) {
          try { contracts = JSON.parse(fs.readFileSync(demoCandidate, "utf-8")); } catch {}
        }

        const baseline = await client.createBaseline(undefined, {
          version_tag: `v${Date.now()}`,
          description: "Baseline snapshot captured from VS Code Extension",
          inventory: inv ? { endpoints: inv.endpoints || [], discovered_endpoints: inv.endpoints?.length || 0 } : {},
          contracts,
        });
        vscode.window.showInformationMessage(
          `Known-good baseline ${baseline.version_tag || 'v' + (baseline.version_number || baseline.version || 1)} captured and versioned.`
        );
        statusBar.setHealthy();
        servicesTree.refresh();
        if (GuardianDashboardPanel.currentPanel) {
          await GuardianDashboardPanel.currentPanel.refresh();
        }
      } catch (err: any) {
        vscode.window.showErrorMessage(`Baseline creation failed: ${err.message}`);
      }
    }
  );

  // Command: Run Contract Drift Detection
  const runDetectionCmd = vscode.commands.registerCommand(
    "dependencyGuardian.runDetection",
    async () => {
      try {
        // Look for sample/demo contracts in workspace
        const demoV1 = path.join(workspaceRoot, "demo", "sample-api", "contracts", "openapi-v1.json");
        const demoV2 = path.join(workspaceRoot, "demo", "sample-api", "contracts", "openapi-v2.json");
        const hasDemo = fs.existsSync(demoV1) && fs.existsSync(demoV2);

        interface ContractChoice extends vscode.QuickPickItem {
          type: "demo" | "pick" | "custom";
        }

        const choices: ContractChoice[] = [];
        if (hasDemo) {
          choices.push({
            label: "$(beaker) Run with Sample API Contracts (v1 -> v2)",
            description: "demo/sample-api/contracts/openapi-v1.json -> openapi-v2.json",
            type: "demo",
          });
        }
        choices.push({
          label: "$(file-code) Select OpenAPI Contract Files...",
          description: "Choose baseline and current specification files from disk",
          type: "pick",
        });
        choices.push({
          label: "$(settings) Specify File Paths Manually...",
          description: "Enter paths to baseline and current OpenAPI specifications",
          type: "custom",
        });

        const selectedOption = await vscode.window.showQuickPick(choices, {
          placeHolder: "Select OpenAPI specifications for Contract Drift Detection",
        });
        if (!selectedOption) return;

        let baselinePath = "";
        let currentPath = "";

        if (selectedOption.type === "demo") {
          baselinePath = demoV1;
          currentPath = demoV2;
        } else if (selectedOption.type === "pick") {
          const baseUri = await vscode.window.showOpenDialog({
            canSelectFiles: true,
            canSelectFolders: false,
            canSelectMany: false,
            openLabel: "Select Baseline OpenAPI Spec",
            filters: { "OpenAPI Specifications": ["json", "yaml", "yml"] },
          });
          if (!baseUri || baseUri.length === 0) return;
          baselinePath = baseUri[0].fsPath;

          const currUri = await vscode.window.showOpenDialog({
            canSelectFiles: true,
            canSelectFolders: false,
            canSelectMany: false,
            openLabel: "Select Current OpenAPI Spec",
            filters: { "OpenAPI Specifications": ["json", "yaml", "yml"] },
          });
          if (!currUri || currUri.length === 0) return;
          currentPath = currUri[0].fsPath;
        } else {
          const b = await vscode.window.showInputBox({
            prompt: "Enter path to baseline OpenAPI specification",
            placeHolder: "e.g. contracts/openapi-v1.json",
          });
          if (!b) return;
          baselinePath = path.isAbsolute(b) ? b : path.resolve(workspaceRoot, b);

          const c = await vscode.window.showInputBox({
            prompt: "Enter path to current OpenAPI specification",
            placeHolder: "e.g. contracts/openapi-v2.json",
          });
          if (!c) return;
          currentPath = path.isAbsolute(c) ? c : path.resolve(workspaceRoot, c);
        }

        outputChannel.show(true);
        outputChannel.appendLine(`\n=== Running Contract Drift Detection ===`);
        outputChannel.appendLine(`Baseline: ${baselinePath}`);
        outputChannel.appendLine(`Current:  ${currentPath}`);

        statusBar.setScanning();

        await vscode.window.withProgress(
          {
            location: vscode.ProgressLocation.Notification,
            title: "Dependency Guardian: Running Contract Drift Detection...",
            cancellable: true,
          },
          async (progress, token) => {
            progress.report({ message: "Comparing OpenAPI specifications and syncing backend..." });
            const driftResult = await detectionService.detectContractDrift({
              baselinePath,
              currentPath,
              syncBackend: true,
              cancellationToken: token,
            });

            const mappedChanges = detectionService.mapFindingsToChanges(driftResult.findings);
            changesTree.refresh(mappedChanges);
            GuardianDashboardPanel.currentPanel?.updateDriftResult(driftResult, mappedChanges);
            GuardianDashboardPanel.currentPanel?.refresh();

            const total = driftResult.summary.total_findings;
            const breaking = driftResult.summary.breaking_count;

            outputChannel.appendLine(
              `[Detection Result] Total Findings: ${total}, Breaking Changes: ${breaking}`
            );

            if (breaking > 0) {
              const action = await vscode.window.showWarningMessage(
                `Detection complete: ${breaking} breaking change(s) detected! (${total} total findings)`,
                "Open Dashboard",
                "Generate Repairs"
              );
              if (action === "Open Dashboard") {
                vscode.commands.executeCommand("dependencyGuardian.openDashboard");
              } else if (action === "Generate Repairs") {
                vscode.commands.executeCommand("dependencyGuardian.proposeRepair");
              }
            } else {
              vscode.window.showInformationMessage(
                `Detection complete: Contracts are compatible. (${total} total findings)`
              );
            }
          }
        );
      } catch (err: any) {
        statusBar.setOffline(client.getBaseUrl());
        outputChannel.appendLine(`[Detection Error] ${err.message}`);
        vscode.window.showErrorMessage(`Detection failed: ${err.message}`);
      }
    }
  );

  // Command: Scan Codebase / Dependencies
  const runCodebaseScanHandler = async () => {
    try {
      const demoApiDir = path.join(workspaceRoot, "demo", "sample-api");
      const hasDemoApi = fs.existsSync(demoApiDir);

      interface ScanChoice extends vscode.QuickPickItem {
        type: "workspace" | "demo" | "pick";
      }

      const choices: ScanChoice[] = [
        {
          label: "$(root-folder) Current Workspace Root",
          description: workspaceRoot,
          type: "workspace",
        },
      ];

      if (hasDemoApi) {
        choices.push({
          label: "$(beaker) Sample API Demo Directory",
          description: "demo/sample-api",
          type: "demo",
        });
      }

      choices.push({
        label: "$(folder-opened) Select Subdirectory to Scan...",
        description: "Choose a specific project or service folder",
        type: "pick",
      });

      const selectedOption = await vscode.window.showQuickPick(choices, {
        placeHolder: "Select target directory for Repository Intelligence scan",
      });
      if (!selectedOption) return;

      let targetDir = workspaceRoot;
      if (selectedOption.type === "demo") {
        targetDir = demoApiDir;
      } else if (selectedOption.type === "pick") {
        const picked = await vscode.window.showOpenDialog({
          canSelectFiles: false,
          canSelectFolders: true,
          canSelectMany: false,
          openLabel: "Select Directory to Scan",
        });
        if (!picked || picked.length === 0) return;
        targetDir = picked[0].fsPath;
      }

      outputChannel.show(true);
      outputChannel.appendLine(`\n=== Running Repository Intelligence Scan ===`);
      outputChannel.appendLine(`Target Path: ${targetDir}`);

      statusBar.setScanning();

      await vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: "Dependency Guardian: Scanning Codebase & Repository Inventory...",
          cancellable: true,
        },
        async (progress, token) => {
          token.onCancellationRequested(() => {
            detectionService.cancelCodebaseScan();
          });
          progress.report({ message: "Discovering routes, dependencies, and spec discrepancies..." });
          const inventory = await detectionService.scanCodebase(targetDir, {
            cancellationToken: token,
            onProgress: (prog) => {
              let label = prog.message;
              if (prog.filesProcessed && prog.totalFiles) {
                label = `[${prog.filesProcessed}/${prog.totalFiles}] ${prog.message}`;
              }
              if (prog.quietWarning) {
                label = `(Active AST analysis...) ${prog.message}`;
              }
              progress.report({ message: label });
            },
          });

          GuardianDashboardPanel.currentPanel?.updateCodebaseInventory(inventory);
          GuardianDashboardPanel.currentPanel?.refresh();

          const epCount = inventory.endpoints.length;
          const depCount = inventory.dependencies.length;
          const integCount = inventory.integrations.length;
          const discCount = inventory.discrepancies.length;
          const cov = inventory.test_coverage.coverage_percentage;

          outputChannel.appendLine(
            `[Scan Result] Endpoints: ${epCount}, Dependencies: ${depCount}, Integrations: ${integCount}, Discrepancies: ${discCount}, Test Coverage: ${cov}%`
          );

          statusBar.setHealthy();

          let msg = `Repository Intelligence scan complete: ${epCount} server endpoint(s), ${depCount} dependencies, ${cov}% test coverage.`;
          if (epCount === 0 && integCount > 0) {
            msg = `Repository scan complete: Client application (${integCount} service integrations, ${depCount} dependencies; 0 server endpoints declared).`;
          }

          const action = await vscode.window.showInformationMessage(msg, "Open Dashboard");
          if (action === "Open Dashboard") {
            vscode.commands.executeCommand("dependencyGuardian.openDashboard");
          }
        }
      );
    } catch (err: any) {
      outputChannel.appendLine(`[Scan Error] ${err.message}`);
      if (err.message?.includes("cancelled")) {
        vscode.window.showInformationMessage("Codebase scan canceled.");
      } else {
        vscode.window.showErrorMessage(`Codebase scan failed: ${err.message}`);
      }
    }
  };

  const scanCmd = vscode.commands.registerCommand(
    "dependencyGuardian.scanDependencies",
    runCodebaseScanHandler
  );

  const scanCodebaseCmd = vscode.commands.registerCommand(
    "dependencyGuardian.scanCodebase",
    runCodebaseScanHandler
  );

  const cancelCodebaseScanCmd = vscode.commands.registerCommand(
    "dependencyGuardian.cancelCodebaseScan",
    () => {
      const canceled = detectionService.cancelCodebaseScan();
      if (canceled) {
        vscode.window.showInformationMessage("Codebase scan cancellation requested.");
      } else {
        vscode.window.showInformationMessage("No codebase scan is currently active.");
      }
    }
  );

  // Command: Open Affected File
  const openAffectedFileCmd = vscode.commands.registerCommand(
    "dependencyGuardian.openAffectedFile",
    async (arg?: ChangeTreeItem | ChangeItem) => {
      let change: ChangeItem | undefined;
      if (arg instanceof ChangeTreeItem) {
        change = arg.change;
      } else if (arg && typeof arg === "object" && "id" in arg) {
        change = arg as ChangeItem;
      }

      if (!change) {
        vscode.window.showWarningMessage("No finding or change selected.");
        return;
      }

      const affectedFiles = change.affected_files || [];
      if (affectedFiles.length === 0) {
        vscode.window.showInformationMessage(
          `Finding '${change.id}' has no specific source file mapping. Contract drift applies to external dependency '${change.dependency_id}'.`
        );
        return;
      }

      let targetFile = affectedFiles[0];
      if (affectedFiles.length > 1) {
        const picked = await vscode.window.showQuickPick(affectedFiles, {
          placeHolder: "Select affected source file to open",
        });
        if (!picked) return;
        targetFile = picked;
      }

      const fullPath = resolveWorkspaceFile(workspaceRoot, targetFile);
      if (!fullPath || !fs.existsSync(fullPath)) {
        vscode.window.showWarningMessage(
          `Affected source file '${targetFile}' was not found in the current workspace.`
        );
        return;
      }

      const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(fullPath));
      await vscode.window.showTextDocument(doc);
    }
  );

  // Command: Propose Repair
  const proposeRepairCmd = vscode.commands.registerCommand(
    "dependencyGuardian.proposeRepair",
    async (arg?: ChangeTreeItem | ChangeItem | string) => {
      try {
        let incidentId = "";
        let targetFile: string | undefined;

        if (typeof arg === "string") {
          incidentId = arg;
        } else if (arg instanceof ChangeTreeItem && arg.change) {
          incidentId = arg.change.id;
          if (arg.change.affected_files && arg.change.affected_files.length > 0) {
            targetFile = arg.change.affected_files[0];
          }
        } else if (arg && typeof arg === "object" && "id" in arg) {
          const item = arg as ChangeItem;
          incidentId = item.id;
          if (item.affected_files && item.affected_files.length > 0) {
            targetFile = item.affected_files[0];
          }
        }

        // If no incident specified, prompt with available detected changes
        if (!incidentId) {
          const changes = await client.getChanges();
          if (changes.length === 0) {
            vscode.window.showInformationMessage("No detected incidents found to repair. Run detection first.");
            return;
          }
          const picked = await vscode.window.showQuickPick(
            changes.map((c) => ({
              label: `$(alert) ${c.dependency_id}: ${c.change_type}`,
              description: `Incident ID: ${c.id.slice(0, 8)} [${c.severity.toUpperCase()}]`,
              change: c,
            })),
            { placeHolder: "Select an incident to generate a backwards-compatible repair" }
          );
          if (!picked) return;
          incidentId = picked.change.id;
          if (picked.change.affected_files && picked.change.affected_files.length > 0) {
            targetFile = picked.change.affected_files[0];
          }
        }

        outputChannel.show(true);
        outputChannel.appendLine(`\n=== Running Repair Agent ===`);
        outputChannel.appendLine(`Incident ID: ${incidentId}`);
        if (targetFile) outputChannel.appendLine(`Target File: ${targetFile}`);

        await vscode.window.withProgress(
          {
            location: vscode.ProgressLocation.Notification,
            title: `Dependency Guardian: Generating repair for incident ${incidentId.slice(0, 8)}...`,
            cancellable: true,
          },
          async (progress, token) => {
            progress.report({ message: "Executing patch generator & AST sandbox validation..." });
            const repairResult = await agentRunner.runRepair(workspaceRoot, {
              incidentId,
              targetFile,
              syncBackend: true,
              cancellationToken: token,
            });

            outputChannel.appendLine(
              `[Repair Agent Output] Status: ${repairResult.status || "proposed"}, Strategy: ${
                repairResult.strategy || "N/A"
              }`
            );

            repairsTree.refresh();
            GuardianDashboardPanel.currentPanel?.refresh();

            const action = await vscode.window.showInformationMessage(
              `Repair proposal created for incident '${incidentId.slice(0, 8)}' (Status: ${
                repairResult.status || "proposed"
              }).`,
              "Review Diff",
              "Open Dashboard"
            );

            if (action === "Review Diff") {
              vscode.commands.executeCommand(
                "dependencyGuardian.reviewRepair",
                repairResult.repair_id || incidentId
              );
            } else if (action === "Open Dashboard") {
              vscode.commands.executeCommand("dependencyGuardian.openDashboard", incidentId);
            }
          }
        );
      } catch (err: any) {
        outputChannel.appendLine(`[Repair Error] ${err.message}`);
        vscode.window.showErrorMessage(`Repair generation failed: ${err.message}`);
      }
    }
  );

  // Command: Review Repair Diff
  const reviewRepairCmd = vscode.commands.registerCommand(
    "dependencyGuardian.reviewRepair",
    async (arg?: RepairTreeItem | RepairProposal | string) => {
      try {
        let proposal: RepairProposal | undefined;

        if (arg instanceof RepairTreeItem) {
          proposal = arg.repair;
        } else if (arg && typeof arg === "object" && "id" in arg) {
          proposal = arg as RepairProposal;
        } else if (typeof arg === "string") {
          try {
            proposal = await client.getRepair(arg);
          } catch {
            const props = await client.getRepairProposals(arg);
            if (props && props.length > 0) {
              proposal = props[0];
            }
          }
        }

        // If not provided, prompt user to select from available repairs
        if (!proposal) {
          const changes = await client.getChanges();
          const allProposals: RepairProposal[] = [];
          for (const c of changes) {
            const props = await client.getRepairProposals(c.id);
            allProposals.push(...props);
          }
          if (allProposals.length === 0) {
            vscode.window.showInformationMessage("No repair proposals available to review.");
            return;
          }
          const picked = await vscode.window.showQuickPick(
            allProposals.map((p) => ({
              label: `$(tools) ${p.repair_type}: ${p.target_file || p.id}`,
              description: `Status: [${p.status.toUpperCase()}] Confidence: ${Math.round(p.confidence * 100)}%`,
              proposal: p,
            })),
            { placeHolder: "Select a repair proposal to review diff" }
          );
          if (!picked) return;
          proposal = picked.proposal;
        }

        // Step 1: Extract changes and pre-validate all file paths against traversal / symlink escapes
        const changes = extractChangeSet(proposal, workspaceRoot);
        if (changes.length === 0) {
          if (proposal.diff) {
            const virtualUri = vscode.Uri.parse(
              `${RepairContentProvider.scheme}:/patch-${proposal.id.slice(0, 8)}.diff?repairId=${proposal.id}`
            );
            diffProvider.setContent(virtualUri, proposal.diff);
            const doc = await vscode.workspace.openTextDocument(virtualUri);
            await vscode.window.showTextDocument(doc);
            patchIntegrityStore.recordReview(proposal, workspaceRoot);
          } else {
            vscode.window.showInformationMessage(
              `Repair proposal '${proposal.id.slice(0, 8)}' has no diff content. Strategy: ${
                proposal.repair_type
              }, Status: ${proposal.status}`
            );
          }
          return;
        }

        for (const change of changes) {
          const pathCheck = validateWorkspacePath(workspaceRoot, change.relativePath);
          if (!pathCheck.ok) {
            vscode.window.showErrorMessage(`Cannot review repair: ${pathCheck.reason}`);
            return;
          }
        }

        let targetChange = changes[0];
        if (changes.length > 1) {
          const picked = await vscode.window.showQuickPick(
            changes.map((c) => ({
              label: `$(file-code) ${c.relativePath}`,
              description: `Target file in change set`,
              change: c,
            })),
            { placeHolder: `Proposal modifies ${changes.length} files. Select a file to view diff` }
          );
          if (picked) {
            targetChange = picked.change;
          }
        }

        const fullTargetPath = path.resolve(workspaceRoot, targetChange.relativePath);
        if (fs.existsSync(fullTargetPath) && targetChange.proposedContent) {
          const originalUri = vscode.Uri.file(fullTargetPath);
          const virtualUri = vscode.Uri.parse(
            `${RepairContentProvider.scheme}:/${path.basename(fullTargetPath)}?repairId=${proposal.id}&file=${encodeURIComponent(targetChange.relativePath)}`
          );
          diffProvider.setContent(virtualUri, targetChange.proposedContent);

          const title = `Repair Diff: ${path.basename(fullTargetPath)} [${proposal.id.slice(0, 8)}]`;
          await vscode.commands.executeCommand("vscode.diff", originalUri, virtualUri, title);
        } else if (proposal.diff) {
          const virtualUri = vscode.Uri.parse(
            `${RepairContentProvider.scheme}:/patch-${proposal.id.slice(0, 8)}.diff?repairId=${proposal.id}`
          );
          diffProvider.setContent(virtualUri, proposal.diff);
          const doc = await vscode.workspace.openTextDocument(virtualUri);
          await vscode.window.showTextDocument(doc);
        }

        // Record explicit successful diff review ONLY after diff display succeeds
        const reviewRecord = patchIntegrityStore.recordReview(proposal, workspaceRoot);
        outputChannel.appendLine(
          `[Patch Integrity] Proposal ${proposal.id} diff reviewed. Canonical patch hash: ${reviewRecord.patchHash} (${reviewRecord.fileChanges.length} file(s))`
        );
      } catch (err: any) {
        vscode.window.showErrorMessage(`Reviewing repair failed: ${err.message}`);
      }
    }
  );

  // Command: Approve Repair
  const approveRepairCmd = vscode.commands.registerCommand(
    "dependencyGuardian.approveRepair",
    async (arg?: RepairTreeItem | RepairProposal | string) => {
      try {
        let proposal: RepairProposal | undefined;
        if (arg instanceof RepairTreeItem && arg.repair) {
          proposal = arg.repair;
        } else if (arg && typeof arg === "object" && "id" in arg) {
          proposal = arg as RepairProposal;
        } else if (typeof arg === "string") {
          proposal = await client.getRepair(arg);
        }

        if (!proposal) {
          vscode.window.showWarningMessage("No repair proposal selected to approve.");
          return;
        }

        // Requirement 1: Require an explicit successful diff-review action before approval.
        // Remove the implicit recordReview() fallback from the approval command.
        const record = patchIntegrityStore.getRecord(proposal.id);
        if (!record || !record.isDiffReviewed) {
          const reviewAction = "Review Diff First";
          const res = await vscode.window.showErrorMessage(
            `Cannot approve repair: You must perform an explicit diff review of proposal '${proposal.id.slice(0, 8)}' before approving it.`,
            reviewAction
          );
          if (res === reviewAction) {
            vscode.commands.executeCommand("dependencyGuardian.reviewRepair", proposal);
          }
          return;
        }

        const patchHash = record.patchHash;
        const fileCount = record.fileChanges.length;

        const confirm = await vscode.window.showInformationMessage(
          `Explicit Human Approval: Approve repair proposal '${proposal.id.slice(0, 8)}'?\n` +
          `Verified Patch Hash: ${patchHash.slice(0, 12)}... (${fileCount} file(s))\n` +
          `Approving binds your approval strictly to this immutable patch content.`,
          "Approve",
          "Review Diff First",
          "Cancel"
        );

        if (confirm === "Review Diff First") {
          vscode.commands.executeCommand("dependencyGuardian.reviewRepair", proposal);
          return;
        }
        if (confirm !== "Approve") return;

        // Requirement 5: Handle backend approval failure so the UI cannot misleadingly imply that approval succeeded.
        try {
          if (proposal.status !== "approved") {
            await client.approveRepair(
              proposal.id,
              "vscode-developer",
              `Approved patch hash: ${patchHash}`
            );
          }

          // Only record approval locally after backend confirms success
          const approvedHash = patchIntegrityStore.recordApproval(proposal.id);

          outputChannel.appendLine(
            `[Patch Approval] Proposal ${proposal.id} approved with bound patch hash ${approvedHash}`
          );

          vscode.window.showInformationMessage(
            `Repair proposal '${proposal.id.slice(0, 8)}' approved [Bound to Patch Hash: ${approvedHash.slice(0, 8)}]. Ready for safe application.`
          );
          repairsTree.refresh();
          GuardianDashboardPanel.currentPanel?.refresh();
        } catch (backendErr: any) {
          patchIntegrityStore.revokeApproval(proposal.id);
          outputChannel.appendLine(
            `[Patch Approval Failed] Backend rejected approval for proposal ${proposal.id}: ${backendErr.message}`
          );
          vscode.window.showErrorMessage(
            `Failed to approve repair proposal on backend: ${backendErr.message}. Proposal remains unapproved.`
          );
          repairsTree.refresh();
          GuardianDashboardPanel.currentPanel?.refresh();
        }
      } catch (err: any) {
        vscode.window.showErrorMessage(`Failed to approve repair: ${err.message}`);
      }
    }
  );

  // Command: Reject Repair
  const rejectRepairCmd = vscode.commands.registerCommand(
    "dependencyGuardian.rejectRepair",
    async (arg?: RepairTreeItem | RepairProposal | string, reasonInput?: string) => {
      try {
        let proposal: RepairProposal | undefined;
        if (arg instanceof RepairTreeItem && arg.repair) {
          proposal = arg.repair;
        } else if (arg && typeof arg === "object" && "id" in arg) {
          proposal = arg as RepairProposal;
        } else if (typeof arg === "string") {
          proposal = await client.getRepair(arg);
        }

        if (!proposal) {
          vscode.window.showWarningMessage("No repair proposal selected to reject.");
          return;
        }

        let reason = reasonInput;
        if (!reason) {
          reason = await vscode.window.showInputBox({
            prompt: `Enter reason for rejecting repair proposal '${proposal.id.slice(0, 8)}'`,
            value: "Rejected by developer during diff review.",
          });
        }
        if (!reason) return;

        await client.rejectRepair(proposal.id, "vscode-developer", reason);
        patchIntegrityStore.revokeApproval(proposal.id);

        vscode.window.showInformationMessage(
          `Repair proposal '${proposal.id.slice(0, 8)}' rejected on backend.`
        );
        repairsTree.refresh();
        GuardianDashboardPanel.currentPanel?.refresh();
      } catch (err: any) {
        vscode.window.showErrorMessage(`Failed to reject repair: ${err.message}`);
      }
    }
  );

  // Command: Apply Repair (Safe Human-Confirmed Application with Patch Integrity)
  const applyRepairCmd = vscode.commands.registerCommand(
    "dependencyGuardian.applyRepair",
    async (arg?: RepairTreeItem | RepairProposal | string) => {
      try {
        let proposal: RepairProposal | undefined;
        if (arg instanceof RepairTreeItem && arg.repair) {
          proposal = arg.repair;
        } else if (arg && typeof arg === "object" && "id" in arg) {
          proposal = arg as RepairProposal;
        } else if (typeof arg === "string") {
          proposal = await client.getRepair(arg);
        }

        if (!proposal) {
          vscode.window.showWarningMessage("No repair proposal selected to apply.");
          return;
        }

        // Requirement 5: Require the appropriate backend status before applying a repair.
        let liveProposal: RepairProposal;
        try {
          liveProposal = await client.getRepair(proposal.id);
        } catch (fetchErr: any) {
          vscode.window.showErrorMessage(
            `Cannot verify repair proposal with backend: ${fetchErr.message}. Live backend status check is mandatory before applying.`
          );
          return;
        }

        // Strict Requirement: Never auto-approve or auto-apply!
        if (liveProposal.status !== "approved") {
          vscode.window.showErrorMessage(
            `Cannot apply repair: Repair proposal '${liveProposal.id.slice(0, 8)}' status on backend is '${liveProposal.status}'. ` +
            `Repair proposal must be in 'approved' status on the backend before changes can be applied.`
          );
          return;
        }

        // Strict Requirement: Reject stale proposals if source file changed on disk
        const staleness = patchIntegrityStore.checkProposalStaleness(liveProposal, workspaceRoot);
        if (staleness.isStale) {
          vscode.window.showErrorMessage(`Cannot apply repair: ${staleness.reason}`);
          return;
        }

        // Ensure review and local approval binding for approved proposal
        let record = patchIntegrityStore.getRecord(liveProposal.id);
        if (!record || !record.isDiffReviewed) {
          record = patchIntegrityStore.recordReview(liveProposal, workspaceRoot);
        }
        if (liveProposal.status === "approved" && !record.approvedPatchHash) {
          patchIntegrityStore.recordApproval(liveProposal.id);
        }

        // Strict Requirement: Cryptographic patch integrity and conflict verification
        const verification = patchIntegrityStore.verifyBeforeApplication(liveProposal, workspaceRoot);
        if (!verification.ok) {
          vscode.window.showErrorMessage(
            `Repair application aborted: ${verification.reason}`
          );
          return;
        }

        const changes = verification.changes!;
        const approvedHash = verification.approvedHash!;
        const fileList = changes.map((c) => c.relativePath).join(", ");

        // Strict Requirement: Explicit modal confirmation listing all affected files and approved hash
        const confirm = await vscode.window.showWarningMessage(
          `Apply approved repair to workspace?\n` +
          `Target Files (${changes.length}): ${fileList}\n` +
          `Verified Patch Hash: ${approvedHash.slice(0, 12)}...\n\n` +
          `This will modify the specified local files in your workspace.`,
          { modal: true },
          "Apply Changes",
          "Cancel"
        );
        if (confirm !== "Apply Changes") {
          return;
        }

        // Requirements 3 & 4: Safe multi-file atomic write with immediate pre-write revalidation and robust rollback
        let appliedFiles: string[] = [];
        try {
          appliedFiles = patchIntegrityStore.applyApprovedChangesSafely(changes, workspaceRoot, liveProposal.id);
        } catch (applyErr: any) {
          vscode.window.showErrorMessage(
            `Patch application failed: ${applyErr.message}`
          );
          return;
        }

        // Strict Requirement: Record application on backend ONLY after verified local file write
        try {
          await client.applyRepair(
            liveProposal.id,
            "vscode-developer",
            "applied",
            workspaceRoot,
            `Applied patch hash: ${approvedHash}`
          );
        } catch (backendErr: any) {
          vscode.window.showWarningMessage(
            `Files updated successfully, but reporting application to backend returned: ${backendErr.message}`
          );
        }

        patchIntegrityStore.recordApplied(liveProposal.id);
        vscode.window.showInformationMessage(
          `Repair successfully applied to ${appliedFiles.length} file(s) [Patch Hash: ${approvedHash.slice(0, 8)}].`
        );

        repairsTree.refresh();
        GuardianDashboardPanel.currentPanel?.refresh();

        // Open first applied file in editor for developer review
        if (appliedFiles.length > 0) {
          const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(appliedFiles[0]));
          await vscode.window.showTextDocument(doc);
        }
      } catch (err: any) {
        vscode.window.showErrorMessage(`Failed to apply repair: ${err.message}`);
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
      GuardianDashboardPanel.currentPanel?.refresh();
      vscode.window.showInformationMessage("Demo reset: All services restored to clean baseline v1.");
    } catch (err: any) {
      vscode.window.showErrorMessage(`Reset failed: ${err.message}`);
    }
  });

  // Command: Select Detection Mode
  const setDetectionModeCmd = vscode.commands.registerCommand(
    "dependencyGuardian.setDetectionMode",
    async (modeArg?: "algorithmic" | "hybrid" | "ai") => {
      let targetMode = modeArg;
      if (!targetMode) {
        const picked = await vscode.window.showQuickPick(
          [
            {
              label: "$(zap) Algorithmic (Deterministic)",
              description: "Fast offline schema AST diffing. No LLM required.",
              mode: "algorithmic" as const,
            },
            {
              label: "$(circuit-board) Hybrid (Recommended)",
              description: "Deterministic detection + AI explanation & repair guidance.",
              mode: "hybrid" as const,
            },
            {
              label: "$(hubot) AI-Assisted",
              description: "Deep AI semantic change reasoning and breaking change classification.",
              mode: "ai" as const,
            },
          ],
          { placeHolder: "Select Dependency Guardian Detection Mode" }
        );
        if (!picked) return;
        targetMode = picked.mode;
      }

      await updateDetectionMode(targetMode);
      vscode.window.showInformationMessage(`Detection mode set to: ${targetMode.toUpperCase()}`);
      GuardianDashboardPanel.currentPanel?.refresh();
    }
  );

  // Command: Validate External APIs
  const validateExternalApisCmd = vscode.commands.registerCommand(
    "dependencyGuardian.validateExternalApis",
    async () => {
      try {
        outputChannel.show(true);
        outputChannel.appendLine(`\n=== Running External API Live Validation ===`);

        await vscode.window.withProgress(
          {
            location: vscode.ProgressLocation.Notification,
            title: "Dependency Guardian: Validating External APIs...",
            cancellable: true,
          },
          async (progress, token) => {
            const report = await detectionService.validateExternalApis({
              cancellationToken: token,
              onProgress: (p) => progress.report({ message: p.message }),
            });

            outputChannel.appendLine(
              `[Live Validation Result] Probes: ${report.total_probes}, Reachable: ${report.reachable_count}, Contract Mismatches: ${report.contract_mismatch_count}, Blocked: ${report.security_blocked_count}`
            );

            GuardianDashboardPanel.currentPanel?.updateLiveValidationResult(report);
            GuardianDashboardPanel.currentPanel?.refresh();

            vscode.window.showInformationMessage(
              `Live API Validation Complete: ${report.total_probes} probed, ${report.contract_mismatch_count} mismatches, ${report.findings.length} findings.`
            );
          }
        );
      } catch (err: any) {
        outputChannel.appendLine(`[Live Validation Error] ${err.message}`);
        vscode.window.showErrorMessage(`Live API Validation failed: ${err.message}`);
      }
    }
  );

  // Command: Run Complete Analysis
  const runAnalysisCmd = vscode.commands.registerCommand(
    "dependencyGuardian.runAnalysis",
    async () => {
      try {
        outputChannel.show(true);
        outputChannel.appendLine(`\n=== Running Dependency Guardian Complete Analysis ===`);

        statusBar.setScanning();

        await vscode.window.withProgress(
          {
            location: vscode.ProgressLocation.Notification,
            title: "Dependency Guardian: Running Complete Analysis...",
            cancellable: true,
          },
          async (progress, token) => {
            progress.report({ message: "Executing codebase scan, contract drift, and external API validation..." });
            const result = await detectionService.runUnifiedAnalysis({
              cancellationToken: token,
            });

            if (result.drift) {
              const mapped = detectionService.mapFindingsToChanges(result.drift.findings);
              changesTree.refresh(mapped);
              GuardianDashboardPanel.currentPanel?.updateDriftResult(result.drift, mapped);
            }
            if (result.codebase) {
              GuardianDashboardPanel.currentPanel?.updateCodebaseInventory(result.codebase);
            }
            if (result.liveValidation) {
              GuardianDashboardPanel.currentPanel?.updateLiveValidationResult(result.liveValidation);
            }

            GuardianDashboardPanel.currentPanel?.refresh();

            const driftCount = result.drift?.summary.breaking_count || 0;
            const liveMismatches = result.liveValidation?.contract_mismatch_count || 0;
            const endpoints = result.codebase?.endpoints.length || 0;

            outputChannel.appendLine(
              `[Complete Analysis Complete] Endpoints: ${endpoints}, Breaking Drift: ${driftCount}, Live Mismatches: ${liveMismatches}`
            );

            if (driftCount > 0 || liveMismatches > 0) {
              statusBar.setIssues(driftCount + liveMismatches);
              vscode.window.showWarningMessage(
                `Complete Analysis Finished: ${driftCount} breaking contract changes, ${liveMismatches} live API mismatches.`
              );
            } else {
              statusBar.setHealthy();
              vscode.window.showInformationMessage(
                `Complete Analysis Finished: All systems healthy and compatible.`
              );
            }
          }
        );
      } catch (err: any) {
        outputChannel.appendLine(`[Complete Analysis Error] ${err.message}`);
        vscode.window.showErrorMessage(`Analysis failed: ${err.message}`);
      }
    }
  );

  context.subscriptions.push(
    statusBar,
    openDashboardCmd,
    openDependencyGraphCmd,
    openChatCmd,
    initCmd,
    createBaselineCmd,
    runDetectionCmd,
    scanCmd,
    scanCodebaseCmd,
    cancelCodebaseScanCmd,
    openAffectedFileCmd,
    proposeRepairCmd,
    reviewRepairCmd,
    approveRepairCmd,
    rejectRepairCmd,
    applyRepairCmd,
    setupEnvCmd,
    refreshCmd,
    resetCmd,
    setDetectionModeCmd,
    validateExternalApisCmd,
    runAnalysisCmd,
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("dependencyGuardian")) {
        GuardianDashboardPanel.currentPanel?.refresh();
      }
    })
  );

  // Initial health check in background
  checkBackendHealth();

  // Make the main dashboard the primary workspace by default
  vscode.commands.executeCommand("dependencyGuardian.openDashboard");
}

export function deactivate() {}
