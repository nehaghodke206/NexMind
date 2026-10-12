import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import {
  GuardianClient,
  ChangeItem,
  ImpactItem,
  RepairProposal,
  ValidationResult,
} from "../api/guardianClient";
import { AgentRunner } from "../agents/agentRunner";
import { DetectionService } from "../agents/detectionService";
import {
  RepositoryInventoryResult,
  ContractDriftResult,
  DetectionStateEvent,
  LiveValidationReport,
} from "../agents/detectionTypes";
import { RepairService } from "../agents/repairService";
import { getGuardianConfig, updateDetectionMode } from "../config";
import {
  patchIntegrityStore,
  extractChangeSet,
} from "../patchIntegrity";
import {
  buildDependencyGraph,
  DependencyGraphData,
} from "../graph/dependencyGraph";
import {
  calculateContractCoverage,
  ContractCoverageReport,
} from "../graph/contractCoverageReport";

export class GuardianDashboardPanel {
  public static currentPanel: GuardianDashboardPanel | undefined;
  private readonly _panel: vscode.WebviewPanel;
  private readonly _extensionUri: vscode.Uri;
  private _disposables: vscode.Disposable[] = [];
  private _selectedChangeId?: string;
  private _currentProjectId?: string;
  private _currentChanges: ChangeItem[] = [];
  private _graphData?: DependencyGraphData;
  private _coverageReport?: ContractCoverageReport;

  public static createOrShow(
    extensionUri: vscode.Uri,
    client: GuardianClient,
    changeId?: string,
    agentRunner?: AgentRunner,
    workspaceRoot?: string,
    detectionService?: DetectionService,
    repairService?: RepairService
  ) {
    const column = vscode.window.activeTextEditor
      ? vscode.window.activeTextEditor.viewColumn
      : vscode.ViewColumn.One;

    if (GuardianDashboardPanel.currentPanel) {
      GuardianDashboardPanel.currentPanel._panel.reveal(column);
      if (changeId) {
        GuardianDashboardPanel.currentPanel.selectChange(changeId);
      } else {
        GuardianDashboardPanel.currentPanel.refresh();
      }
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      "guardianDashboard",
      "Dependency Guardian Dashboard",
      column || vscode.ViewColumn.One,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [extensionUri],
      }
    );

    GuardianDashboardPanel.currentPanel = new GuardianDashboardPanel(
      panel,
      extensionUri,
      client,
      agentRunner,
      workspaceRoot,
      detectionService
    );

    if (changeId) {
      GuardianDashboardPanel.currentPanel.selectChange(changeId);
    }
  }

  private constructor(
    panel: vscode.WebviewPanel,
    extensionUri: vscode.Uri,
    private client: GuardianClient,
    private agentRunner?: AgentRunner,
    private workspaceRoot?: string,
    private detectionService?: DetectionService
  ) {
    this._panel = panel;
    this._extensionUri = extensionUri;

    this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

    if (this.detectionService) {
      this._disposables.push(
        this.detectionService.onDidChangeState((event) => {
          this.sendMessage("agentStateEvent", event);
          if (event.state === "succeeded") {
            if (event.codebaseResult) {
              this.sendMessage("codebaseScanResult", { inventory: event.codebaseResult });
            }
            if (event.driftResult) {
              const mapped = this.detectionService!.mapFindingsToChanges(event.driftResult.findings);
              this.sendMessage("driftResult", {
                driftResult: event.driftResult,
                changes: mapped,
              });
            }
            if (event.liveValidationResult) {
              this.sendMessage("liveValidationResult", { report: event.liveValidationResult });
            }
            if (event.codebaseResult || event.driftResult) {
              this.updateAndSendGraphData();
              this.updateAndSendContractCoverageData();
            }
          }
        })
      );
    }

    this._panel.webview.onDidReceiveMessage(
      async (message) => {
        try {
          switch (message.command) {
            case "webviewReady":
              await this.loadInitialData();
              break;
            case "refreshGraph":
              this.updateAndSendGraphData();
              break;
            case "refreshContractCoverage":
              this.updateAndSendContractCoverageData();
              break;
            case "openDependencyGraph":
              this.showDependencyGraph();
              break;
            case "webviewError":
              console.error(`[Guardian Dashboard Webview Error] ${message.error}`);
              break;
            case "requestCreateBaseline": {
              const inv = this.detectionService?.getLastInventory();
              const count = inv?.endpoints?.length || 0;
              const defaultTag = `v1.${Date.now().toString().slice(-4)}.0-snapshot`;
              const tag = await vscode.window.showInputBox({
                prompt: `Enter version tag for baseline snapshot (${count} endpoints discovered):`,
                value: defaultTag,
              });
              if (tag) {
                await this.handleCreateProjectBaseline(tag, `Discovered inventory snapshot (${count} endpoints)`);
              }
              break;
            }
            case "requestRejectRepair": {
              const reason = await vscode.window.showInputBox({
                prompt: "Enter reason for rejecting repair proposal:",
                value: "Rejected by developer during diff review.",
              });
              if (reason !== undefined) {
                await this.handleRejectRepair(message.repairId, reason);
              }
              break;
            }
            case "requestResolveIncident": {
              const notes = await vscode.window.showInputBox({
                prompt: "Enter resolution notes (optional):",
                value: "Resolved and verified backwards compatibility.",
              });
              if (notes !== undefined) {
                await this.handleResolveIncident(message.incidentId, notes);
              }
              break;
            }
            case "requestReopenIncident": {
              const notes = await vscode.window.showInputBox({
                prompt: "Enter reason for reopening incident:",
                value: "Contract drift re-observed in workspace.",
              });
              if (notes !== undefined) {
                await this.handleReopenIncident(message.incidentId, notes);
              }
              break;
            }
            case "refresh":
              await this.refresh();
              break;
            case "setDetectionMode":
              await updateDetectionMode(message.mode);
              await this.refresh();
              break;
            case "runAnalysis":
              vscode.commands.executeCommand("dependencyGuardian.runAnalysis");
              break;
            case "validateExternalApis":
              vscode.commands.executeCommand("dependencyGuardian.validateExternalApis");
              break;
            case "runDetection":
              vscode.commands.executeCommand("dependencyGuardian.runDetection");
              break;
            case "scan":
              vscode.commands.executeCommand("dependencyGuardian.scanDependencies");
              break;
            case "cancelScan":
              vscode.commands.executeCommand("dependencyGuardian.cancelCodebaseScan");
              break;
            case "createBaseline":
              vscode.commands.executeCommand("dependencyGuardian.createBaseline");
              break;
            case "setupEnvironment":
              vscode.commands.executeCommand("dependencyGuardian.setupEnvironment");
              break;
            case "openChat":
              vscode.commands.executeCommand("dependencyGuardian.openChat");
              break;
            case "selectChange":
              await this.selectChange(message.changeId);
              break;
            case "proposeRepair":
              await this.handleProposeRepair(message.changeId);
              break;
            case "reviewRepair":
              vscode.commands.executeCommand(
                "dependencyGuardian.reviewRepair",
                message.repairId || message.changeId
              );
              break;
            case "approveRepair":
              await this.handleApproveRepair(message.repairId);
              break;
            case "rejectRepair":
              await this.handleRejectRepair(message.repairId, message.reason);
              break;
            case "applyRepair":
              await this.handleApplyRepair(message.repairId);
              break;
            case "validateRepair":
              await this.handleValidateRepair(message.repairId);
              break;
            case "rollbackRepair":
              await this.handleRollbackRepair(message.repairId);
              break;
            case "setScenario":
              await this.handleSetScenario(message.scenario);
              break;
            case "resetDemo":
              await this.handleResetDemo();
              break;
            case "openFile":
              await this.handleOpenFile(message.filePath, message.lineNumber);
              break;
            case "acknowledgeIncident":
              await this.handleAcknowledgeIncident(message.incidentId, message.notes);
              break;
            case "resolveIncident":
              await this.handleResolveIncident(message.incidentId, message.notes);
              break;
            case "reopenIncident":
              await this.handleReopenIncident(message.incidentId, message.notes);
              break;
            case "promoteBaseline":
              await this.handlePromoteBaseline(message.baselineId);
              break;
            case "createProjectBaseline":
              await this.handleCreateProjectBaseline(message.versionTag, message.description);
              break;
            case "compareBaselines":
              await this.handleCompareBaselines(message.base, message.target);
              break;
          }
        } catch (err: any) {
          vscode.window.showErrorMessage(`Guardian Action Failed: ${err.message}`);
          this.sendMessage("actionError", { error: err.message });
        }
      },
      null,
      this._disposables
    );

    this._panel.webview.html = this._getHtmlForWebview();
    this.loadInitialData();
  }

  private async handleOpenFile(filePath: string, lineNumber?: number) {
    if (!filePath) return;
    const fullPath = path.isAbsolute(filePath)
      ? filePath
      : path.resolve(this.workspaceRoot || "", filePath);

    if (fs.existsSync(fullPath)) {
      const doc = await vscode.workspace.openTextDocument(fullPath);
      const editor = await vscode.window.showTextDocument(doc);
      if (lineNumber && lineNumber > 0) {
        const line = lineNumber - 1;
        const pos = new vscode.Position(line, 0);
        editor.selection = new vscode.Selection(pos, pos);
        editor.revealRange(new vscode.Range(pos, pos), vscode.TextEditorRevealType.InCenter);
      }
    } else {
      vscode.window.showWarningMessage(`Source file not found: ${filePath}`);
    }
  }

  private sendMessage(type: string, payload: any) {
    this._panel.webview.postMessage({ type, ...payload });
  }

  public async selectChange(changeId: string) {
    this._selectedChangeId = changeId;
    await this.loadChangeDetails(changeId);
  }

  public async refresh() {
    await this.loadInitialData();
    if (this._selectedChangeId) {
      await this.loadChangeDetails(this._selectedChangeId);
    }
  }

  public updateCodebaseInventory(inventory: RepositoryInventoryResult) {
    this.sendMessage("codebaseScanResult", { inventory });
    this.updateAndSendGraphData();
    this.updateAndSendContractCoverageData();
  }

  public updateDriftResult(driftResult: ContractDriftResult, changes: ChangeItem[]) {
    this.sendMessage("driftResult", { driftResult, changes });
    this.updateAndSendGraphData();
    this.updateAndSendContractCoverageData();
  }

  public updateLiveValidationResult(report: LiveValidationReport) {
    this.sendMessage("liveValidationResult", { report });
  }

  public showDependencyGraph() {
    this.sendMessage("showDependencyGraph", {});
  }

  private updateAndSendGraphData() {
    let inv = this.detectionService?.getLastInventory();
    if (!inv && this.workspaceRoot) {
      try {
        const p = path.join(this.workspaceRoot, "reports", "repository-inventory", "repository-inventory.json");
        if (fs.existsSync(p)) {
          inv = JSON.parse(fs.readFileSync(p, "utf-8"));
        }
      } catch {}
    }
    const driftResult = this.detectionService?.getLastDriftResult();
    const findings = driftResult?.findings || [];
    this._graphData = buildDependencyGraph({
      inventory: inv || null,
      driftFindings: findings,
      workspaceRoot: this.workspaceRoot,
    });
    this.sendMessage("dependencyGraphData", { graph: this._graphData });
  }

  private updateAndSendContractCoverageData() {
    let inv = this.detectionService?.getLastInventory();
    if (!inv && this.workspaceRoot) {
      try {
        const p = path.join(this.workspaceRoot, "reports", "repository-inventory", "repository-inventory.json");
        if (fs.existsSync(p)) {
          inv = JSON.parse(fs.readFileSync(p, "utf-8"));
        }
      } catch {}
    }
    const driftResult = this.detectionService?.getLastDriftResult();
    const findings = driftResult?.findings || [];
    this._coverageReport = calculateContractCoverage({
      inventory: inv || null,
      driftFindings: findings,
      workspaceRoot: this.workspaceRoot,
    });
    this.sendMessage("contractCoverageData", { report: this._coverageReport });
  }

  private async loadInitialData() {
    const config = getGuardianConfig();
    let aiModelReady = false;
    let aiModelMessage = "Algorithmic AST mode (offline)";

    if (this.agentRunner) {
      try {
        const probe = await this.agentRunner.probeOllama(config.ollamaBaseUrl, config.ollamaModel);
        if (probe.reachable && probe.modelInstalled) {
          aiModelReady = true;
          aiModelMessage = `${config.ollamaModel} ready`;
        } else if (probe.reachable) {
          aiModelReady = false;
          aiModelMessage = `${config.ollamaModel} not installed`;
        } else {
          aiModelReady = false;
          aiModelMessage = `Ollama offline (fallback)`;
        }
      } catch {
        aiModelReady = false;
        aiModelMessage = `Ollama offline (fallback)`;
      }
    }

    try {
      const health = await this.client.getHealth();
      const services = await this.client.getServices();
      const changes = await this.client.getChanges();

      let projects: any[] = [];
      let baselines: any[] = [];
      let activeBaseline: any = null;
      let scanHistory: any[] = [];

      try {
        projects = await this.client.getProjects();
        if (projects.length > 0) {
          const currentPid = config.projectId || projects[0].id;
          this._currentProjectId = currentPid;
          const blRes = await this.client.getProjectBaselines(currentPid);
          baselines = blRes.items || [];
          activeBaseline = blRes.active_baseline || null;
          scanHistory = await this.client.listProjectScans(currentPid, 20);
        }
      } catch {}

      const allRepairs: RepairProposal[] = [];
      for (const c of changes) {
        try {
          const props = await this.client.getRepairProposals(c.id);
          allRepairs.push(...props);
        } catch {}
      }

      const breakingCount = changes.filter(
        (c) =>
          c.severity === "high" ||
          c.severity === "critical" ||
          c.severity === "blocked"
      ).length;

      const approvedCount = allRepairs.filter(
        (r) => r.status === "approved" || r.status === "applied"
      ).length;

      this.sendMessage("initialData", {
        health,
        services,
        changes,
        repairs: allRepairs,
        projects,
        currentProjectId: this._currentProjectId,
        baselines,
        activeBaseline,
        scanHistory,
        detectionConfig: {
          mode: config.detectionMode,
          aiProvider: config.aiProvider,
          ollamaModel: config.ollamaModel,
          ollamaBaseUrl: config.ollamaBaseUrl,
          aiModelReady,
          aiModelMessage,
        },
        metrics: {
          servicesCount: services.length,
          changesCount: changes.length,
          breakingCount,
          repairsCount: allRepairs.length,
          approvedCount,
          activeBaselineVersion: activeBaseline ? `v${activeBaseline.version_number}` : "None",
          activeBaselineTag: activeBaseline?.version_tag || "No active baseline",
          scansCount: scanHistory.length,
        },
      });

      if (this.detectionService) {
        const lastInv = this.detectionService.getLastInventory();
        if (lastInv) {
          this.sendMessage("codebaseScanResult", { inventory: lastInv });
        }
        const lastDrift = this.detectionService.getLastDriftResult();
        if (lastDrift) {
          const mapped = this.detectionService.mapFindingsToChanges(lastDrift.findings);
          this.sendMessage("driftResult", { driftResult: lastDrift, changes: mapped });
        }
        const lastLive = this.detectionService.getLastLiveValidationResult();
        if (lastLive) {
          this.sendMessage("liveValidationResult", { report: lastLive });
        }
      }

      this.updateAndSendGraphData();
      this.updateAndSendContractCoverageData();

      if (!this._selectedChangeId && changes.length > 0) {
        await this.selectChange(changes[0].id);
      }
    } catch (err: any) {
      this.sendMessage("backendOffline", {
        error: err.message,
        url: this.client.getBaseUrl(),
        detectionConfig: {
          mode: config.detectionMode,
          aiProvider: config.aiProvider,
          ollamaModel: config.ollamaModel,
          ollamaBaseUrl: config.ollamaBaseUrl,
          aiModelReady,
          aiModelMessage,
        },
      });

      if (this.detectionService) {
        const lastInv = this.detectionService.getLastInventory();
        if (lastInv) {
          this.sendMessage("codebaseScanResult", { inventory: lastInv });
        }
        const lastDrift = this.detectionService.getLastDriftResult();
        if (lastDrift) {
          const mapped = this.detectionService.mapFindingsToChanges(lastDrift.findings);
          this.sendMessage("driftResult", { driftResult: lastDrift, changes: mapped });
        }
        const lastLive = this.detectionService.getLastLiveValidationResult();
        if (lastLive) {
          this.sendMessage("liveValidationResult", { report: lastLive });
        }
      }

      this.updateAndSendGraphData();
      this.updateAndSendContractCoverageData();
    }
  }

  private async loadChangeDetails(changeId: string) {
    try {
      const changes = await this.client.getChanges();
      let change = changes.find((c) => c.id === changeId);

      if (!change && this.detectionService) {
        const lastDrift = this.detectionService.getLastDriftResult();
        if (lastDrift) {
          const mapped = this.detectionService.mapFindingsToChanges(lastDrift.findings);
          change = mapped.find((c) => c.id === changeId);
        }
      }

      if (!change) return;

      let impacts: ImpactItem[] = [];
      try {
        impacts = await this.client.getChangeImpact(changeId);
      } catch {}

      let repairs: RepairProposal[] = [];
      try {
        repairs = await this.client.getRepairProposals(changeId);
      } catch {}

      let events: any[] = [];
      try {
        events = await this.client.getIncidentEvents(changeId);
      } catch {}

      let currentRepair = repairs.length > 0 ? repairs[0] : null;
      let staleness: { isStale: boolean; reason?: string } = { isStale: false };
      let changeSet: any[] = [];

      if (currentRepair && this.workspaceRoot) {
        try {
          patchIntegrityStore.recordReview(currentRepair, this.workspaceRoot);
        } catch {}
        staleness = patchIntegrityStore.checkProposalStaleness(currentRepair, this.workspaceRoot);
        changeSet = extractChangeSet(currentRepair, this.workspaceRoot).map((fc) => {
          let orig = fc.originalContent;
          if (orig === undefined || orig === null || orig === "") {
            const fullPath = path.resolve(this.workspaceRoot!, fc.relativePath);
            if (fs.existsSync(fullPath)) {
              try {
                orig = fs.readFileSync(fullPath, "utf-8");
              } catch {}
            }
          }
          return {
            relativePath: fc.relativePath,
            originalContent: orig || "",
            proposedContent: fc.proposedContent || "",
          };
        });
      }

      this.sendMessage("changeSelected", {
        change,
        impacts,
        repairs,
        events,
        currentRepair,
        staleness,
        changeSet,
      });
    } catch (err: any) {
      this.sendMessage("actionError", { error: err.message });
    }
  }

  private async handleAcknowledgeIncident(incidentId: string, notes?: string) {
    try {
      await this.client.acknowledgeIncident(incidentId, notes || "Acknowledged via Dashboard");
      vscode.window.showInformationMessage("Incident acknowledged.");
      await this.refresh();
    } catch (err: any) {
      vscode.window.showErrorMessage(`Failed to acknowledge incident: ${err.message}`);
    }
  }

  private async handleResolveIncident(incidentId: string, notes?: string) {
    try {
      await this.client.resolveIncident(incidentId, notes || "Resolved via Dashboard");
      vscode.window.showInformationMessage("Incident resolved.");
      await this.refresh();
    } catch (err: any) {
      vscode.window.showErrorMessage(`Failed to resolve incident: ${err.message}`);
    }
  }

  private async handleReopenIncident(incidentId: string, notes?: string) {
    try {
      await this.client.reopenIncident(incidentId, notes || "Reopened via Dashboard");
      vscode.window.showInformationMessage("Incident reopened.");
      await this.refresh();
    } catch (err: any) {
      vscode.window.showErrorMessage(`Failed to reopen incident: ${err.message}`);
    }
  }

  private async handlePromoteBaseline(baselineId: string) {
    if (!this._currentProjectId) {
      vscode.window.showErrorMessage("No active project found to promote baseline.");
      return;
    }
    try {
      await this.client.promoteProjectBaseline(this._currentProjectId, baselineId);
      vscode.window.showInformationMessage("Baseline promoted as active project reference.");
      await this.refresh();
    } catch (err: any) {
      vscode.window.showErrorMessage(`Failed to promote baseline: ${err.message}`);
    }
  }

  private async handleCreateProjectBaseline(versionTag?: string, description?: string) {
    let targetPid = this._currentProjectId;
    if (!targetPid) {
      const config = getGuardianConfig();
      targetPid = config.projectId;
      if (!targetPid) {
        try {
          const projects = await this.client.getProjects();
          if (projects && projects.length > 0) {
            targetPid = projects[0].id;
          }
        } catch {}
      }
    }
    if (!targetPid) {
      vscode.window.showErrorMessage("No active project found to create baseline.");
      return;
    }
    this._currentProjectId = targetPid;
    try {
      const inv = this.detectionService?.getLastInventory();
      let contracts: Record<string, any> = {};
      if (this.workspaceRoot) {
        const openapiCandidate = path.join(this.workspaceRoot, "reports", "repository-inventory", "openapi.enriched.json");
        const demoCandidate = path.join(this.workspaceRoot, "demo", "sample-api", "contracts", "openapi-v1.json");
        if (fs.existsSync(openapiCandidate)) {
          try { contracts = JSON.parse(fs.readFileSync(openapiCandidate, "utf-8")); } catch {}
        } else if (fs.existsSync(demoCandidate)) {
          try { contracts = JSON.parse(fs.readFileSync(demoCandidate, "utf-8")); } catch {}
        }
      }
      await this.client.createProjectBaseline(targetPid, {
        version_tag: versionTag || `v${Date.now()}`,
        description: description || "Captured snapshot from VS Code Extension",
        inventory: inv ? { endpoints: inv.endpoints || [], discovered_endpoints: inv.endpoints?.length || 0 } : {},
        contracts,
      });
      vscode.window.showInformationMessage("Created new project baseline snapshot.");
      await this.refresh();
    } catch (err: any) {
      vscode.window.showErrorMessage(`Failed to create project baseline: ${err.message}`);
    }
  }

  private async handleCompareBaselines(base: string, target: string) {
    let pid = this._currentProjectId;
    if (!pid) {
      try {
        const projs = await this.client.getProjects();
        if (projs.length > 0) {
          pid = projs[0].id;
          this._currentProjectId = pid;
        }
      } catch {}
    }
    if (!pid) {
      vscode.window.showErrorMessage("No active project found for baseline comparison.");
      this.sendMessage("actionError", { action: "compareBaselines", error: "No active project found." });
      return;
    }
    try {
      this.sendMessage("actionRunning", { action: "compareBaselines" });
      const diff = await this.client.compareProjectBaselines(pid, base, target);
      this.sendMessage("baselineCompareResult", { diff, base, target });
    } catch (err: any) {
      vscode.window.showErrorMessage(`Baseline comparison failed: ${err.message}`);
      this.sendMessage("actionError", { action: "compareBaselines", error: err.message });
    }
  }

  private async handleProposeRepair(changeId: string) {
    if (!this.workspaceRoot) {
      vscode.window.showErrorMessage("No workspace root found.");
      return;
    }

    try {
      this.sendMessage("actionRunning", { action: "proposeRepair", changeId });
      let repairResult: any;
      if (this.agentRunner) {
        await vscode.window.withProgress(
          {
            location: vscode.ProgressLocation.Notification,
            title: `Dependency Guardian: Generating repair proposal for incident ${changeId.slice(0, 8)}...`,
            cancellable: false,
          },
          async () => {
            repairResult = await this.agentRunner!.runRepair(this.workspaceRoot!, {
              incidentId: changeId,
              syncBackend: true,
            });
          }
        );
      }

      const proposals = await this.client.getRepairProposals(changeId);
      if (proposals.length === 0) {
        throw new Error(
          repairResult?.error_message ||
          "No repair proposal was generated for this incident. Insufficient evidence or no automated pattern matched."
        );
      }

      const proposal = proposals[0];
      this.sendMessage("repairProposed", { proposal });
      await this.refresh();
      vscode.window.showInformationMessage(
        `Repair proposal '${proposal.id.slice(0, 8)}' created for incident '${changeId.slice(0, 8)}'.`
      );
    } catch (err: any) {
      vscode.window.showErrorMessage(`Failed to generate repair proposal: ${err.message}`);
      this.sendMessage("actionError", { action: "proposeRepair", error: err.message, changeId });
    }
  }

  private async handleApproveRepair(repairId: string) {
    try {
      this.sendMessage("actionRunning", { action: "approveRepair", repairId });
      let proposal = await this.client.getRepair(repairId);
      if (!proposal) {
        throw new Error(`Repair proposal '${repairId}' not found on backend.`);
      }

      // Ensure review record exists for the proposal
      let record = patchIntegrityStore.getRecord(proposal.id);
      if (!record || !record.isDiffReviewed) {
        record = patchIntegrityStore.recordReview(proposal, this.workspaceRoot!);
      }

      const patchHash = record.patchHash;

      let approvalRes: any;
      if (proposal.status !== "approved") {
        // 1. Call real backend approval operation
        approvalRes = await this.client.approveRepair(
          proposal.id,
          "vscode-developer",
          `Approved patch hash: ${patchHash}`
        );
      }

      // 2. Bind approval locally to the exact reviewed patch hash
      const approvedHash = patchIntegrityStore.recordApproval(proposal.id);

      // 3. Retrieve / confirm persisted proposal status from backend
      const liveProposal = await this.client.getRepair(proposal.id);
      if (liveProposal.status !== "approved") {
        throw new Error(
          `Backend approval completed but proposal status is '${liveProposal.status}', expected 'approved'.`
        );
      }

      this.sendMessage("repairApproved", {
        repair: liveProposal,
        approvedHash,
        approval: approvalRes,
      });

      vscode.window.showInformationMessage(
        `Repair proposal '${liveProposal.id.slice(0, 8)}' approved [Bound to Patch Hash: ${approvedHash.slice(0, 8)}]. Ready for safe application.`
      );

      await this.refresh();
    } catch (err: any) {
      patchIntegrityStore.revokeApproval(repairId);
      vscode.window.showErrorMessage(`Failed to approve repair proposal: ${err.message}`);
      this.sendMessage("actionError", { action: "approveRepair", error: err.message, repairId });
      await this.refresh();
    }
  }

  private async handleRejectRepair(repairId: string, reason?: string) {
    try {
      this.sendMessage("actionRunning", { action: "rejectRepair", repairId });
      let proposal = await this.client.getRepair(repairId);
      if (!proposal) {
        throw new Error(`Repair proposal '${repairId}' not found.`);
      }

      if (proposal.status === "applied") {
        throw new Error(`Cannot reject repair: Proposal '${proposal.id.slice(0, 8)}' has already been applied.`);
      }

      const rejectionReason = reason || "Rejected by developer during diff review.";
      await this.client.rejectRepair(proposal.id, "vscode-developer", rejectionReason);
      patchIntegrityStore.revokeApproval(proposal.id);

      const updatedRepair = await this.client.getRepair(proposal.id);

      this.sendMessage("repairRejected", {
        repair: updatedRepair,
        reason: rejectionReason,
      });

      vscode.window.showInformationMessage(
        `Repair proposal '${proposal.id.slice(0, 8)}' rejected. Status updated to 'rejected'.`
      );

      await this.refresh();
    } catch (err: any) {
      vscode.window.showErrorMessage(`Failed to reject repair proposal: ${err.message}`);
      this.sendMessage("actionError", { action: "rejectRepair", error: err.message, repairId });
      await this.refresh();
    }
  }

  private async handleApplyRepair(repairId: string) {
    try {
      this.sendMessage("actionRunning", { action: "applyRepair", repairId });
      let proposal = await this.client.getRepair(repairId);
      if (!proposal) {
        throw new Error(`Repair proposal '${repairId}' not found.`);
      }

      // 1. Mandatory backend status check: Proposal must be in 'approved' status!
      if (proposal.status !== "approved") {
        throw new Error(
          `Cannot apply repair: Repair proposal '${proposal.id.slice(0, 8)}' status on backend is '${proposal.status}'. ` +
          `Repair proposal must be in 'approved' status on the backend before changes can be applied.`
        );
      }

      // 2. Reject stale proposals if source file changed on disk
      const staleness = patchIntegrityStore.checkProposalStaleness(proposal, this.workspaceRoot!);
      if (staleness.isStale) {
        throw new Error(`Cannot apply repair: ${staleness.reason}`);
      }

      // Ensure review record exists for the proposal
      let record = patchIntegrityStore.getRecord(proposal.id);
      if (!record || !record.isDiffReviewed) {
        record = patchIntegrityStore.recordReview(proposal, this.workspaceRoot!);
      }

      // If already approved on backend, bind human approval to the reviewed patch hash
      if (proposal.status === "approved" && !record.approvedPatchHash) {
        patchIntegrityStore.recordApproval(proposal.id);
      }

      // 3. Patch integrity verification
      const verification = patchIntegrityStore.verifyBeforeApplication(proposal, this.workspaceRoot!);
      if (!verification.ok) {
        throw new Error(`Repair application aborted: ${verification.reason}`);
      }

      const changes = verification.changes!;
      const approvedHash = verification.approvedHash!;

      // 4. Human confirmation modal
      const fileList = changes.map((c) => c.relativePath).join(", ");
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
        this.sendMessage("actionCancelled", { action: "applyRepair", repairId });
        return;
      }

      // 5. Safe atomic file application with persistent backup (.guardian.bak)
      const appliedFiles = patchIntegrityStore.applyApprovedChangesSafely(
        changes,
        this.workspaceRoot!,
        proposal.id
      );

      // 6. Record application on backend
      const appResult = await this.client.applyRepair(
        proposal.id,
        "vscode-developer",
        "applied",
        this.workspaceRoot,
        `Repair applied to ${appliedFiles.length} file(s) with patch hash ${approvedHash.slice(0, 12)}`
      );

      patchIntegrityStore.recordApplied(proposal.id);

      // 7. Re-fetch proposal from backend to confirm 'applied' status
      const updatedRepair = await this.client.getRepair(proposal.id);

      this.sendMessage("repairApplied", {
        repair: updatedRepair,
        result: appResult,
        appliedFiles,
      });

      vscode.window.showInformationMessage(
        `Repair applied successfully to ${appliedFiles.length} file(s). Status updated to 'applied'.`
      );

      await this.refresh();
    } catch (err: any) {
      vscode.window.showErrorMessage(`Apply repair failed: ${err.message}`);
      this.sendMessage("actionError", { action: "applyRepair", error: err.message, repairId });
      await this.refresh();
    }
  }

  private async handleValidateRepair(repairId: string) {
    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: "Running contract & regression validation...",
        cancellable: false,
      },
      async () => {
        try {
          this.sendMessage("actionRunning", { action: "validateRepair", repairId });
          let result: any;
          if (this.agentRunner) {
            result = await this.agentRunner.runRepairValidation(this.workspaceRoot || "", repairId);
          } else {
            result = await this.client.validateRepair(repairId);
          }
          const repair = await this.client.getRepair(repairId);
          this.sendMessage("validationCompleted", { result, repair });
          if (result.status === "passed") {
            vscode.window.showInformationMessage("Validation Passed. Repair is ready for review/approval.");
          } else {
            vscode.window.showWarningMessage("Validation Failed. Review test summary.");
          }
        } catch (err: any) {
          vscode.window.showErrorMessage(`Validation failed: ${err.message}`);
          this.sendMessage("actionError", { action: "validateRepair", error: err.message, repairId });
        }
      }
    );
  }

  private async handleRollbackRepair(repairId: string) {
    try {
      this.sendMessage("actionRunning", { action: "rollbackRepair", repairId });
      const restored = patchIntegrityStore.rollbackAppliedChanges(this.workspaceRoot!, repairId);
      const result = await this.client.rollbackRepair(repairId);
      const repair = await this.client.getRepair(repairId);
      this.sendMessage("repairRolledBack", { result, repair, restoredFiles: restored });
      await this.refresh();
      vscode.window.showInformationMessage(
        `Repair rolled back. Restored ${restored.length} file(s) in workspace.`
      );
    } catch (err: any) {
      vscode.window.showErrorMessage(`Rollback failed: ${err.message}`);
      this.sendMessage("actionError", { action: "rollbackRepair", error: err.message, repairId });
      await this.refresh();
    }
  }

  private async handleSetScenario(scenario: string) {
    try {
      await this.client.setScenario(scenario);
      vscode.window.showInformationMessage(`Simulator scenario updated: ${scenario}`);
      vscode.commands.executeCommand("dependencyGuardian.scanDependencies");
    } catch (err: any) {
      vscode.window.showErrorMessage(`Scenario update failed: ${err.message}`);
    }
  }

  private async handleResetDemo() {
    try {
      await this.client.resetDemo();
      vscode.window.showInformationMessage("Demo reset: All services restored to baseline v1.");
      await this.refresh();
    } catch (err: any) {
      vscode.window.showErrorMessage(`Demo reset failed: ${err.message}`);
    }
  }

  public dispose() {
    GuardianDashboardPanel.currentPanel = undefined;
    this._panel.dispose();
    while (this._disposables.length) {
      const x = this._disposables.pop();
      if (x) x.dispose();
    }
  }

  private _getHtmlForWebview(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';">
  <title>Dependency Guardian Dashboard</title>
  <style>
    :root {
      --bg: var(--vscode-editor-background, #1E1E1E);
      --card-bg: var(--vscode-sideBar-background, #252526);
      --input-bg: var(--vscode-input-background, #2D2D30);
      --border-subtle: var(--vscode-widget-border, #3E3E42);
      --border-focus: var(--vscode-focusBorder, #007ACC);
      --hover-subtle: var(--vscode-list-hoverBackground, #37373D);
      --text-main: var(--vscode-editor-foreground, #CCCCCC);
      --text-muted: var(--vscode-descriptionForeground, #8E8E93);
      --accent: var(--vscode-button-background, #0E639C);
      --accent-hover: var(--vscode-button-hoverBackground, #1177BB);
      --code-bg: var(--vscode-textCodeBlock-background, #1E1E1E);
      --error-color: var(--vscode-errorForeground, #F14C4C);
      --warning-color: var(--vscode-editorWarning-foreground, #CCA700);
      --success-color: var(--vscode-testing-iconPassed, #4EC9B0);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg);
      color: var(--text-main);
      font-family: var(--vscode-font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
      font-size: var(--vscode-font-size, 12px);
      line-height: 1.5;
      padding: 18px 24px;
    }

    .dashboard-container {
      max-width: 1400px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    /* Header */
    .dashboard-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--border-subtle);
    }

    .brand-title h1 {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-main);
      letter-spacing: -0.2px;
    }

    .brand-subtitle {
      font-size: 11px;
      color: var(--text-muted);
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .status-indicator {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 3px 8px;
      border: 1px solid var(--border-subtle);
      border-radius: 3px;
      font-size: 11px;
      background: var(--input-bg);
      color: var(--text-main);
    }

    .status-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--text-muted);
    }

    .status-dot.online { background: var(--success-color); }
    .status-dot.offline { background: var(--error-color); }
    .status-dot.running { background: var(--warning-color); }

    /* Buttons */
    .btn {
      font-family: inherit;
      font-size: 11px;
      font-weight: 500;
      padding: 5px 12px;
      border-radius: 3px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: background 0.1s ease;
      white-space: nowrap;
    }

    .btn-primary {
      background: var(--accent);
      color: var(--vscode-button-foreground, #FFFFFF);
      border: 1px solid var(--accent);
    }

    .btn-primary:hover {
      background: var(--accent-hover);
      border-color: var(--accent-hover);
    }

    .btn-secondary {
      background: transparent;
      color: var(--text-main);
      border: 1px solid var(--border-subtle);
    }

    .btn-secondary:hover {
      background: var(--hover-subtle);
    }

    .btn-sm {
      padding: 3px 8px;
      font-size: 10px;
    }

    .btn:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }

    /* Offline Banner */
    .offline-banner {
      background: var(--input-bg);
      border: 1px solid var(--border-subtle);
      border-left: 3px solid var(--warning-color);
      padding: 10px 14px;
      border-radius: 3px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }

    .banner-text strong {
      color: var(--warning-color);
      display: block;
      font-size: 11px;
      margin-bottom: 2px;
    }

    .banner-text p {
      color: var(--text-muted);
      font-size: 11px;
    }

    .banner-buttons {
      display: flex;
      gap: 8px;
      flex-shrink: 0;
    }

    /* Metrics Strip */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: 12px;
    }

    .metric-card {
      background: var(--card-bg);
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      padding: 10px 14px;
    }

    .metric-num {
      font-size: 18px;
      font-weight: 600;
      color: var(--text-main);
      margin-bottom: 2px;
    }

    .metric-label {
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      font-weight: 500;
    }

    /* Actions & Controls Toolbar */
    .toolbar-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--card-bg);
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      padding: 8px 12px;
      gap: 10px;
      flex-wrap: wrap;
    }

    .toolbar-left, .toolbar-right {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    /* Tab Switcher */
    .tab-bar {
      display: flex;
      gap: 4px;
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 2px;
    }

    .tab-btn {
      background: transparent;
      color: var(--text-muted);
      border: none;
      border-bottom: 2px solid transparent;
      padding: 6px 14px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      transition: color 0.1s ease, border-color 0.1s ease;
    }

    .tab-btn:hover {
      color: var(--text-main);
    }

    .tab-btn.active {
      color: var(--text-main);
      border-bottom-color: var(--border-focus);
    }

    /* Split Workspace Grid */
    .workspace-grid {
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 16px;
      min-height: 520px;
    }

    .panel-box {
      background: var(--card-bg);
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .panel-box-header {
      padding: 10px 12px;
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--card-bg);
    }

    .panel-box-header h2 {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
    }

    .count-pill {
      font-size: 10px;
      padding: 1px 6px;
      border-radius: 2px;
      background: var(--input-bg);
      color: var(--text-main);
      border: 1px solid var(--border-subtle);
    }

    /* Incident List */
    .incident-list {
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      overflow-y: auto;
      max-height: 600px;
    }

    .incident-item {
      background: var(--input-bg);
      border: 1px solid var(--border-subtle);
      border-radius: 3px;
      padding: 8px 10px;
      cursor: pointer;
      transition: background 0.1s ease, border-color 0.1s ease;
    }

    .incident-item:hover {
      background: var(--hover-subtle);
    }

    .incident-item.active {
      border-color: var(--border-focus);
      background: var(--hover-subtle);
    }

    .incident-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 3px;
    }

    .incident-name {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-main);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 240px;
    }

    .tag {
      font-size: 9px;
      font-weight: 600;
      text-transform: uppercase;
      padding: 1px 5px;
      border-radius: 2px;
      letter-spacing: 0.3px;
    }

    .tag.breaking {
      border: 1px solid rgba(241, 76, 76, 0.4);
      color: var(--error-color);
    }

    .tag.medium {
      border: 1px solid rgba(204, 167, 0, 0.4);
      color: var(--warning-color);
    }

    .tag.low {
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
    }

    .tag.approved {
      border: 1px solid rgba(78, 201, 176, 0.4);
      color: var(--success-color);
    }

    .tag.method-get { color: #4EC9B0; border: 1px solid rgba(78, 201, 176, 0.3); }
    .tag.method-post { color: #569CD6; border: 1px solid rgba(86, 156, 214, 0.3); }
    .tag.method-put { color: #DCDCAA; border: 1px solid rgba(220, 220, 170, 0.3); }
    .tag.method-delete { color: #F14C4C; border: 1px solid rgba(241, 76, 76, 0.3); }
    .tag.method-patch { color: #C586C0; border: 1px solid rgba(197, 134, 192, 0.3); }

    .tag.provenance-static_ast { color: #9CDCFE; border: 1px solid rgba(156, 220, 254, 0.4); background: rgba(156, 220, 254, 0.08); }
    .tag.provenance-contract_diff { color: #CE9178; border: 1px solid rgba(206, 145, 120, 0.4); background: rgba(206, 145, 120, 0.08); }
    .tag.provenance-live_probe { color: #4EC9B0; border: 1px solid rgba(78, 201, 176, 0.4); background: rgba(78, 201, 176, 0.08); }
    .tag.provenance-ai_inferred { color: #C586C0; border: 1px solid rgba(197, 134, 192, 0.4); background: rgba(197, 134, 192, 0.08); }

    .tag.status-open { color: #569CD6; border: 1px solid rgba(86, 156, 214, 0.4); background: rgba(86, 156, 214, 0.08); }
    .tag.status-acknowledged { color: #DCDCAA; border: 1px solid rgba(220, 220, 170, 0.4); background: rgba(220, 220, 170, 0.08); }
    .tag.status-resolved { color: #4EC9B0; border: 1px solid rgba(78, 201, 176, 0.4); background: rgba(78, 201, 176, 0.08); }
    .tag.status-reopened { color: #F14C4C; border: 1px solid rgba(241, 76, 76, 0.4); background: rgba(241, 76, 76, 0.08); }
    .tag.occurrence { color: var(--text-muted); border: 1px solid var(--border-subtle); background: var(--input-bg); font-weight: 600; }
    .tag.mode-algorithmic { color: #9CDCFE; border: 1px solid rgba(156, 220, 254, 0.4); }
    .tag.mode-hybrid { color: #C586C0; border: 1px solid rgba(197, 134, 192, 0.4); }
    .tag.mode-ai { color: #4EC9B0; border: 1px solid rgba(78, 201, 176, 0.4); }

    .filter-btn {
      font-size: 10px;
      padding: 2px 7px;
      border-radius: 2px;
      border: 1px solid var(--border-subtle);
      background: transparent;
      color: var(--text-muted);
      cursor: pointer;
    }
    .filter-btn.active {
      background: var(--accent);
      color: #FFF;
      border-color: var(--accent);
    }

    .rec-action-box {
      margin-top: 8px;
      padding: 8px 10px;
      background: rgba(78, 201, 176, 0.08);
      border-left: 3px solid var(--success-color);
      border-radius: 2px;
      font-size: 11px;
      line-height: 1.4;
      color: var(--text-main);
    }

    .rec-action-title {
      font-weight: 600;
      color: var(--success-color);
      margin-bottom: 2px;
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .tech-evidence-details {
      margin-top: 10px;
      padding: 6px 8px;
      background: var(--input-bg);
      border: 1px solid var(--border-subtle);
      border-radius: 3px;
    }

    .tech-evidence-details summary {
      cursor: pointer;
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
      list-style: none;
      display: flex;
      align-items: center;
      gap: 6px;
      user-select: none;
    }

    .tech-evidence-details summary::-webkit-details-marker {
      display: none;
    }

    .tech-evidence-details summary::before {
      content: '▶';
      font-size: 9px;
      display: inline-block;
      transition: transform 0.15s ease;
    }

    .tech-evidence-details[open] summary::before {
      transform: rotate(90deg);
    }

    .mode-selector-wrapper {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: var(--card-bg);
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      padding: 2px 6px;
    }

    .mode-label {
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      color: var(--text-muted);
      letter-spacing: 0.5px;
    }

    .mode-selector {
      display: inline-flex;
      align-items: center;
      background: var(--input-bg);
      border: 1px solid var(--border-subtle);
      border-radius: 3px;
      padding: 1px;
    }

    .mode-btn {
      font-family: inherit;
      font-size: 10px;
      font-weight: 500;
      padding: 3px 8px;
      border: none;
      background: transparent;
      color: var(--text-muted);
      cursor: pointer;
      border-radius: 2px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: all 0.15s ease;
    }

    .mode-btn:hover {
      color: var(--text-main);
      background: var(--hover-subtle);
    }

    .mode-btn.active {
      background: var(--accent);
      color: var(--vscode-button-foreground, #FFFFFF);
      font-weight: 600;
    }

    .mode-btn .mode-dot {
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: currentColor;
    }

    .ai-model-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 10px;
      color: var(--text-muted);
      padding: 2px 6px;
      border-radius: 2px;
      border: 1px solid var(--border-subtle);
      background: var(--input-bg);
    }

    .probe-status-pill {
      font-size: 10px;
      font-weight: 600;
      padding: 2px 6px;
      border-radius: 2px;
      text-transform: uppercase;
      display: inline-block;
    }
    .probe-status-pill.reachable { color: var(--success-color); border: 1px solid rgba(78, 201, 176, 0.4); background: rgba(78, 201, 176, 0.08); }
    .probe-status-pill.auth_failure { color: var(--warning-color); border: 1px solid rgba(204, 167, 0, 0.4); background: rgba(204, 167, 0, 0.08); }
    .probe-status-pill.client_error { color: var(--warning-color); border: 1px solid rgba(204, 167, 0, 0.4); background: rgba(204, 167, 0, 0.08); }
    .probe-status-pill.server_failure { color: var(--error-color); border: 1px solid rgba(241, 76, 76, 0.4); background: rgba(241, 76, 76, 0.08); }
    .probe-status-pill.unreachable { color: var(--text-muted); border: 1px solid var(--border-subtle); }
    .probe-status-pill.contract_mismatch { color: var(--error-color); border: 1px solid rgba(241, 76, 76, 0.4); background: rgba(241, 76, 76, 0.08); }
    .probe-status-pill.security_blocked { color: #E06C75; border: 1px solid rgba(224, 108, 117, 0.4); background: rgba(224, 108, 117, 0.08); }

    .rec-action-box {
      background: rgba(14, 99, 156, 0.1);
      border: 1px solid rgba(14, 99, 156, 0.3);
      border-left: 3px solid var(--accent);
      border-radius: 3px;
      padding: 8px 10px;
      font-size: 11px;
      color: var(--text-main);
      line-height: 1.5;
    }

    .incident-sub {
      font-size: 10px;
      color: var(--text-muted);
      font-family: Consolas, monospace;
    }

    /* Details Panel */
    .details-scroll {
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      overflow-y: auto;
      max-height: 600px;
    }

    .section-card {
      background: var(--input-bg);
      border: 1px solid var(--border-subtle);
      border-radius: 3px;
      padding: 12px;
    }

    .section-header {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      margin-bottom: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .evidence-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }

    .code-box {
      background: var(--code-bg);
      border: 1px solid var(--border-subtle);
      border-radius: 3px;
      padding: 8px 10px;
      font-family: Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 11px;
      line-height: 1.5;
      overflow-x: auto;
      max-height: 180px;
      white-space: pre;
    }

    .diff-line-del { color: var(--error-color); background: rgba(241, 76, 76, 0.08); display: block; }
    .diff-line-add { color: var(--success-color); background: rgba(78, 201, 176, 0.08); display: block; }

    /* Git-Style Diff Review UI */
    .diff-review-container {
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      overflow: hidden;
      background: var(--input-bg);
      margin-bottom: 12px;
      font-family: var(--vscode-editor-font-family, 'Menlo', 'Monaco', 'Courier New', monospace);
      font-size: 11px;
    }

    .diff-review-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 10px;
      background: var(--card-bg);
      border-bottom: 1px solid var(--border-subtle);
      flex-wrap: wrap;
      gap: 8px;
    }

    .diff-file-tabs {
      display: flex;
      gap: 4px;
      overflow-x: auto;
      max-width: 65%;
    }

    .diff-file-tab {
      padding: 3px 8px;
      border-radius: 3px;
      background: var(--input-bg);
      border: 1px solid var(--border-subtle);
      font-size: 10px;
      cursor: pointer;
      color: var(--text-main);
      display: inline-flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
    }

    .diff-file-tab.active {
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }

    .diff-stats-badge {
      font-size: 10px;
      display: inline-flex;
      gap: 6px;
      align-items: center;
      color: var(--text-muted);
    }

    .diff-stat-add {
      color: var(--success-color);
      font-weight: 600;
    }

    .diff-stat-del {
      color: var(--error-color);
      font-weight: 600;
    }

    .diff-view-mode-toggle {
      display: inline-flex;
      border: 1px solid var(--border-subtle);
      border-radius: 3px;
      overflow: hidden;
    }

    .diff-view-mode-btn {
      background: var(--card-bg);
      border: none;
      padding: 3px 8px;
      font-size: 10px;
      color: var(--text-muted);
      cursor: pointer;
    }

    .diff-view-mode-btn.active {
      background: var(--input-bg);
      color: var(--text-main);
      font-weight: 600;
    }

    .diff-split-wrapper {
      display: grid;
      grid-template-columns: 1fr 1fr;
      overflow-x: auto;
      max-height: 420px;
      border-top: 1px solid var(--border-subtle);
    }

    .diff-pane {
      overflow-y: auto;
      overflow-x: auto;
      background: var(--input-bg);
    }

    .diff-pane-left {
      border-right: 1px solid var(--border-subtle);
    }

    .diff-pane-header {
      padding: 4px 8px;
      font-size: 10px;
      font-weight: 600;
      color: var(--text-muted);
      background: var(--card-bg);
      border-bottom: 1px solid var(--border-subtle);
      position: sticky;
      top: 0;
      z-index: 2;
    }

    .diff-table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }

    .diff-table td {
      padding: 1px 4px;
      line-height: 1.45;
      font-family: inherit;
      font-size: 11px;
      vertical-align: top;
      white-space: pre-wrap;
      word-break: break-all;
    }

    .diff-gutter {
      width: 38px;
      min-width: 38px;
      max-width: 38px;
      text-align: right;
      color: var(--text-muted);
      user-select: none;
      border-right: 1px solid var(--border-subtle);
      padding-right: 6px !important;
      opacity: 0.65;
    }

    .diff-content {
      padding-left: 8px !important;
    }

    .diff-row-del {
      background: rgba(248, 81, 73, 0.12);
      color: #ff7b72;
    }

    .diff-row-del .diff-gutter {
      background: rgba(248, 81, 73, 0.22);
      color: #ffa198;
    }

    .diff-row-add {
      background: rgba(46, 160, 67, 0.12);
      color: #7ee787;
    }

    .diff-row-add .diff-gutter {
      background: rgba(46, 160, 67, 0.22);
      color: #56d364;
    }

    .diff-row-empty {
      background: rgba(120, 120, 120, 0.05);
    }

    .diff-row-empty .diff-gutter {
      background: rgba(120, 120, 120, 0.08);
    }

    .diff-hunk-header {
      background: var(--hover-subtle);
      color: var(--text-muted);
      font-style: italic;
      font-size: 10px;
      padding: 3px 8px;
      border-top: 1px solid var(--border-subtle);
      border-bottom: 1px solid var(--border-subtle);
    }

    .diff-unified-wrapper {
      max-height: 420px;
      overflow-y: auto;
      overflow-x: auto;
    }

    .diff-unified-table {
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }

    .diff-unified-table td {
      padding: 1px 4px;
      line-height: 1.45;
      font-size: 11px;
      font-family: inherit;
      white-space: pre-wrap;
      word-break: break-all;
    }

    .diff-unified-gutter-old, .diff-unified-gutter-new {
      width: 36px;
      min-width: 36px;
      max-width: 36px;
      text-align: right;
      color: var(--text-muted);
      user-select: none;
      opacity: 0.65;
    }

    .diff-unified-marker {
      width: 16px;
      min-width: 16px;
      max-width: 16px;
      text-align: center;
      user-select: none;
      font-weight: 600;
    }

    .empty-state {
      padding: 32px 16px;
      text-align: center;
      color: var(--text-muted);
      font-size: 11px;
    }

    /* Codebase Intelligence Layout */
    .scan-progress-card {
      background: var(--card-bg);
      border: 1px solid var(--border-subtle);
      border-radius: 3px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .progress-bar-bg {
      background: var(--input-bg);
      border: 1px solid var(--border-subtle);
      border-radius: 2px;
      height: 6px;
      overflow: hidden;
      position: relative;
    }

    .progress-bar-fill {
      background: var(--accent);
      height: 100%;
      transition: width 0.3s ease;
    }

    .quiet-warning {
      color: var(--warning-color);
      font-size: 11px;
      display: flex;
      align-items: center;
      gap: 6px;
      padding-top: 2px;
    }

    .contract-coverage-container {
      margin-top: 10px;
      padding-top: 8px;
      border-top: 1px solid var(--border-subtle);
    }

    .contract-coverage-summary-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      user-select: none;
      padding: 6px 10px;
      background: var(--input-bg);
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      font-size: 11px;
      transition: background 0.15s ease, border-color 0.15s ease;
    }

    .contract-coverage-summary-bar:hover {
      background: var(--btn-secondary-hover, rgba(255, 255, 255, 0.06));
      border-color: var(--primary-color, #007acc);
    }

    .codebase-container {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .table-container {
      overflow-x: auto;
    }

    table.data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
      text-align: left;
    }

    table.data-table th {
      padding: 8px 10px;
      background: var(--input-bg);
      border-bottom: 1px solid var(--border-subtle);
      color: var(--text-muted);
      font-weight: 600;
      text-transform: uppercase;
      font-size: 10px;
      letter-spacing: 0.4px;
    }

    table.data-table td {
      padding: 8px 10px;
      border-bottom: 1px solid var(--border-subtle);
      vertical-align: middle;
    }

    table.data-table tr:hover {
      background: var(--hover-subtle);
    }

    .file-link {
      color: var(--vscode-textLink-foreground, #3794FF);
      cursor: pointer;
      text-decoration: underline;
      background: none;
      border: none;
      font-family: inherit;
      font-size: inherit;
      padding: 0;
    }

    .file-link:hover {
      color: var(--vscode-textLink-activeForeground, #5EAAFF);
    }

    /* API Dependency Graph Styles */
    .graph-toolbar .filter-btn {
      font-size: 10px;
      padding: 2px 7px;
    }
    .graph-node {
      cursor: pointer;
    }
    .graph-node rect {
      transition: stroke 0.15s, fill 0.15s, filter 0.15s;
    }
    .graph-node:hover rect {
      filter: brightness(1.25);
    }
    .graph-node.selected rect {
      stroke: #007ACC !important;
      stroke-width: 2.5px !important;
      filter: drop-shadow(0 0 6px rgba(0, 122, 204, 0.6));
    }
    .graph-node.dimmed {
      opacity: 0.22;
    }
    .graph-edge {
      fill: none;
      transition: stroke-width 0.15s, opacity 0.15s;
    }
    .graph-edge.calls {
      stroke: #4FC1FF;
      stroke-width: 1.5px;
      opacity: 0.7;
    }
    .graph-edge.belongs_to {
      stroke: #9DCDFE;
      stroke-width: 1.5px;
      opacity: 0.6;
    }
    .graph-edge.validated_by {
      stroke: #DCDCAA;
      stroke-width: 1.5px;
      opacity: 0.75;
    }
    .graph-edge.breaking {
      stroke: var(--error-color) !important;
      stroke-width: 2px;
      opacity: 0.95;
    }
    .graph-edge.drift {
      stroke: var(--warning-color) !important;
      stroke-width: 2px;
      opacity: 0.9;
    }
    .graph-edge.highlighted {
      stroke-width: 2.5px !important;
      opacity: 1 !important;
    }
    .graph-edge.dimmed {
      opacity: 0.08 !important;
    }
  </style>
</head>
<body>
  <div class="dashboard-container">
    <!-- Header -->
    <header class="dashboard-header">
      <div class="brand-title">
        <h1>Dependency Guardian</h1>
        <span class="brand-subtitle">API contract drift detection and repository intelligence</span>
      </div>
      <div class="header-actions">
        <div id="detectorStatusBadge" class="status-indicator">
          <span id="detectorDot" class="status-dot"></span>
          <span id="detectorText">Detector: Idle</span>
        </div>
        <div id="statusBadge" class="status-indicator">
          <span id="statusDot" class="status-dot"></span>
          <span id="statusText">Checking backend...</span>
        </div>
        <button class="btn btn-secondary" id="btnAssistant" onclick="openChat()" data-action="openChat">Assistant</button>
        <button class="btn btn-secondary" id="btnRefresh" onclick="refreshDashboard()" data-action="refresh">Refresh ↻</button>
      </div>
    </header>

    <!-- Global Toast Banner -->
    <div id="dashboardToast" class="dashboard-toast" style="display: none; position: fixed; bottom: 20px; right: 24px; padding: 10px 16px; border-radius: 4px; font-size: 11px; z-index: 99999; box-shadow: 0 4px 12px rgba(0,0,0,0.4); max-width: 420px; border: 1px solid var(--border-subtle);"></div>

    <!-- Offline Warning Notice -->
    <div id="offlineNotice" class="offline-banner" style="display: none;">
      <div class="banner-text">
        <strong>Backend Service Offline</strong>
        <p id="offlineReason">Unable to connect to backend endpoint.</p>
      </div>
      <div class="banner-buttons">
        <button class="btn btn-secondary" onclick="setupEnv()" data-action="setupEnv">Check Environment</button>
        <button class="btn btn-secondary" onclick="refreshDashboard()" data-action="refresh">Retry Connection</button>
      </div>
    </div>

    <!-- Summary Metrics -->
    <div class="metrics-grid">
      <div class="metric-card">
        <div id="metricServices" class="metric-num">0</div>
        <div class="metric-label">Dependencies Monitored</div>
      </div>
      <div class="metric-card">
        <div id="metricEndpoints" class="metric-num">0</div>
        <div class="metric-label">Endpoints Discovered</div>
      </div>
      <div class="metric-card">
        <div id="metricChanges" class="metric-num">0</div>
        <div class="metric-label">Contract Drift Incidents</div>
      </div>
      <div class="metric-card">
        <div id="metricBreaking" class="metric-num">0</div>
        <div class="metric-label">Breaking Changes</div>
      </div>
      <div class="metric-card">
        <div id="metricCoverage" class="metric-num">0%</div>
        <div class="metric-label">API Test Coverage</div>
      </div>
      <div class="metric-card">
        <div id="metricRepairs" class="metric-num">0</div>
        <div class="metric-label">Repair Proposals (<span id="metricApproved">0</span> Approved)</div>
      </div>
      <div class="metric-card">
        <div id="metricBaseline" class="metric-num">None</div>
        <div class="metric-label">Active Baseline (<span id="metricBaselineTag">None</span>)</div>
      </div>
      <div class="metric-card">
        <div id="metricScans" class="metric-num">0</div>
        <div class="metric-label">Scan Runs Recorded</div>
      </div>
    </div>

    <!-- Actions & Toolbar -->
    <div class="toolbar-row">
      <div class="toolbar-left">
        <button class="btn btn-primary" id="btnRunAnalysis" onclick="runAnalysis()" data-action="runAnalysis" title="Execute complete unified analysis: Codebase AST Scan + Contract Drift Detection + Safe Live Validation">▶ Run Analysis</button>
        <button class="btn btn-secondary" id="btnValidateApis" onclick="validateExternalApis()" data-action="validateApis" title="Execute safe read-only HTTP probes to validate live endpoints against contract">Validate External APIs</button>
        <button class="btn btn-secondary" id="btnRunDetection" onclick="runDetection()" data-action="runDetection">Contract Drift</button>
        <button class="btn btn-secondary" id="btnScanCodebase" onclick="triggerScan()" data-action="scanCodebase">Scan Codebase</button>
        <button class="btn btn-secondary" id="btnCreateBaseline" onclick="createBaseline()" data-action="createBaseline">Baseline</button>
        <button class="btn btn-secondary" id="btnSetupEnv" onclick="setupEnv()" data-action="setupEnv">Environment</button>
      </div>
      <div class="toolbar-right">
        <div class="mode-selector-wrapper">
          <span class="mode-label">Mode:</span>
          <div class="mode-selector" role="radiogroup" aria-label="Detection Mode">
            <button class="mode-btn active" id="modeBtnAlgorithmic" onclick="setDetectionMode('algorithmic')" data-action="setMode" data-mode="algorithmic" title="Algorithmic: Fast, deterministic AST schema diffing without AI models">
              <span class="mode-dot"></span> Algorithmic
            </button>
            <button class="mode-btn" id="modeBtnHybrid" onclick="setDetectionMode('hybrid')" data-action="setMode" data-mode="hybrid" title="Hybrid: Deterministic detection augmented with AI explanation and repair advice">
              <span class="mode-dot"></span> Hybrid
            </button>
            <button class="mode-btn" id="modeBtnAi" onclick="setDetectionMode('ai')" data-action="setMode" data-mode="ai" title="AI: Pure AI reasoning for breaking changes and contract drift">
              <span class="mode-dot"></span> AI
            </button>
          </div>
          <div id="aiModelBadge" class="ai-model-badge" title="AI Model Status">
            <span class="status-dot" id="aiModelDot"></span>
            <span id="aiModelText">Checking AI model...</span>
          </div>
        </div>
        <div class="tab-bar">
          <button class="tab-btn active" id="tabBtnDrift" onclick="switchTab('drift')" data-action="switchTab" data-tab="drift">Incidents &amp; Findings</button>
          <button class="tab-btn" id="tabBtnBaselines" onclick="switchTab('baselines')" data-action="switchTab" data-tab="baselines">Baselines</button>
          <button class="tab-btn" id="tabBtnScans" onclick="switchTab('scans')" data-action="switchTab" data-tab="scans">Scan History</button>
          <button class="tab-btn" id="tabBtnLive" onclick="switchTab('live')" data-action="switchTab" data-tab="live">External API Validation</button>
          <button class="tab-btn" id="tabBtnCodebase" onclick="switchTab('codebase')" data-action="switchTab" data-tab="codebase">Codebase Intelligence</button>
        </div>
      </div>
    </div>

    <!-- Tab 1: Contract Drift & Repairs -->
    <div id="tabDrift" class="workspace-grid">
      <!-- Left: Incidents List -->
      <div class="panel-box">
        <div class="panel-box-header">
          <h2>Detected Incidents &amp; Findings</h2>
          <span id="incidentsCount" class="count-pill">0</span>
        </div>
        <div class="incident-filter-bar" style="display: flex; gap: 4px; padding: 6px 10px; border-bottom: 1px solid var(--border-subtle); background: var(--input-bg);">
          <button class="filter-btn active" id="filterBtnAll" onclick="setIncidentFilter('all')" data-action="filterIncidents" data-filter="all">All</button>
          <button class="filter-btn" id="filterBtnOpen" onclick="setIncidentFilter('open')" data-action="filterIncidents" data-filter="open">Open</button>
          <button class="filter-btn" id="filterBtnAck" onclick="setIncidentFilter('acknowledged')" data-action="filterIncidents" data-filter="acknowledged">Acknowledged</button>
          <button class="filter-btn" id="filterBtnRes" onclick="setIncidentFilter('resolved')" data-action="filterIncidents" data-filter="resolved">Resolved</button>
          <button class="filter-btn" id="filterBtnReopen" onclick="setIncidentFilter('reopened')" data-action="filterIncidents" data-filter="reopened">Reopened</button>
        </div>
        <div id="incidentsList" class="incident-list">
          <div class="empty-state">No incidents loaded. Run analysis or contract drift detection.</div>
        </div>
      </div>

      <!-- Right: Details & Repair Studio -->
      <div class="panel-box">
        <div class="panel-box-header">
          <h2>Incident Evidence &amp; Repair Studio</h2>
        </div>
        <div id="detailsContainer" class="details-scroll">
          <div id="noSelectionMsg" class="empty-state">
            Select a detected incident on the left to inspect contract changes and backwards-compatible repairs.
          </div>
          <div id="activeDetails" style="display: none; flex-direction: column; gap: 14px;">
            <!-- Rendered dynamically -->
          </div>
        </div>
      </div>
    </div>

    <!-- Tab 2: Persistent Baselines -->
    <div id="tabBaselines" class="codebase-container" style="display: none; flex-direction: column; gap: 14px;">
      <!-- Breadcrumb Navigation Bar: API Inventory -> Baselines -> Compare -->
      <div class="breadcrumb-bar" style="display: flex; gap: 8px; align-items: center; padding: 8px 12px; background: var(--input-bg); border: 1px solid var(--border-subtle); border-radius: 4px; font-size: 11px;">
        <span style="color: var(--text-muted); font-weight: 500;">Workflow:</span>
        <button class="btn btn-secondary btn-sm" onclick="switchTab('codebase')" data-action="switchTab" data-tab="codebase">1. API Inventory</button>
        <span style="color: var(--text-muted);">➔</span>
        <button class="btn btn-secondary btn-sm active" onclick="switchTab('baselines')" data-action="switchTab" data-tab="baselines" style="font-weight: 600; border-color: var(--border-focus);">2. Baselines Reference</button>
        <span style="color: var(--text-muted);">➔</span>
        <button class="btn btn-secondary btn-sm" onclick="scrollToCompareStudio()" data-action="scrollToCompareStudio">3. Compare Snapshots</button>
      </div>

      <!-- Active Baseline Reference Card -->
      <div class="section-card">
        <div class="section-header">
          <span>Active Project Reference Baseline</span>
          <span id="activeBaselineStatusBadge" class="tag approved">Active Reference</span>
        </div>
        <div id="activeBaselineDetails" style="font-size: 11px; line-height: 1.6; color: var(--text-main);">
          No active baseline reference selected. Create or promote a snapshot to establish the source of truth for contract drift detection.
        </div>
        <div style="display: flex; gap: 8px; margin-top: 10px;">
          <button class="btn btn-primary btn-sm" id="btnPromptCreateBaseline" onclick="promptCreateBaseline()" data-action="promptCreateBaseline">+ Snapshot Inventory as New Baseline</button>
          <button class="btn btn-secondary btn-sm" onclick="scrollToCompareStudio()" data-action="scrollToCompareStudio">⇄ Compare Against Active Baseline</button>
        </div>
      </div>

      <!-- Contract Comparison Studio -->
      <div class="section-card" id="baselineCompareStudio">
        <div class="section-header">
          <span>Contract Comparison Studio</span>
          <span class="tag low">Version Diffing</span>
        </div>
        <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px; line-height: 1.5;">
          Select two persisted snapshots to compute exact contract differences, endpoint additions/removals, parameter modifications, and request/response schema changes.
        </div>
        <div style="display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap;">
          <div style="display: flex; flex-direction: column; gap: 4px;">
            <label for="compareBaseSelect" style="font-size: 10px; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">Base Snapshot (Reference):</label>
            <select id="compareBaseSelect" class="form-select" style="min-width: 240px; padding: 5px 8px; background: var(--input-bg); color: var(--text-main); border: 1px solid var(--border-subtle); border-radius: 3px; font-size: 11px; font-family: inherit;"></select>
          </div>
          <div style="display: flex; flex-direction: column; gap: 4px;">
            <label for="compareTargetSelect" style="font-size: 10px; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">Target Snapshot (Comparison):</label>
            <select id="compareTargetSelect" class="form-select" style="min-width: 240px; padding: 5px 8px; background: var(--input-bg); color: var(--text-main); border: 1px solid var(--border-subtle); border-radius: 3px; font-size: 11px; font-family: inherit;"></select>
          </div>
          <button class="btn btn-primary" id="btnCompareSnapshots" onclick="executeSelectedCompare()" data-action="executeSelectedCompare">⇄ Compare Snapshots</button>
        </div>
      </div>

      <!-- Baseline Diff Card -->
      <div id="baselineDiffCard" class="section-card" style="display: none;">
        <div class="section-header">
          <span>Baseline Diff Comparison</span>
          <button class="btn btn-secondary btn-sm" onclick="closeBaselineDiff()" data-action="closeBaselineDiff">Close Diff</button>
        </div>
        <div id="baselineDiffContent"></div>
      </div>

      <!-- Baseline Versions Table -->
      <div class="panel-box">
        <div class="panel-box-header">
          <h2>Baseline Snapshot Versions</h2>
          <span id="baselinesCount" class="count-pill">0</span>
        </div>
        <div id="baselinesTableContainer" style="overflow-x: auto; padding: 10px;">
          <div class="empty-state">No baseline versions recorded.</div>
        </div>
      </div>
    </div>

    <!-- Tab 3: Persistent Scan History -->
    <div id="tabScans" class="codebase-container" style="display: none; flex-direction: column; gap: 14px;">
      <div class="section-card">
        <div class="section-header">
          <span>Persistent Scan Intelligence &amp; Audit History</span>
          <span id="scansCount" class="count-pill">0</span>
        </div>
        <div style="font-size: 11px; line-height: 1.6; color: var(--text-muted);">
          Every local AST codebase scan, contract drift evaluation, and safe API validation run is persisted with detection mode, duration, capabilities executed, and summary counts.
        </div>
      </div>

      <div class="panel-box">
        <div class="panel-box-header">
          <h2>Recent Scan Runs</h2>
        </div>
        <div id="scansTableContainer" style="overflow-x: auto; padding: 10px;">
          <div class="empty-state">No scan history recorded. Run analysis to record scans.</div>
        </div>
      </div>
    </div>

    <!-- Tab 4: External API Intelligence & Live Validation -->
    <div id="tabLive" class="codebase-container" style="display: none;">
      <div class="section-card">
        <div class="section-header">
          <span>External API Intelligence &amp; Safe Live Validation</span>
          <span id="liveTimestamp" style="font-size: 10px; color: var(--text-muted);">Not validated yet</span>
        </div>
        <div style="font-size: 11px; line-height: 1.6; color: var(--text-main);" id="liveSummaryDetails">
          Safe, read-only HTTP validation against external endpoints configured in <code>dependency-guardian.yml</code>.<br>
          Enforces read-only operations (GET/HEAD/OPTIONS), bounded timeouts, and strict credential redaction.
        </div>
      </div>

      <!-- Live Probe Metrics -->
      <div class="metrics-grid" id="liveMetricsGrid">
        <div class="metric-card">
          <div id="metricLiveProbes" class="metric-num">0</div>
          <div class="metric-label">Probes Executed</div>
        </div>
        <div class="metric-card">
          <div id="metricLiveReachable" class="metric-num">0</div>
          <div class="metric-label">Reachable (2xx)</div>
        </div>
        <div class="metric-card">
          <div id="metricLiveMismatches" class="metric-num">0</div>
          <div class="metric-label">Contract Mismatches</div>
        </div>
        <div class="metric-card">
          <div id="metricLiveAuthFail" class="metric-num">0</div>
          <div class="metric-label">Auth Failures</div>
        </div>
        <div class="metric-card">
          <div id="metricLiveUnreachable" class="metric-num">0</div>
          <div class="metric-label">Unreachable / Offline</div>
        </div>
        <div class="metric-card">
          <div id="metricLiveBlocked" class="metric-num">0</div>
          <div class="metric-label">Security Blocked</div>
        </div>
      </div>

      <!-- Live Probes Table -->
      <div class="section-card">
        <div class="section-header">
          <span>Executed Endpoint Probes</span>
          <span id="liveProbesCount" class="count-pill">0</span>
        </div>
        <div class="table-container" id="liveProbesTableContainer">
          <div class="empty-state">No live validation probes executed yet. Click <strong>Validate External APIs</strong> to run safe probes.</div>
        </div>
      </div>
    </div>

    <!-- Tab 2: Codebase Intelligence & Inventory -->
    <div id="tabCodebase" class="codebase-container" style="display: none;">
      <!-- Live Progress Card -->
      <div id="scanProgressCard" class="scan-progress-card" style="display: none;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="status-dot running" id="scanProgressDot"></span>
            <strong id="scanPhaseTitle" style="font-size: 12px;">Initializing Repository Intelligence Scan...</strong>
          </div>
          <div style="display: flex; align-items: center; gap: 10px;">
            <span id="scanElapsedTimer" style="font-size: 11px; color: var(--text-muted);">0s elapsed</span>
            <button class="btn btn-secondary" style="padding: 2px 8px; font-size: 11px;" onclick="cancelScan()">Cancel Scan</button>
          </div>
        </div>
        <div class="progress-bar-bg">
          <div id="scanProgressBar" class="progress-bar-fill" style="width: 5%;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: var(--text-muted);">
          <span id="scanProgressMessage">Preparing fast repository inventory...</span>
          <span id="scanFileCounter"></span>
        </div>
        <div id="scanQuietWarning" class="quiet-warning" style="display: none;">
          <span>⚠ Scan active: performing deep AST framework analysis / network checks...</span>
        </div>
      </div>

      <div class="section-card" id="codebaseSummaryCard">
        <div class="section-header">
          <span>Repository Intelligence Overview</span>
          <span id="scanTimestamp" style="font-size: 10px; color: var(--text-muted);">Not scanned yet</span>
        </div>
        <div style="font-size: 11px; line-height: 1.6; color: var(--text-main);" id="codebaseSummaryDetails">
          Click <strong>Scan Codebase &amp; Inventory</strong> to inspect routes, manifest dependencies, test coverage gaps, and spec discrepancies.
        </div>
        <!-- Contract Coverage Summary Footer (Single-line collapsed by default) -->
        <div id="contractCoverageContainer" class="contract-coverage-container">
          <div class="contract-coverage-summary-bar" id="contractCoverageSummaryBar" onclick="toggleContractCoverage()" title="Click to view API contract coverage breakdown and affected consumers">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span id="coverageToggleIcon" style="font-size: 10px; transition: transform 0.2s;">▶</span>
              <span style="font-weight: 600;">Contract Coverage</span>
              <span id="coverageSummaryPill" class="tag low">No scan data available</span>
            </div>
            <div id="coverageQuickStats" style="display: flex; gap: 6px; font-size: 10px;"></div>
          </div>
          <div id="contractCoverageDetails" style="display: none; margin-top: 10px; border-top: 1px solid var(--border-subtle); padding-top: 10px;">
            <div id="contractCoverageFeedback" style="display: none; font-size: 11px; padding: 4px 8px; margin-bottom: 8px; border-radius: 3px; background: var(--input-bg); color: var(--warning-color);"></div>
            <div id="contractCoverageBody"></div>
          </div>
        </div>
      </div>

      <!-- API Dependency Graph Section (Collapsed by Default) -->
      <div class="section-card" id="apiDependencyGraphSection">
        <div class="section-header" style="cursor: pointer; user-select: none;" id="graphHeaderToggle" onclick="toggleDependencyGraph()" data-action="toggleGraph">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span id="graphToggleIcon" style="display: inline-block; transition: transform 0.2s; font-size: 11px;">▶</span>
            <span style="font-weight: 600;">API Dependency Graph</span>
            <span class="count-pill" id="graphNodeCountBadge">0 nodes</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <div id="graphSummaryPills" style="display: flex; gap: 5px; font-size: 10px;">
              <span id="pillGraphServices" class="tag low">Services: 0</span>
              <span id="pillGraphEndpoints" class="tag low">Endpoints: 0</span>
              <span id="pillGraphConsumers" class="tag low">Consumers: 0</span>
              <span id="pillGraphContracts" class="tag low">Contracts: 0</span>
              <span id="pillGraphIssues" class="tag breaking" style="display: none;">Issues: 0</span>
            </div>
            <button class="btn btn-secondary btn-sm" id="btnToggleGraph" onclick="event.stopPropagation(); toggleDependencyGraph()" data-action="toggleGraph">▶ Expand Graph</button>
          </div>
        </div>
        <div id="graphContainerBody" style="display: none; margin-top: 10px;">
          <!-- Toolbar -->
          <div class="graph-toolbar" style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; padding: 8px 10px; background: var(--input-bg); border: 1px solid var(--border-subtle); border-radius: 4px; margin-bottom: 10px;">
            <div style="display: flex; align-items: center; gap: 6px; flex: 1; min-width: 260px;">
              <input type="text" id="graphSearchInput" placeholder="Filter graph (e.g. /health, client.py, localhost)..." style="width: 100%; max-width: 320px; padding: 4px 8px; font-size: 11px; background: var(--bg); color: var(--text-main); border: 1px solid var(--border-subtle); border-radius: 3px;" oninput="onGraphSearchInput(this.value)" />
            </div>
            <div style="display: flex; align-items: center; gap: 4px;">
              <span style="font-size: 10px; color: var(--text-muted); margin-right: 2px;">Type:</span>
              <button class="filter-btn active" id="gTypeAll" onclick="setGraphTypeFilter('all')" data-action="gType" data-type="all">All</button>
              <button class="filter-btn" id="gTypeEndpoints" onclick="setGraphTypeFilter('endpoint')" data-action="gType" data-type="endpoint">Endpoints</button>
              <button class="filter-btn" id="gTypeServices" onclick="setGraphTypeFilter('service')" data-action="gType" data-type="service">Services</button>
              <button class="filter-btn" id="gTypeFiles" onclick="setGraphTypeFilter('source_file')" data-action="gType" data-type="source_file">Sources</button>
              <button class="filter-btn" id="gTypeContracts" onclick="setGraphTypeFilter('contract')" data-action="gType" data-type="contract">Contracts</button>
            </div>
            <div style="display: flex; align-items: center; gap: 4px;">
              <span style="font-size: 10px; color: var(--text-muted); margin-right: 2px;">Status:</span>
              <button class="filter-btn active" id="gStatusAll" onclick="setGraphStatusFilter('all')" data-action="gStatus" data-status="all">All</button>
              <button class="filter-btn" id="gStatusIssues" onclick="setGraphStatusFilter('issues')" data-action="gStatus" data-status="issues">Issues</button>
              <button class="filter-btn" id="gStatusClean" onclick="setGraphStatusFilter('clean')" data-action="gStatus" data-status="clean">Clean</button>
              <button class="filter-btn" id="gStatusUnknown" onclick="setGraphStatusFilter('unknown')" data-action="gStatus" data-status="unknown">Unknown</button>
            </div>
            <div style="display: flex; align-items: center; gap: 4px;">
              <button class="btn btn-secondary btn-sm" onclick="graphZoom(1.2)" title="Zoom in">+</button>
              <button class="btn btn-secondary btn-sm" onclick="graphZoom(0.8)" title="Zoom out">-</button>
              <button class="btn btn-secondary btn-sm" onclick="graphFitView()" title="Fit all nodes to view">Fit</button>
              <button class="btn btn-secondary btn-sm" onclick="graphResetView()" title="Reset zoom and pan">Reset</button>
              <button class="btn btn-secondary btn-sm" onclick="requestRefreshGraph()" title="Refresh graph from latest scan">↻</button>
            </div>
          </div>

          <!-- Main Layout: SVG Canvas + Node Details Drawer -->
          <div style="display: flex; gap: 12px; height: 500px; border: 1px solid var(--border-subtle); border-radius: 4px; overflow: hidden; background: var(--input-bg);">
            <!-- Canvas Wrapper -->
            <div id="graphCanvasWrapper" style="flex: 1; height: 100%; position: relative; overflow: hidden; cursor: grab;" onmousedown="onGraphMouseDown(event)" onwheel="onGraphWheel(event)">
              <svg id="dependencyGraphSvg" width="100%" height="100%" style="display: block;">
                <defs>
                  <marker id="arrow-calls" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                    <path d="M 0 1 L 9 5 L 0 9 z" fill="#4fc1ff" opacity="0.8" />
                  </marker>
                  <marker id="arrow-belongs" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                    <path d="M 0 1 L 9 5 L 0 9 z" fill="#9cdcfe" opacity="0.7" />
                  </marker>
                  <marker id="arrow-validated" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                    <path d="M 0 1 L 9 5 L 0 9 z" fill="#dcdcaa" opacity="0.8" />
                  </marker>
                  <marker id="arrow-breaking" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
                    <path d="M 0 1 L 9 5 L 0 9 z" fill="#f14c4c" opacity="0.9" />
                  </marker>
                </defs>
                <g id="graphViewportGroup" transform="translate(20, 20) scale(1)">
                  <g id="graphEdgesLayer"></g>
                  <g id="graphNodesLayer"></g>
                </g>
              </svg>
              <!-- Zoom Indicator Badge -->
              <div id="graphZoomBadge" style="position: absolute; bottom: 8px; left: 8px; font-size: 10px; color: var(--text-muted); background: rgba(0,0,0,0.6); padding: 2px 6px; border-radius: 3px; pointer-events: none;">100%</div>
              <!-- Empty State Overlay -->
              <div id="graphEmptyOverlay" style="display: none; position: absolute; inset: 0; align-items: center; justify-content: center; flex-direction: column; gap: 8px; background: rgba(30,30,30,0.85);">
                <span style="font-weight: 600; color: var(--text-main);">No API Dependency Graph Available</span>
                <span style="font-size: 11px; color: var(--text-muted);">Run Codebase Scan or Contract Drift Detection to build the live graph.</span>
                <button class="btn btn-primary btn-sm" onclick="triggerScan()">Scan Codebase Now</button>
              </div>
            </div>

            <!-- Details Drawer -->
            <div id="graphNodeDetailsDrawer" style="width: 320px; height: 100%; border-left: 1px solid var(--border-subtle); background: var(--card-bg); padding: 12px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px;">
              <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.5px;">Node Inspector</div>
              <div id="graphDrawerEmpty" style="font-size: 11px; color: var(--text-muted); line-height: 1.5; margin-top: 20px; text-align: center;">
                Click any node in the graph to inspect routes, callers, target services, and contract validation status.
              </div>
              <div id="graphDrawerContent" style="display: none; flex-direction: column; gap: 10px;">
                <!-- Rendered dynamically -->
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Endpoints Discovered -->
      <div class="section-card">
        <div class="section-header">
          <span>Discovered API Endpoints</span>
          <span id="endpointsCount" class="count-pill">0</span>
        </div>
        <div class="table-container" id="endpointsTableContainer">
          <div class="empty-state">No endpoints discovered. Run codebase scan.</div>
        </div>
      </div>

      <!-- Spec Discrepancies -->
      <div class="section-card">
        <div class="section-header">
          <span>Specification Discrepancies (Undocumented / Ghost Routes)</span>
          <span id="discrepanciesCount" class="count-pill">0</span>
        </div>
        <div id="discrepanciesList">
          <div class="empty-state">No discrepancies discovered.</div>
        </div>
      </div>

      <!-- Dependencies & Integrations -->
      <div class="section-card">
        <div class="section-header">
          <span>Dependencies &amp; External Integrations</span>
          <span id="depsCount" class="count-pill">0</span>
        </div>
        <div id="depsAndIntegrationsList">
          <div class="empty-state">No dependency data loaded.</div>
        </div>
      </div>

      <!-- Documentation Deliverables -->
      <div class="section-card">
        <div class="section-header">
          <span>Generated Documentation Deliverables</span>
        </div>
        <div id="deliverablesList" style="font-size: 11px; line-height: 1.6;">
          <div class="empty-state">Documentation deliverables will appear here after scanning.</div>
        </div>
      </div>
    </div>

  </div>

  <script>
    window.onerror = function(msg, url, line, col, err) {
      console.error("Guardian Dashboard Webview Error:", msg, "at line", line, err);
      try {
        if (typeof vscode !== 'undefined' && vscode.postMessage) {
          vscode.postMessage({ command: "webviewError", error: String(msg) + " at line " + line });
        }
      } catch(e) {}
    };

    const vscode = acquireVsCodeApi();

    function showToast(msg, type) {
      const toast = document.getElementById('dashboardToast');
      if (!toast) return;
      toast.textContent = msg;
      toast.className = 'dashboard-toast ' + (type || 'info');
      toast.style.display = 'block';
      setTimeout(() => { toast.style.display = 'none'; }, 4000);
    }

    let currentTab = 'drift';
    let state = {
      services: [],
      changes: [],
      repairs: [],
      inventory: null,
      driftResult: null,
      liveValidation: null,
      detectionConfig: null,
      metrics: null,
      selectedChange: null,
      impacts: [],
      currentRepair: null,
      validation: null,
      events: [],
      baselines: [],
      activeBaseline: null,
      scanHistory: [],
      incidentFilter: 'all',
      diffViewMode: 'split',
      selectedDiffFileIndex: 0,
      staleness: { isStale: false },
      changeSet: [],
      actionPending: null,
      repairError: null,
      graphData: null,
      graphExpanded: false,
      graphSelectedNodeId: null,
      graphSearchQuery: '',
      graphTypeFilter: 'all',
      graphStatusFilter: 'all',
      graphPan: { x: 20, y: 20 },
      graphScale: 1.0,
      graphIsPanning: false,
      graphPanStart: { x: 0, y: 0 }
    };

    function switchTab(tab) {
      currentTab = tab;
      const tabs = [
        { id: 'drift', el: 'tabDrift', btn: 'tabBtnDrift', display: 'grid' },
        { id: 'baselines', el: 'tabBaselines', btn: 'tabBtnBaselines', display: 'flex' },
        { id: 'scans', el: 'tabScans', btn: 'tabBtnScans', display: 'flex' },
        { id: 'live', el: 'tabLive', btn: 'tabBtnLive', display: 'flex' },
        { id: 'codebase', el: 'tabCodebase', btn: 'tabBtnCodebase', display: 'flex' }
      ];

      tabs.forEach(t => {
        const el = document.getElementById(t.el);
        const btn = document.getElementById(t.btn);
        if (el) el.style.display = t.id === tab ? t.display : 'none';
        if (btn) btn.classList.toggle('active', t.id === tab);
      });
    }

    function setDetectionMode(mode) {
      vscode.postMessage({ command: 'setDetectionMode', mode });
    }

    function updateModeSelector(cfg) {
      if (!cfg) return;
      const mode = cfg.mode || 'algorithmic';
      const mAlg = document.getElementById('modeBtnAlgorithmic');
      const mHyb = document.getElementById('modeBtnHybrid');
      const mAi = document.getElementById('modeBtnAi');
      if (mAlg) mAlg.classList.toggle('active', mode === 'algorithmic');
      if (mHyb) mHyb.classList.toggle('active', mode === 'hybrid');
      if (mAi) mAi.classList.toggle('active', mode === 'ai');

      const dot = document.getElementById('aiModelDot');
      const text = document.getElementById('aiModelText');
      if (dot && text) {
        if (cfg.aiModelReady) {
          dot.className = 'status-dot online';
          text.textContent = cfg.aiModelMessage || (cfg.ollamaModel + ' Ready');
        } else if (mode === 'algorithmic') {
          dot.className = 'status-dot';
          text.textContent = 'AST Mode (Offline)';
        } else {
          dot.className = 'status-dot offline';
          text.textContent = cfg.aiModelMessage || 'AI Offline (Fallback Active)';
        }
      }
    }

    function runAnalysis() {
      vscode.postMessage({ command: 'runAnalysis' });
    }

    function validateExternalApis() {
      switchTab('live');
      vscode.postMessage({ command: 'validateExternalApis' });
    }

    function runDetection() {
      vscode.postMessage({ command: 'runDetection' });
    }

    function triggerScan() {
      switchTab('codebase');
      updateScanProgress({
        phase: 'starting',
        message: 'Initializing repository intelligence scan...',
        elapsedSeconds: 0
      });
      vscode.postMessage({ command: 'scan' });
    }

    function cancelScan() {
      vscode.postMessage({ command: 'cancelScan' });
    }

    const phaseNames = {
      'starting': 'Initializing Repository Intelligence Scan',
      'discovering_files': 'Discovering & Categorizing Files',
      'inspecting_dependencies': 'Inspecting Dependencies & Integrations',
      'analyzing_source': 'Analyzing Source Code & AST',
      'checking_specifications': 'Reconciling OpenAPI Specifications',
      'evaluating_tests': 'Evaluating Test Suite Coverage',
      'generating_reports': 'Generating Inventory Deliverables',
      'completed': 'Repository Intelligence Scan Complete'
    };

    const phasePct = {
      'starting': 5,
      'discovering_files': 15,
      'inspecting_dependencies': 35,
      'analyzing_source': 60,
      'checking_specifications': 75,
      'evaluating_tests': 85,
      'generating_reports': 95,
      'completed': 100
    };

    function updateScanProgress(prog) {
      const card = document.getElementById('scanProgressCard');
      if (!card) return;
      card.style.display = 'flex';

      const phase = (prog && prog.phase) || 'starting';
      const title = phaseNames[phase] || ('Scanning: ' + phase);
      document.getElementById('scanPhaseTitle').textContent = title;

      let pct = phasePct[phase] || 20;
      if (prog && prog.filesProcessed && prog.totalFiles && prog.totalFiles > 0) {
        pct = Math.min(98, Math.max(pct, Math.round((prog.filesProcessed / prog.totalFiles) * 100)));
      }
      const progressBar = document.getElementById('scanProgressBar');
      progressBar.style.width = pct + '%';
      progressBar.style.background = 'var(--accent)';

      if (prog && prog.message) {
        document.getElementById('scanProgressMessage').textContent = prog.message;
      }

      const counterEl = document.getElementById('scanFileCounter');
      if (prog && prog.filesProcessed && prog.totalFiles) {
        counterEl.textContent = prog.filesProcessed + ' / ' + prog.totalFiles + ' files';
      } else if (prog && prog.filesDiscovered) {
        counterEl.textContent = prog.filesDiscovered + ' files discovered';
      } else {
        counterEl.textContent = '';
      }

      if (prog && prog.elapsedSeconds !== undefined) {
        document.getElementById('scanElapsedTimer').textContent = prog.elapsedSeconds + 's elapsed';
      }

      const warnEl = document.getElementById('scanQuietWarning');
      if (prog && prog.quietWarning) {
        warnEl.style.display = 'flex';
      } else {
        warnEl.style.display = 'none';
      }

      document.getElementById('scanProgressDot').className = 'status-dot running';
    }

    function completeScanProgress(result) {
      updateScanProgress({
        phase: 'completed',
        message: 'Scan completed successfully.',
        elapsedSeconds: parseInt(document.getElementById('scanElapsedTimer').textContent) || 0
      });
      setTimeout(() => {
        const card = document.getElementById('scanProgressCard');
        if (card) card.style.display = 'none';
      }, 2500);
    }

    function failScanProgress(errorMsg) {
      const card = document.getElementById('scanProgressCard');
      if (!card) return;
      document.getElementById('scanPhaseTitle').textContent = 'Repository Scan Failed';
      document.getElementById('scanProgressMessage').textContent = errorMsg || 'An error occurred during scanning.';
      const progressBar = document.getElementById('scanProgressBar');
      progressBar.style.width = '100%';
      progressBar.style.background = 'var(--error-color)';
      document.getElementById('scanQuietWarning').style.display = 'none';
      document.getElementById('scanProgressDot').className = 'status-dot offline';
    }

    function cancelScanProgress() {
      const card = document.getElementById('scanProgressCard');
      if (!card) return;
      document.getElementById('scanPhaseTitle').textContent = 'Scan Canceled';
      document.getElementById('scanProgressMessage').textContent = 'Scan was canceled by user.';
      const progressBar = document.getElementById('scanProgressBar');
      progressBar.style.width = '100%';
      progressBar.style.background = 'var(--text-muted)';
      document.getElementById('scanQuietWarning').style.display = 'none';
      document.getElementById('scanProgressDot').className = 'status-dot';
      setTimeout(() => {
        if (card) card.style.display = 'none';
      }, 3000);
    }

    function createBaseline() {
      vscode.postMessage({ command: 'createBaseline' });
    }

    function setupEnv() {
      vscode.postMessage({ command: 'setupEnvironment' });
    }

    function openChat() {
      vscode.postMessage({ command: 'openChat' });
    }

    function refreshDashboard() {
      vscode.postMessage({ command: 'refresh' });
    }

    function setScenario(scenario) {
      vscode.postMessage({ command: 'setScenario', scenario });
    }

    function resetDemo() {
      vscode.postMessage({ command: 'resetDemo' });
    }

    function selectIncident(changeId) {
      state.repairError = null;
      vscode.postMessage({ command: 'selectChange', changeId });
    }

    function proposeRepair(changeId) {
      state.repairError = null;
      vscode.postMessage({ command: 'proposeRepair', changeId });
    }

    function reviewRepair(repairId, changeId) {
      vscode.postMessage({ command: 'reviewRepair', repairId, changeId });
    }

    function approveRepair(repairId) {
      vscode.postMessage({ command: 'approveRepair', repairId });
    }

    function rejectRepair(repairId) {
      vscode.postMessage({ command: 'requestRejectRepair', repairId: repairId });
    }

    function applyRepair(repairId) {
      vscode.postMessage({ command: 'applyRepair', repairId });
    }

    function validateRepair(repairId) {
      vscode.postMessage({ command: 'validateRepair', repairId });
    }

    function rollbackRepair(repairId) {
      vscode.postMessage({ command: 'rollbackRepair', repairId });
    }

    function openNativeDiff(repairId) {
      vscode.postMessage({ command: 'reviewRepair', repairId, changeId: state.selectedChange ? state.selectedChange.id : undefined });
    }

    function setDiffViewMode(mode) {
      state.diffViewMode = mode;
      renderDetails();
    }

    function selectDiffFile(index) {
      state.selectedDiffFileIndex = index;
      renderDetails();
    }

    function syncDiffScroll(source, targetId) {
      const target = document.getElementById(targetId);
      if (target && !source._isSyncing) {
        target._isSyncing = true;
        target.scrollTop = source.scrollTop;
        target.scrollLeft = source.scrollLeft;
        setTimeout(() => { target._isSyncing = false; }, 30);
      }
    }

    function openFile(filePath, lineNumber) {
      vscode.postMessage({ command: 'openFile', filePath, lineNumber });
    }

    window.addEventListener('message', (event) => {
      const msg = event.data;
      switch (msg.type) {
        case 'initialData':
          state.services = msg.services || [];
          state.changes = msg.changes || [];
          state.repairs = msg.repairs || [];
          state.metrics = msg.metrics || null;
          state.baselines = msg.baselines || [];
          state.activeBaseline = msg.activeBaseline || null;
          state.scanHistory = msg.scanHistory || [];
          if (msg.detectionConfig) {
            state.detectionConfig = msg.detectionConfig;
            updateModeSelector(msg.detectionConfig);
          }
          handleOnlineState(msg.health);
          renderMetrics();
          renderIncidents();
          renderBaselines();
          renderScanHistory();
          break;
        case 'backendOffline':
          if (msg.detectionConfig) {
            state.detectionConfig = msg.detectionConfig;
            updateModeSelector(msg.detectionConfig);
          }
          handleOfflineState(msg.error, msg.url);
          break;
        case 'agentStateEvent':
          handleAgentState(msg);
          break;
        case 'codebaseScanResult':
          state.inventory = msg.inventory;
          renderMetrics();
          renderCodebase();
          switchTab('codebase');
          break;
        case 'dependencyGraphData':
          state.graphData = msg.graph;
          renderDependencyGraph(msg.graph);
          break;
        case 'showDependencyGraph':
          switchTab('codebase');
          expandDependencyGraph();
          break;
        case 'driftResult':
          state.driftResult = msg.driftResult;
          state.changes = msg.changes || [];
          renderMetrics();
          renderIncidents();
          if (state.changes.length > 0) {
            selectIncident(state.changes[0].id);
          }
          switchTab('drift');
          break;
        case 'liveValidationResult':
          state.liveValidation = msg.report;
          if (msg.report && msg.report.findings && msg.report.findings.length > 0) {
            const liveChanges = msg.report.findings.map(f => ({
              id: f.id,
              scan_id: f.id,
              dependency_id: f.path || 'external-api',
              probe_id: (f.method || 'GET') + ' ' + f.path,
              change_type: f.rule_id,
              severity: f.severity === 'critical' || f.severity === 'high' ? 'high' : (f.severity === 'medium' ? 'medium' : 'low'),
              evidence: {
                ...f.evidence,
                message: f.message,
                rule_id: f.rule_id,
                compatibility: f.compatibility,
                provenance: 'live_probe',
                confidence: f.confidence !== undefined ? f.confidence : 1.0,
                recommended_action: f.recommended_action,
              },
              status: f.compatibility,
              created_at: new Date().toISOString(),
              affected_files: [],
              affected_workflows: [],
            }));
            const existingIds = new Set(state.changes.map(c => c.id));
            for (const lc of liveChanges) {
              if (!existingIds.has(lc.id)) {
                state.changes.push(lc);
              }
            }
          }
          renderMetrics();
          renderIncidents();
          renderLiveValidation();
          switchTab('live');
          break;
        case 'changeSelected':
          state.selectedChange = msg.change;
          state.impacts = msg.impacts || [];
          state.repairs = msg.repairs || [];
          state.currentRepair = msg.currentRepair || null;
          state.events = msg.events || [];
          state.validation = null;
          state.staleness = msg.staleness || { isStale: false };
          state.changeSet = msg.changeSet || [];
          state.selectedDiffFileIndex = 0;
          state.actionPending = null;
          renderDetails();
          break;
        case 'baselineCompareResult':
          renderBaselineDiff(msg.diff);
          break;
        case 'repairProposed':
          state.currentRepair = msg.proposal;
          state.actionPending = null;
          state.repairError = null;
          renderDetails();
          break;
        case 'repairApproved':
          state.currentRepair = msg.repair;
          state.actionPending = null;
          renderDetails();
          break;
        case 'repairRejected':
          state.currentRepair = msg.repair;
          state.actionPending = null;
          renderDetails();
          break;
        case 'validationCompleted':
          state.validation = msg.result;
          state.currentRepair = msg.repair;
          state.actionPending = null;
          renderDetails();
          break;
        case 'repairApplied':
        case 'repairRolledBack':
          state.currentRepair = msg.repair;
          state.actionPending = null;
          renderDetails();
          break;
        case 'actionRunning':
          state.actionPending = msg.action;
          renderDetails();
          break;
        case 'actionCancelled':
          state.actionPending = null;
          renderDetails();
          break;
        case 'actionError':
          state.actionPending = null;
          if (msg.action === 'proposeRepair') {
            state.repairError = msg.error || 'Failed to generate repair proposal.';
          }
          renderDetails();
          break;
      }
    });

    function toggleTechEvidence() {
      const box = document.getElementById('techEvidenceBox');
      if (box) {
        box.style.display = box.style.display === 'none' ? 'block' : 'none';
      }
    }

    function renderLiveValidation() {
      const report = state.liveValidation;
      if (!report) return;

      const timeEl = document.getElementById('liveTimestamp');
      if (timeEl) timeEl.textContent = report.timestamp ? new Date(report.timestamp).toLocaleString() : 'Validated';
      const mProbes = document.getElementById('metricLiveProbes');
      if (mProbes) mProbes.textContent = report.total_probes || 0;
      const mReach = document.getElementById('metricLiveReachable');
      if (mReach) mReach.textContent = report.reachable_count || 0;
      const mMismatch = document.getElementById('metricLiveMismatches');
      if (mMismatch) mMismatch.textContent = report.contract_mismatch_count || 0;
      const mAuth = document.getElementById('metricLiveAuthFail');
      if (mAuth) mAuth.textContent = report.auth_failure_count || 0;
      const mUnreach = document.getElementById('metricLiveUnreachable');
      if (mUnreach) mUnreach.textContent = report.unreachable_count || 0;
      const mBlocked = document.getElementById('metricLiveBlocked');
      if (mBlocked) mBlocked.textContent = report.security_blocked_count || 0;
      const mCount = document.getElementById('liveProbesCount');
      if (mCount) mCount.textContent = (report.results || []).length;

      const tblContainer = document.getElementById('liveProbesTableContainer');
      if (!tblContainer) return;
      if (!report.results || report.results.length === 0) {
        tblContainer.innerHTML = '<div class="empty-state">No live probe results recorded. Click Validate External APIs to execute safe probes.</div>';
        return;
      }

      tblContainer.innerHTML = \`
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 70px;">Method</th>
              <th>Service</th>
              <th>Status</th>
              <th>HTTP Code</th>
              <th>Latency</th>
              <th>Target URL</th>
              <th>Outcome Details</th>
            </tr>
          </thead>
          <tbody>
            \${report.results.map(r => {
              const statusPillClass = 'probe-status-pill ' + (r.status || 'reachable');
              const methodLower = (r.method || 'get').toLowerCase();
              const detailMsg = r.error_message || (r.findings && r.findings.length > 0 ? r.findings.map(f => f.message).join('; ') : (r.status === 'reachable' ? 'OK' : r.status));
              const isErr = r.status !== 'reachable';
              return \`
                <tr>
                  <td><span class="tag method-\${methodLower}">\${escapeHtml(r.method)}</span></td>
                  <td><strong>\${escapeHtml(r.service_name || 'external')}</strong></td>
                  <td><span class="\${statusPillClass}">\${escapeHtml(r.status)}</span></td>
                  <td>\${r.status_code ? r.status_code : '-'}</td>
                  <td>\${r.latency_ms ? r.latency_ms + 'ms' : '-'}</td>
                  <td style="font-family: monospace; font-size: 10px;">\${escapeHtml(r.url)}</td>
                  <td style="font-size: 10px; color: \${isErr ? 'var(--error-color)' : 'var(--text-muted)'}; font-weight: \${isErr ? '600' : 'normal'};">\${escapeHtml(detailMsg)}</td>
                </tr>
              \`;
            }).join('')}
          </tbody>
        </table>
      \`;
    }

    function handleOnlineState(health) {
      const dot = document.getElementById('statusDot');
      const text = document.getElementById('statusText');
      const notice = document.getElementById('offlineNotice');

      dot.className = 'status-dot online';
      text.textContent = 'Backend Connected';
      notice.style.display = 'none';
    }

    function handleOfflineState(error, url) {
      const dot = document.getElementById('statusDot');
      const text = document.getElementById('statusText');
      const notice = document.getElementById('offlineNotice');
      const reason = document.getElementById('offlineReason');

      dot.className = 'status-dot offline';
      text.textContent = 'Backend Offline';
      notice.style.display = 'flex';
      reason.textContent = error ? error + ' (' + (url || 'unreachable') + ')' : 'Cannot reach ' + url;
    }

    function handleAgentState(event) {
      const dot = document.getElementById('detectorDot');
      const text = document.getElementById('detectorText');
      const capName = event.capability === 'codebase_scan' ? 'Scan' : 'Drift';

      if (event.state === 'running') {
        dot.className = 'status-dot running';
        text.textContent = capName + ': Running...';
        if (event.capability === 'codebase_scan') {
          updateScanProgress(event.progress);
        }
      } else if (event.state === 'succeeded') {
        dot.className = 'status-dot online';
        text.textContent = capName + ': Ready';
        if (event.capability === 'codebase_scan') {
          completeScanProgress(event.codebaseResult);
        }
      } else if (event.state === 'failed') {
        dot.className = 'status-dot offline';
        text.textContent = capName + ': Failed';
        if (event.capability === 'codebase_scan') {
          failScanProgress(event.error);
        }
      } else if (event.state === 'canceled') {
        dot.className = 'status-dot';
        text.textContent = capName + ': Canceled';
        if (event.capability === 'codebase_scan') {
          cancelScanProgress();
        }
      } else {
        dot.className = 'status-dot';
        text.textContent = 'Detector: Idle';
      }
    }

    function renderMetrics() {
      let depsCount = state.services.length;
      let endpointsCount = 0;
      let coverageStr = '0%';

      if (state.inventory) {
        depsCount = state.inventory.dependencies.length || depsCount;
        endpointsCount = state.inventory.endpoints.length;
        coverageStr = (state.inventory.test_coverage.coverage_percentage || 0) + '%';
      }

      let changesCount = state.changes.length;
      let breakingCount = state.changes.filter(c => c.severity === 'high' || c.severity === 'critical' || c.severity === 'blocked').length;

      if (state.driftResult && state.driftResult.summary) {
        changesCount = state.driftResult.summary.total_findings;
        breakingCount = state.driftResult.summary.breaking_count;
      }

      const repairsCount = state.repairs.length;
      const approvedCount = state.repairs.filter(r => r.status === 'approved' || r.status === 'applied').length;

      document.getElementById('metricServices').textContent = depsCount;
      document.getElementById('metricEndpoints').textContent = endpointsCount;
      document.getElementById('metricChanges').textContent = changesCount;
      document.getElementById('metricBreaking').textContent = breakingCount;
      document.getElementById('metricCoverage').textContent = coverageStr;
      document.getElementById('metricRepairs').textContent = repairsCount;
      document.getElementById('metricApproved').textContent = approvedCount;
      document.getElementById('incidentsCount').textContent = changesCount;

      const mBase = document.getElementById('metricBaseline');
      const mBaseTag = document.getElementById('metricBaselineTag');
      if (mBase && mBaseTag) {
        if (state.activeBaseline) {
          mBase.textContent = 'v' + state.activeBaseline.version_number;
          mBaseTag.textContent = state.activeBaseline.version_tag;
        } else {
          mBase.textContent = 'None';
          mBaseTag.textContent = 'No active baseline';
        }
      }

      const mScans = document.getElementById('metricScans');
      if (mScans) {
        mScans.textContent = state.scanHistory.length;
      }
    }

    function setIncidentFilter(filter) {
      state.incidentFilter = filter;
      ['all', 'open', 'acknowledged', 'resolved', 'reopened'].forEach(f => {
        const btn = document.getElementById('filterBtn' + f.charAt(0).toUpperCase() + f.slice(1));
        if (btn) btn.classList.toggle('active', f === filter);
      });
      renderIncidents();
    }

    function renderIncidents() {
      const listEl = document.getElementById('incidentsList');
      if (!state.changes || state.changes.length === 0) {
        listEl.innerHTML = '<div class="empty-state">No incidents detected. All dependencies match baseline contracts.</div>';
        return;
      }

      let filtered = state.changes;
      if (state.incidentFilter && state.incidentFilter !== 'all') {
        filtered = state.changes.filter(c => (c.status || 'open').toLowerCase() === state.incidentFilter);
      }

      if (filtered.length === 0) {
        listEl.innerHTML = '<div class="empty-state">No incidents with status "' + escapeHtml(state.incidentFilter) + '".</div>';
        return;
      }

      listEl.innerHTML = filtered.map((c) => {
        const isSelected = state.selectedChange && state.selectedChange.id === c.id;
        const isBreaking = c.severity === 'high' || c.severity === 'critical' || c.severity === 'blocked';
        const tagClass = isBreaking ? 'breaking' : (c.severity === 'medium' ? 'medium' : 'low');
        const prov = (c.evidence && c.evidence.provenance) || c.provenance || 'contract_diff';
        const provClass = 'provenance-' + prov;
        const provLabel = prov === 'codebase_scanner' ? 'Codebase AST' : (prov === 'static_ast' ? 'Static AST' : (prov === 'live_probe' ? 'Live Probe' : (prov === 'ai_inferred' ? 'AI Inferred' : 'Contract Diff')));
        const status = (c.status || 'open').toLowerCase();
        const statusClass = 'status-' + status;
        const occBadge = (c.occurrence_count && c.occurrence_count > 1) ? ('<span class="tag occurrence">#' + c.occurrence_count + '</span>') : '';

        return \`
          <div class="incident-item \${isSelected ? 'active' : ''}" onclick="selectIncident('\${escapeHtml(c.id)}')" data-action="selectChange" data-change-id="\${escapeHtml(c.id)}">
            <div class="incident-top">
              <span class="incident-name">\${escapeHtml(c.dependency_id)}: \${escapeHtml(c.change_type || c.probe_id)}</span>
              <div style="display: flex; gap: 4px; align-items: center;">
                <span class="tag \${statusClass}">\${escapeHtml(status)}</span>
                \${occBadge}
                <span class="tag \${tagClass}">\${escapeHtml(c.severity)}</span>
              </div>
            </div>
            <div class="incident-sub" style="display: flex; justify-content: space-between; align-items: center;">
              <span>Probe: \${escapeHtml(c.probe_id)}</span>
              <span class="tag \${provClass}">\${provLabel}</span>
            </div>
          </div>
        \`;
      }).join('');
    }

    function renderCodebase() {
      if (!state.inventory) return;
      const inv = state.inventory;
      const meta = inv.metadata;
      const cov = inv.test_coverage;

      document.getElementById('scanTimestamp').textContent = meta.scan_timestamp ? new Date(meta.scan_timestamp).toLocaleString() : 'Scanned';

      const langs = meta.languages_detected.join(', ') || 'None';
      const fws = meta.frameworks_detected.join(', ') || 'None';
      const openapiCount = (meta.openapi_specs_found || []).length;

      document.getElementById('codebaseSummaryDetails').innerHTML = \`
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 8px;">
          <div><strong>Scanned Path:</strong> \${escapeHtml(meta.scanned_path)}</div>
          <div><strong>Languages:</strong> \${escapeHtml(langs)}</div>
          <div><strong>Frameworks:</strong> \${escapeHtml(fws)}</div>
          <div><strong>Files Scanned:</strong> \${meta.total_files_scanned}</div>
        </div>
        <div style="display: flex; gap: 16px; align-items: center; padding-top: 6px; border-top: 1px solid var(--border-subtle);">
          <div><strong>OpenAPI Specs:</strong> \${openapiCount} found</div>
          <div><strong>Discovered Endpoints:</strong> \${inv.endpoints.length}</div>
          <div><strong>Discrepancies:</strong> \${inv.discrepancies.length}</div>
          <div><strong>API Coverage:</strong> \${cov.coverage_percentage}% (\${cov.tested_endpoints}/\${cov.total_endpoints} tested, \${cov.untested_endpoints} gaps)</div>
        </div>
      \`;

      // Endpoints Table
      document.getElementById('endpointsCount').textContent = inv.endpoints.length;
      const tblContainer = document.getElementById('endpointsTableContainer');
      if (inv.endpoints.length === 0) {
        tblContainer.innerHTML = \`
          <div class="empty-state">
            <strong style="color: var(--text-main); display: block; margin-bottom: 4px;">0 Server API Endpoints Declared</strong>
            <div style="color: var(--text-muted); line-height: 1.5;">
              This repository contains client applications or services consuming external APIs rather than declaring server routes.<br>
              Discovered <strong>\${inv.integrations.length}</strong> external service integration(s) and <strong>\${inv.dependencies.length}</strong> manifest dependencies below.
            </div>
          </div>
        \`;
      } else {
        tblContainer.innerHTML = \`
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 70px;">Method</th>
                <th>Route Path</th>
                <th>Handler</th>
                <th>Source Location</th>
                <th>Discovery</th>
                <th>Coverage</th>
              </tr>
            </thead>
            <tbody>
              \${inv.endpoints.map(e => {
                const methodLower = (e.http_method || 'get').toLowerCase();
                const isTested = e.existing_tests && e.existing_tests.length > 0;
                const fileLoc = e.source_file ? (e.line_number ? e.source_file + ':' + e.line_number : e.source_file) : 'N/A';
                return \`
                  <tr>
                    <td><span class="tag method-\${methodLower}">\${escapeHtml(e.http_method)}</span></td>
                    <td><strong>\${escapeHtml(e.route_path)}</strong></td>
                    <td>\${escapeHtml(e.handler_function || 'anonymous')}</td>
                    <td>
                      \${e.source_file ? \`<button class="file-link" onclick="openFile('\${escapeHtml(e.source_file)}', \${e.line_number || 1})">\${escapeHtml(fileLoc)}</button>\` : 'N/A'}
                    </td>
                    <td>\${escapeHtml(e.discovery_method)}</td>
                    <td><span class="tag \${isTested ? 'approved' : 'medium'}">\${isTested ? 'Tested' : 'Untested'}</span></td>
                  </tr>
                \`;
              }).join('')}
            </tbody>
          </table>
        \`;
      }

      // Discrepancies List
      document.getElementById('discrepanciesCount').textContent = inv.discrepancies.length;
      const discList = document.getElementById('discrepanciesList');
      if (inv.discrepancies.length === 0) {
        discList.innerHTML = '<div class="empty-state">No discrepancies discovered between source AST and OpenAPI specifications.</div>';
      } else {
        discList.innerHTML = inv.discrepancies.map(d => \`
          <div style="background: var(--input-bg); border: 1px solid var(--border-subtle); border-radius: 3px; padding: 8px 10px; margin-bottom: 6px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span style="font-weight: 600;">\${escapeHtml(d.method)} \${escapeHtml(d.endpoint_path)}</span>
              <span class="tag \${d.discrepancy_type === 'undocumented_endpoint' ? 'medium' : 'breaking'}">\${escapeHtml(d.discrepancy_type)}</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">\${escapeHtml(d.description)}</div>
            \${d.code_evidence ? \`<div class="code-box" style="margin-top: 4px; max-height: 80px;">\${escapeHtml(d.code_evidence)}</div>\` : ''}
          </div>
        \`).join('');
      }

      // Dependencies & Integrations
      document.getElementById('depsCount').textContent = inv.dependencies.length + inv.integrations.length;
      const depsList = document.getElementById('depsAndIntegrationsList');
      let depsHtml = '';

      if (inv.dependencies.length > 0) {
        depsHtml += '<div style="font-weight: 600; text-transform: uppercase; font-size: 10px; color: var(--text-muted); margin-bottom: 6px;">Manifest Dependencies</div>';
        depsHtml += '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 8px; margin-bottom: 12px;">';
        depsHtml += inv.dependencies.map(dep => \`
          <div style="background: var(--input-bg); border: 1px solid var(--border-subtle); border-radius: 3px; padding: 8px;">
            <div style="display: flex; justify-content: space-between;">
              <strong>\${escapeHtml(dep.package_name)}</strong>
              <span class="tag \${dep.is_used ? 'approved' : 'low'}">\${dep.is_used ? 'Used' : 'Unused'}</span>
            </div>
            <div style="font-size: 10px; color: var(--text-muted);">Ecosystem: \${escapeHtml(dep.ecosystem)} | Version: \${escapeHtml(dep.declared_constraint || 'any')}</div>
            \${dep.import_locations && dep.import_locations.length > 0 ? \`
              <div style="margin-top: 4px; font-size: 10px;">
                Imports: <button class="file-link" onclick="openFile('\${escapeHtml(dep.import_locations[0].file)}', \${dep.import_locations[0].line})">\${escapeHtml(dep.import_locations[0].file)}:\${dep.import_locations[0].line}</button>
              </div>
            \` : ''}
          </div>
        \`).join('');
        depsHtml += '</div>';
      }

      if (inv.integrations.length > 0) {
        depsHtml += '<div style="font-weight: 600; text-transform: uppercase; font-size: 10px; color: var(--text-muted); margin-bottom: 6px;">External Integrations</div>';
        depsHtml += '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 8px;">';
        depsHtml += inv.integrations.map(integ => \`
          <div style="background: var(--input-bg); border: 1px solid var(--border-subtle); border-radius: 3px; padding: 8px;">
            <div style="display: flex; justify-content: space-between;">
              <strong>\${escapeHtml(integ.service_name)}</strong>
              <span class="tag low">\${escapeHtml(integ.integration_type)}</span>
            </div>
            <div style="font-size: 10px; color: var(--text-muted);">Location: <button class="file-link" onclick="openFile('\${escapeHtml(integ.file_path)}', \${integ.line_number})">\${escapeHtml(integ.file_path)}:\${integ.line_number}</button></div>
            \${integ.code_snippet ? \`<div class="code-box" style="margin-top: 4px; max-height: 60px;">\${escapeHtml(integ.code_snippet)}</div>\` : ''}
          </div>
        \`).join('');
        depsHtml += '</div>';
      }

      if (!depsHtml) {
        depsHtml = '<div class="empty-state">No external dependencies or integrations recorded.</div>';
      }
      depsList.innerHTML = depsHtml;

      // Documentation Deliverables
      const delivEl = document.getElementById('deliverablesList');
      const outDir = inv.output_dir || 'reports/repository-inventory';
      delivEl.innerHTML = \`
        <div style="display: flex; flex-direction: column; gap: 4px;">
          <div>[+] <strong>API Reference:</strong> <button class="file-link" onclick="openFile('\${escapeHtml(outDir)}/API_REFERENCE.md', 1)">\${escapeHtml(outDir)}/API_REFERENCE.md</button></div>
          <div>[+] <strong>Dependency Report:</strong> <button class="file-link" onclick="openFile('\${escapeHtml(outDir)}/DEPENDENCY_REPORT.md', 1)">\${escapeHtml(outDir)}/DEPENDENCY_REPORT.md</button></div>
          <div>[+] <strong>Integration Map:</strong> <button class="file-link" onclick="openFile('\${escapeHtml(outDir)}/INTEGRATION_MAP.md', 1)">\${escapeHtml(outDir)}/INTEGRATION_MAP.md</button></div>
          <div>[+] <strong>Test Coverage Audit:</strong> <button class="file-link" onclick="openFile('\${escapeHtml(outDir)}/TEST_COVERAGE.md', 1)">\${escapeHtml(outDir)}/TEST_COVERAGE.md</button></div>
          <div>[+] <strong>Enriched OpenAPI:</strong> <button class="file-link" onclick="openFile('\${escapeHtml(outDir)}/openapi.enriched.json', 1)">\${escapeHtml(outDir)}/openapi.enriched.json</button></div>
        </div>
      \`;

      if (state.graphData) {
        renderDependencyGraph(state.graphData);
      } else {
        vscode.postMessage({ command: 'refreshGraph' });
      }
    }

    /* --- API Dependency Graph Interactive Functions --- */

    function toggleDependencyGraph() {
      const body = document.getElementById('graphContainerBody');
      const icon = document.getElementById('graphToggleIcon');
      const btn = document.getElementById('btnToggleGraph');
      if (!body) return;

      state.graphExpanded = !state.graphExpanded;
      if (state.graphExpanded) {
        body.style.display = 'block';
        if (icon) icon.textContent = '▼';
        if (btn) btn.textContent = '▼ Collapse Graph';
        if (state.graphData) {
          renderDependencyGraph(state.graphData);
          setTimeout(graphFitView, 60);
        } else {
          vscode.postMessage({ command: 'refreshGraph' });
        }
      } else {
        body.style.display = 'none';
        if (icon) icon.textContent = '▶';
        if (btn) btn.textContent = '▶ Expand Graph';
      }
    }

    function expandDependencyGraph() {
      const body = document.getElementById('graphContainerBody');
      const icon = document.getElementById('graphToggleIcon');
      const btn = document.getElementById('btnToggleGraph');
      if (!body) return;
      state.graphExpanded = true;
      body.style.display = 'block';
      if (icon) icon.textContent = '▼';
      if (btn) btn.textContent = '▼ Collapse Graph';
      if (state.graphData) {
        renderDependencyGraph(state.graphData);
        setTimeout(graphFitView, 60);
      } else {
        vscode.postMessage({ command: 'refreshGraph' });
      }
    }

    function requestRefreshGraph() {
      vscode.postMessage({ command: 'refreshGraph' });
    }

    function onGraphSearchInput(val) {
      state.graphSearchQuery = val || '';
      applyGraphFilters();
    }

    function setGraphTypeFilter(type) {
      state.graphTypeFilter = type;
      ['all', 'endpoint', 'service', 'source_file', 'contract'].forEach(function(t) {
        const id = 'gType' + (t === 'all' ? 'All' : (t === 'endpoint' ? 'Endpoints' : (t === 'service' ? 'Services' : (t === 'source_file' ? 'Files' : 'Contracts'))));
        const btn = document.getElementById(id);
        if (btn) btn.classList.toggle('active', t === type);
      });
      applyGraphFilters();
    }

    function setGraphStatusFilter(status) {
      state.graphStatusFilter = status;
      ['all', 'issues', 'clean', 'unknown'].forEach(function(s) {
        const id = 'gStatus' + (s === 'all' ? 'All' : (s === 'issues' ? 'Issues' : (s === 'clean' ? 'Clean' : 'Unknown')));
        const btn = document.getElementById(id);
        if (btn) btn.classList.toggle('active', s === status);
      });
      applyGraphFilters();
    }

    function applyGraphFilters() {
      if (!state.graphData) return;
      const q = (state.graphSearchQuery || '').toLowerCase().trim();
      const typeFilter = state.graphTypeFilter;
      const statusFilter = state.graphStatusFilter;

      const nodes = state.graphData.nodes || [];
      const visibleIds = new Set();

      nodes.forEach(function(n) {
        const matchesType = (typeFilter === 'all') || (n.type === typeFilter);
        const matchesStatus = (statusFilter === 'all') ||
          (statusFilter === 'issues' ? (n.status === 'breaking' || n.status === 'drift') : (n.status === statusFilter));
        const matchesQuery = !q ||
          (n.label && n.label.toLowerCase().indexOf(q) !== -1) ||
          (n.subLabel && n.subLabel.toLowerCase().indexOf(q) !== -1) ||
          (n.routePath && n.routePath.toLowerCase().indexOf(q) !== -1) ||
          (n.filePath && n.filePath.toLowerCase().indexOf(q) !== -1) ||
          (n.serviceName && n.serviceName.toLowerCase().indexOf(q) !== -1);

        const visible = matchesType && matchesStatus && matchesQuery;
        if (visible) visibleIds.add(n.id);

        const el = document.getElementById('gn_' + escapeAttr(n.id));
        if (el) {
          el.style.display = visible ? '' : 'none';
        }
      });

      const edges = state.graphData.edges || [];
      edges.forEach(function(e) {
        const el = document.getElementById('ge_' + escapeAttr(e.id));
        if (el) {
          const visible = visibleIds.has(e.source) && visibleIds.has(e.target);
          el.style.display = visible ? '' : 'none';
        }
      });
    }

    function renderDependencyGraph(graphData) {
      if (!graphData) return;
      state.graphData = graphData;

      const summary = graphData.summary || {};
      const countBadge = document.getElementById('graphNodeCountBadge');
      if (countBadge) countBadge.textContent = (summary.totalNodes || 0) + ' nodes';

      const pSvc = document.getElementById('pillGraphServices');
      if (pSvc) pSvc.textContent = 'Services: ' + (summary.servicesCount || 0);

      const pEp = document.getElementById('pillGraphEndpoints');
      if (pEp) pEp.textContent = 'Endpoints: ' + (summary.endpointsCount || 0);

      const pCons = document.getElementById('pillGraphConsumers');
      if (pCons) pCons.textContent = 'Consumers: ' + (summary.sourceFilesCount || 0);

      const pCont = document.getElementById('pillGraphContracts');
      if (pCont) pCont.textContent = 'Contracts: ' + (summary.contractsCount || 0);

      const pIss = document.getElementById('pillGraphIssues');
      const issuesCount = (summary.breakingCount || 0) + (summary.driftCount || 0);
      if (pIss) {
        if (issuesCount > 0) {
          pIss.style.display = 'inline-block';
          pIss.textContent = 'Issues: ' + issuesCount;
        } else {
          pIss.style.display = 'none';
        }
      }

      const emptyOverlay = document.getElementById('graphEmptyOverlay');
      if (!graphData.nodes || graphData.nodes.length === 0) {
        if (emptyOverlay) emptyOverlay.style.display = 'flex';
        return;
      }
      if (emptyOverlay) emptyOverlay.style.display = 'none';

      const edgesLayer = document.getElementById('graphEdgesLayer');
      const nodesLayer = document.getElementById('graphNodesLayer');
      if (!edgesLayer || !nodesLayer) return;

      if (!nodesLayer._hasGraphListeners) {
        nodesLayer._hasGraphListeners = true;
        nodesLayer.addEventListener('click', function(ev) {
          const g = ev.target.closest('.graph-node');
          if (g) {
            const id = g.getAttribute('data-node-id');
            if (id) selectGraphNode(id);
          }
        });
        nodesLayer.addEventListener('dblclick', function(ev) {
          const g = ev.target.closest('.graph-node');
          if (g) {
            const id = g.getAttribute('data-node-id');
            if (id) onGraphNodeDblClick(id);
          }
        });
      }

      const nodeMap = new Map();
      graphData.nodes.forEach(function(n) { nodeMap.set(n.id, n); });

      // 1. Render Edges
      let edgesHtml = '';
      (graphData.edges || []).forEach(function(e) {
        const s = nodeMap.get(e.source);
        const t = nodeMap.get(e.target);
        if (!s || !t) return;

        const sx = (s.x || 0) + (s.width || 220);
        const sy = (s.y || 0) + 22;
        const tx = t.x || 0;
        const ty = (t.y || 0) + 22;

        const dx = Math.max(40, (tx - sx) / 2);
        const c1x = sx + dx;
        const c1y = sy;
        const c2x = tx - dx;
        const c2y = ty;

        const d = 'M ' + sx + ' ' + sy + ' C ' + c1x + ' ' + c1y + ', ' + c2x + ' ' + c2y + ', ' + tx + ' ' + ty;
        const marker = e.status === 'breaking' ? 'breaking' : (e.type === 'calls' ? 'calls' : (e.type === 'validated_by' ? 'validated' : 'belongs'));

        edgesHtml += '<path id="ge_' + escapeAttr(e.id) + '" class="graph-edge ' + escapeAttr(e.type) + ' ' + escapeAttr(e.status) + '" d="' + d + '" marker-end="url(#arrow-' + marker + ')" data-source="' + escapeAttr(e.source) + '" data-target="' + escapeAttr(e.target) + '" />';
      });
      edgesLayer.innerHTML = edgesHtml;

      // 2. Render Nodes
      let nodesHtml = '';
      graphData.nodes.forEach(function(n) {
        const x = n.x || 0;
        const y = n.y || 0;
        const w = n.width || 220;
        const h = n.height || 44;

        const typeBadge = n.type === 'endpoint' ? (n.method || 'API') : (n.type === 'service' ? 'SVC' : (n.type === 'contract' ? 'SPEC' : 'FILE'));
        const typeBadgeBg = n.type === 'endpoint' ? '#0e639c' : (n.type === 'service' ? '#3794ff' : (n.type === 'contract' ? '#795e26' : '#a64d79'));
        const statusColor = n.status === 'breaking' ? '#f14c4c' : (n.status === 'drift' ? '#cca700' : (n.status === 'clean' ? '#4ec9b0' : '#858585'));

        const titleText = (n.label || '').length > 22 ? (n.label.substring(0, 21) + '…') : n.label;
        const subText = (n.subLabel || n.status || '').length > 25 ? (n.subLabel.substring(0, 24) + '…') : (n.subLabel || n.status);

        nodesHtml += '<g id="gn_' + escapeAttr(n.id) + '" class="graph-node ' + escapeAttr(n.type) + ' ' + escapeAttr(n.status) + '" transform="translate(' + x + ',' + y + ')" data-node-id="' + escapeXml(n.id) + '">';
        nodesHtml += '<rect width="' + w + '" height="' + h + '" rx="4" ry="4" fill="var(--card-bg)" stroke="var(--border-subtle)" stroke-width="1" />';
        nodesHtml += '<rect x="8" y="10" width="38" height="24" rx="3" ry="3" fill="' + typeBadgeBg + '" opacity="0.85" />';
        nodesHtml += '<text x="27" y="26" text-anchor="middle" fill="#FFFFFF" font-size="9" font-weight="700" font-family="sans-serif">' + escapeXml(typeBadge) + '</text>';
        nodesHtml += '<text x="52" y="20" fill="var(--text-main)" font-size="11" font-weight="600" font-family="sans-serif">' + escapeXml(titleText) + '</text>';
        nodesHtml += '<text x="52" y="34" fill="var(--text-muted)" font-size="9" font-family="sans-serif">' + escapeXml(subText) + '</text>';
        nodesHtml += '<circle cx="' + (w - 12) + '" cy="14" r="4" fill="' + statusColor + '" />';
        nodesHtml += '</g>';
      });
      nodesLayer.innerHTML = nodesHtml;

      updateGraphTransform();
      applyGraphFilters();

      if (state.graphSelectedNodeId) {
        selectGraphNode(state.graphSelectedNodeId);
      }
    }

    function selectGraphNode(nodeId) {
      if (!state.graphData) return;
      state.graphSelectedNodeId = nodeId;
      const node = (state.graphData.nodes || []).find(function(n) { return n.id === nodeId; });
      if (!node) return;

      const nodes = state.graphData.nodes || [];
      const edges = state.graphData.edges || [];

      const connectedEdges = edges.filter(function(e) { return e.source === nodeId || e.target === nodeId; });
      const connectedNodeIds = new Set();
      connectedNodeIds.add(nodeId);
      connectedEdges.forEach(function(e) {
        connectedNodeIds.add(e.source);
        connectedNodeIds.add(e.target);
      });

      nodes.forEach(function(n) {
        const el = document.getElementById('gn_' + escapeAttr(n.id));
        if (el) {
          el.classList.toggle('selected', n.id === nodeId);
          el.classList.toggle('dimmed', !connectedNodeIds.has(n.id));
        }
      });

      edges.forEach(function(e) {
        const el = document.getElementById('ge_' + escapeAttr(e.id));
        if (el) {
          const isConn = e.source === nodeId || e.target === nodeId;
          el.classList.toggle('highlighted', isConn);
          el.classList.toggle('dimmed', !isConn);
        }
      });

      renderGraphNodeDrawer(node, connectedEdges);
    }

    function renderGraphNodeDrawer(node, connectedEdges) {
      const drawerEmpty = document.getElementById('graphDrawerEmpty');
      const drawerContent = document.getElementById('graphDrawerContent');
      if (!drawerContent) return;
      if (drawerEmpty) drawerEmpty.style.display = 'none';
      drawerContent.style.display = 'flex';

      if (!drawerContent._hasDrawerListeners) {
        drawerContent._hasDrawerListeners = true;
        drawerContent.addEventListener('click', function(ev) {
          const btn = ev.target.closest('[data-open-file]');
          if (btn) {
            const f = btn.getAttribute('data-open-file');
            const l = parseInt(btn.getAttribute('data-open-line') || '1', 10);
            if (f) openFile(f, l);
            return;
          }
          const sel = ev.target.closest('[data-select-node]');
          if (sel) {
            const id = sel.getAttribute('data-select-node');
            if (id) selectGraphNode(id);
          }
        });
      }

      const statusBadgeClass = node.status === 'breaking' ? 'breaking' : (node.status === 'drift' ? 'medium' : (node.status === 'clean' ? 'approved' : 'low'));
      const statusLabel = node.status.toUpperCase();

      let html = '';
      html += '<div style="display: flex; justify-content: space-between; align-items: center;">';
      html += '<span class="tag low" style="text-transform: uppercase;">' + escapeHtml(node.type.replace('_', ' ')) + '</span>';
      html += '<span class="tag ' + statusBadgeClass + '">' + escapeHtml(statusLabel) + '</span>';
      html += '</div>';

      html += '<div style="font-size: 13px; font-weight: 600; color: var(--text-main); word-break: break-all;">' + escapeHtml(node.label) + '</div>';

      if (node.subLabel && node.subLabel !== node.label) {
        html += '<div style="font-size: 11px; color: var(--text-muted); word-break: break-all;">' + escapeHtml(node.subLabel) + '</div>';
      }

      html += '<div style="display: flex; flex-direction: column; gap: 6px; padding: 8px; background: var(--input-bg); border: 1px solid var(--border-subtle); border-radius: 4px; font-size: 11px;">';

      if (node.type === 'endpoint') {
        html += '<div><strong>Method:</strong> <span class="tag method-' + (node.method || 'get').toLowerCase() + '">' + escapeHtml(node.method || 'GET') + '</span></div>';
        html += '<div><strong>Route Path:</strong> <code>' + escapeHtml(node.routePath || '/') + '</code></div>';
        html += '<div><strong>Belonging Service:</strong> ' + escapeHtml(node.serviceName || 'Unknown') + '</div>';
        html += '<div><strong>Validating Contract:</strong> ' + (node.contractPath && node.contractPath !== 'unavailable' ? '<code>' + escapeHtml(node.contractPath) + '</code>' : '<span style="color: var(--text-muted);">Unavailable</span>') + '</div>';
        if (node.filePath) {
          html += '<div><strong>Location:</strong> <button class="file-link" data-open-file="' + escapeHtml(node.filePath) + '" data-open-line="' + (node.lineNumber || 1) + '">' + escapeHtml(node.filePath) + (node.lineNumber ? ':' + node.lineNumber : '') + '</button></div>';
        }
        if (node.discoveryMethod) {
          html += '<div><strong>Discovery:</strong> ' + escapeHtml(node.discoveryMethod) + '</div>';
        }
        if (node.callLocations && node.callLocations.length > 0) {
          html += '<div style="margin-top: 4px;"><strong>Callers (' + node.callLocations.length + '):</strong><div style="display: flex; flex-direction: column; gap: 2px; margin-top: 2px;">';
          node.callLocations.forEach(function(c) {
            html += '<div>• <button class="file-link" data-open-file="' + escapeHtml(c.file) + '" data-open-line="' + c.line + '">' + escapeHtml(c.file) + ':' + c.line + '</button></div>';
          });
          html += '</div></div>';
        }
        if (node.metadata && node.metadata.statusReasons && node.metadata.statusReasons.length > 0) {
          html += '<div style="margin-top: 4px; color: ' + (node.status === 'breaking' ? 'var(--error-color)' : 'var(--warning-color)') + ';"><strong>Validation Reasons:</strong><ul style="padding-left: 14px; margin-top: 2px;">';
          node.metadata.statusReasons.forEach(function(r) {
            html += '<li>' + escapeHtml(r) + '</li>';
          });
          html += '</ul></div>';
        }
      } else if (node.type === 'source_file') {
        html += '<div><strong>File:</strong> <code>' + escapeHtml(node.filePath || '') + '</code></div>';
        if (node.callLocations && node.callLocations.length > 0) {
          html += '<div><strong>Call Sites (' + node.callLocations.length + '):</strong><div style="display: flex; flex-direction: column; gap: 2px; margin-top: 2px;">';
          node.callLocations.forEach(function(c) {
            html += '<div>• <button class="file-link" data-open-file="' + escapeHtml(c.file) + '" data-open-line="' + c.line + '">Line ' + c.line + '</button></div>';
          });
          html += '</div></div>';
        }
        const calledEps = connectedEdges.filter(function(e) { return e.type === 'calls'; }).map(function(e) { return e.target; });
        if (calledEps.length > 0) {
          html += '<div style="margin-top: 4px;"><strong>Endpoints Called (' + calledEps.length + '):</strong><div style="display: flex; flex-direction: column; gap: 2px; margin-top: 2px;">';
          calledEps.forEach(function(targetId) {
            const ep = (state.graphData.nodes || []).find(function(n) { return n.id === targetId; });
            if (ep) {
              html += '<div>• <a href="javascript:void(0)" data-select-node="' + escapeXml(ep.id) + '" style="color: var(--accent); text-decoration: none;">' + escapeHtml(ep.label) + '</a></div>';
            }
          });
          html += '</div></div>';
        }
      } else if (node.type === 'service') {
        html += '<div><strong>Service Name:</strong> ' + escapeHtml(node.label) + '</div>';
        if (node.metadata && node.metadata.targetUrlOrHost) {
          html += '<div><strong>Target Origin:</strong> <code>' + escapeHtml(node.metadata.targetUrlOrHost) + '</code></div>';
        }
        const memberEps = connectedEdges.filter(function(e) { return e.type === 'belongs_to'; }).map(function(e) { return e.source; });
        html += '<div><strong>Endpoints (' + memberEps.length + '):</strong><div style="display: flex; flex-direction: column; gap: 2px; margin-top: 2px; max-height: 140px; overflow-y: auto;">';
        memberEps.forEach(function(epId) {
          const ep = (state.graphData.nodes || []).find(function(n) { return n.id === epId; });
          if (ep) {
            html += '<div>• <a href="javascript:void(0)" data-select-node="' + escapeXml(ep.id) + '" style="color: var(--accent); text-decoration: none;">' + escapeHtml(ep.label) + '</a></div>';
          }
        });
        html += '</div></div>';
      } else if (node.type === 'contract') {
        html += '<div><strong>Specification:</strong> <code>' + escapeHtml(node.filePath || '') + '</code></div>';
        if (node.metadata && node.metadata.specFormat) {
          html += '<div><strong>Format:</strong> ' + escapeHtml(node.metadata.specFormat) + '</div>';
        }
        const valEps = connectedEdges.filter(function(e) { return e.type === 'validated_by'; }).map(function(e) { return e.source; });
        html += '<div><strong>Endpoints Validated (' + valEps.length + '):</strong><div style="display: flex; flex-direction: column; gap: 2px; margin-top: 2px; max-height: 140px; overflow-y: auto;">';
        valEps.forEach(function(epId) {
          const ep = (state.graphData.nodes || []).find(function(n) { return n.id === epId; });
          if (ep) {
            html += '<div>• <a href="javascript:void(0)" data-select-node="' + escapeXml(ep.id) + '" style="color: var(--accent); text-decoration: none;">' + escapeHtml(ep.label) + '</a></div>';
          }
        });
        html += '</div></div>';
      }

      html += '</div>';

      if (node.filePath && node.filePath !== 'unavailable') {
        html += '<button class="btn btn-primary btn-sm" data-open-file="' + escapeHtml(node.filePath) + '" data-open-line="' + (node.lineNumber || 1) + '">Open in Editor ↗</button>';
      }

      drawerContent.innerHTML = html;
    }

    function onGraphNodeDblClick(nodeId) {
      if (!state.graphData) return;
      const node = (state.graphData.nodes || []).find(function(n) { return n.id === nodeId; });
      if (node && node.filePath && node.filePath !== 'unavailable') {
        openFile(node.filePath, node.lineNumber || 1);
      }
    }

    function onGraphMouseDown(e) {
      if (e.target.closest('.graph-node')) return;
      state.graphIsPanning = true;
      state.graphPanStart = { x: e.clientX - state.graphPan.x, y: e.clientY - state.graphPan.y };
      const wrapper = document.getElementById('graphCanvasWrapper');
      if (wrapper) wrapper.style.cursor = 'grabbing';
      window.addEventListener('mousemove', onGraphMouseMove);
      window.addEventListener('mouseup', onGraphMouseUp);
    }

    function onGraphMouseMove(e) {
      if (!state.graphIsPanning) return;
      state.graphPan.x = e.clientX - state.graphPanStart.x;
      state.graphPan.y = e.clientY - state.graphPanStart.y;
      updateGraphTransform();
    }

    function onGraphMouseUp() {
      state.graphIsPanning = false;
      const wrapper = document.getElementById('graphCanvasWrapper');
      if (wrapper) wrapper.style.cursor = 'grab';
      window.removeEventListener('mousemove', onGraphMouseMove);
      window.removeEventListener('mouseup', onGraphMouseUp);
    }

    function onGraphWheel(e) {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.12 : 0.89;
      graphZoom(zoomFactor);
    }

    function graphZoom(factor) {
      const nextScale = Math.min(2.5, Math.max(0.25, state.graphScale * factor));
      state.graphScale = nextScale;
      updateGraphTransform();
    }

    function updateGraphTransform() {
      const g = document.getElementById('graphViewportGroup');
      if (g) {
        g.setAttribute('transform', 'translate(' + state.graphPan.x + ', ' + state.graphPan.y + ') scale(' + state.graphScale + ')');
      }
      const badge = document.getElementById('graphZoomBadge');
      if (badge) {
        badge.textContent = Math.round(state.graphScale * 100) + '%';
      }
    }

    function graphResetView() {
      state.graphPan = { x: 20, y: 20 };
      state.graphScale = 1.0;
      updateGraphTransform();
    }

    function graphFitView() {
      if (!state.graphData || !state.graphData.nodes || state.graphData.nodes.length === 0) return;
      const wrapper = document.getElementById('graphCanvasWrapper');
      if (!wrapper) return;
      const containerW = wrapper.clientWidth || 800;
      const containerH = wrapper.clientHeight || 500;
      const bounds = state.graphData.bounds || { width: 1200, height: 600 };

      const scaleX = (containerW - 60) / bounds.width;
      const scaleY = (containerH - 60) / bounds.height;
      const fitScale = Math.min(1.2, Math.max(0.25, Math.min(scaleX, scaleY)));

      state.graphScale = fitScale;
      state.graphPan = { x: 20, y: 20 };
      updateGraphTransform();
    }

    function escapeAttr(s) {
      if (!s) return '';
      return String(s).replace(/[^a-zA-Z0-9_-]/g, '_');
    }

    function escapeXml(s) {
      if (s === null || s === undefined) return '';
      return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    function renderDetails() {
      const noSel = document.getElementById('noSelectionMsg');
      const detailsEl = document.getElementById('activeDetails');

      if (!state.selectedChange) {
        noSel.style.display = 'block';
        detailsEl.style.display = 'none';
        return;
      }

      noSel.style.display = 'none';
      detailsEl.style.display = 'flex';

      const c = state.selectedChange;
      const isBlocked = c.change_type === 'semantic_uncertainty' || c.severity === 'blocked';
      const isBreaking = c.severity === 'high' || c.severity === 'critical' || c.severity === 'blocked';

      const prov = (c.evidence && c.evidence.provenance) || 'contract_diff';
      const provClass = 'provenance-' + prov;
      const provLabel = prov === 'static_ast' ? 'Static AST' : (prov === 'live_probe' ? 'Live Probe' : (prov === 'ai_inferred' ? 'AI Inferred' : 'Contract Diff'));
      const conf = (c.evidence && c.evidence.confidence !== undefined) ? c.evidence.confidence : 1.0;

      let html = '';

      // Header Card
      html += \`
        <div class="section-card">
          <div class="section-header">
            <span>\${escapeHtml(c.dependency_id)}: \${escapeHtml(c.change_type)}</span>
            <div style="display: flex; gap: 6px; align-items: center;">
              <span class="tag \${provClass}">\${provLabel}</span>
              <span class="tag low">Confidence: \${Math.round(conf * 100)}%</span>
              <span class="tag \${isBreaking ? 'breaking' : 'medium'}">\${escapeHtml(c.severity)}</span>
            </div>
          </div>
          <div style="font-size: 11px; color: var(--text-muted); line-height: 1.5;">
            <div><strong>Rule ID / Change Type:</strong> \${escapeHtml(c.change_type)}</div>
            <div><strong>Target / Probe:</strong> \${escapeHtml(c.probe_id)}</div>
            <div><strong>Compatibility Status:</strong> \${escapeHtml(c.status)}</div>
            \${c.evidence && c.evidence.location ? \`<div><strong>Location:</strong> \${escapeHtml(typeof c.evidence.location === 'object' ? JSON.stringify(c.evidence.location) : c.evidence.location)}</div>\` : ''}
            \${c.evidence && c.evidence.impact ? \`<div style="margin-top: 4px; color: var(--text-muted);"><strong>Impact:</strong> \${escapeHtml(c.evidence.impact)}</div>\` : ''}
            \${c.evidence && c.evidence.message ? \`<div style="margin-top: 4px; color: var(--text-main);"><strong>Description:</strong> \${escapeHtml(c.evidence.message)}</div>\` : ''}
            \${c.evidence && c.evidence.ai_reasoning ? \`<div style="margin-top: 4px; color: var(--vscode-editorWarning-foreground);"><strong>AI Reasoning:</strong> \${escapeHtml(c.evidence.ai_reasoning)}</div>\` : ''}
            \${c.evidence && c.evidence.recommended_action ? \`
              <div class="rec-action-box">
                <div class="rec-action-title">Recommended Action</div>
                <div>\${escapeHtml(c.evidence.recommended_action)}</div>
              </div>
            \` : ''}
          </div>
        </div>
      \`;

      // Evidence Card
      html += \`
        <div class="section-card">
          <div class="section-header">Contract Drift &amp; Technical Evidence</div>
          <div class="evidence-grid">
            <div>
              <div style="font-size: 10px; color: var(--text-muted); margin-bottom: 4px; text-transform: uppercase;">Baseline Expected</div>
              <div class="code-box">\${c.evidence && c.evidence.baseline_value !== undefined ? escapeHtml(JSON.stringify(c.evidence.baseline_value, null, 2)) : (c.evidence && c.evidence.expected_value !== undefined ? escapeHtml(JSON.stringify(c.evidence.expected_value, null, 2)) : (c.evidence && c.evidence.previous_value !== undefined ? escapeHtml(JSON.stringify(c.evidence.previous_value, null, 2)) : (c.evidence && c.evidence.expected_status_code ? 'HTTP ' + c.evidence.expected_status_code : 'Baseline contract established')))}</div>
            </div>
            <div>
              <div style="font-size: 10px; color: var(--text-muted); margin-bottom: 4px; text-transform: uppercase;">Observed Active</div>
              <div class="code-box">\${c.evidence && c.evidence.observed_value !== undefined ? escapeHtml(JSON.stringify(c.evidence.observed_value, null, 2)) : (c.evidence && c.evidence.current_value !== undefined ? escapeHtml(JSON.stringify(c.evidence.current_value, null, 2)) : (c.evidence && c.evidence.status_code ? 'HTTP ' + c.evidence.status_code + (c.evidence.latency_ms ? ' (' + Math.round(c.evidence.latency_ms) + 'ms)' : '') : (c.evidence && c.evidence.added_field ? '+ Added: ' + escapeHtml(c.evidence.added_field) : 'Drift detected in contract probe')))}</div>
            </div>
          </div>
          <details class="tech-evidence-details">
            <summary>Technical Evidence &amp; Payload Details</summary>
            <div class="code-box" style="margin-top: 8px; max-height: 220px; font-size: 11px; overflow-y: auto;">\${escapeHtml(JSON.stringify(c.evidence, null, 2))}</div>
          </details>
        </div>
      \`;

      // Affected Files & Workflows
      if (c.affected_files && c.affected_files.length > 0) {
        html += \`
          <div class="section-card">
            <div class="section-header">Affected Source Files (\${c.affected_files.length})</div>
            <div style="display: flex; flex-direction: column; gap: 4px;">
              \${c.affected_files.map(f => \`
                <div>
                  [+] <button class="file-link" onclick="openFile('\${escapeHtml(f)}', 1)">\${escapeHtml(f)}</button>
                </div>
              \`).join('')}
            </div>
          </div>
        \`;
      }

      // Repair Studio
      html += \`
        <div class="section-card">
          <div class="section-header">Repair Studio &amp; Backwards-Compatible Adapter</div>
      \`;

      if (state.repairError) {
        html += \`
          <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid var(--error-color); border-radius: 3px; padding: 8px 10px; margin-bottom: 10px; font-size: 11px; color: var(--error-color); line-height: 1.4;">
            <strong>Proposal Generation Error:</strong> \${escapeHtml(state.repairError)}
          </div>
        \`;
      }

      if (isBlocked) {
        html += \`
          <div style="font-size: 11px; color: var(--warning-color); line-height: 1.5; padding: 8px; border: 1px solid var(--border-subtle); border-radius: 2px;">
            Automatic repair generation is disabled for uncertain business semantics. Developer review required.
          </div>
        \`;
      } else if (!state.currentRepair) {
        html += \`
          <p style="font-size: 11px; color: var(--text-muted); margin-bottom: 10px;">
            A backwards-compatible adapter can be generated and validated for this breaking change.
          </p>
          <button class="btn btn-primary" onclick="proposeRepair('\${escapeHtml(c.id)}')" data-action="proposeRepair" data-change-id="\${escapeHtml(c.id)}">Generate Repair Proposal</button>
        \`;
      } else {
        const rep = state.currentRepair;
        const isApproved = rep.status === 'approved';
        const isApplied = rep.status === 'applied';
        const isRejected = rep.status === 'rejected';
        const isRolledBack = rep.status === 'rolled_back';
        const isStale = !!(state.staleness && state.staleness.isStale);

        const canApprove = rep.status === 'proposed' && !isStale && !state.actionPending;
        const canReject = (rep.status === 'proposed' || rep.status === 'approved') && !state.actionPending;
        const canApply = isApproved && !isStale && !state.actionPending;

        html += \`
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 11px; font-weight: 600;">Strategy: \${escapeHtml(rep.repair_type)}</span>
            <span class="tag \${isApproved || isApplied ? 'approved' : (isRejected ? 'breaking' : (isRolledBack ? 'medium' : 'low'))}">Status: \${escapeHtml(rep.status)}</span>
          </div>
          <div style="font-size: 10px; color: var(--text-muted); margin-bottom: 8px;">
            Target: \${escapeHtml(rep.target_file || 'workspace')} | Confidence: \${Math.round((rep.confidence || 0.9) * 100)}%
          </div>
        \`;

        if (rep.rationale) {
          html += \`<div style="font-size: 11px; color: var(--text-main); margin-bottom: 8px; line-height: 1.4;"><strong>Rationale:</strong> \${escapeHtml(rep.rationale)}</div>\`;
        }
        if (rep.likely_root_cause) {
          html += \`<div style="font-size: 10px; color: var(--text-muted); margin-bottom: 8px;"><strong>Root Cause:</strong> \${escapeHtml(rep.likely_root_cause)}</div>\`;
        }

        if (isStale) {
          html += \`
            <div style="background: rgba(204, 167, 0, 0.12); border: 1px solid var(--warning-color); border-radius: 3px; padding: 8px 10px; margin-bottom: 10px; font-size: 11px; color: var(--warning-color); display: flex; gap: 6px; align-items: center;">
              <span>⚠ <strong>Proposal is Stale:</strong> \${escapeHtml(state.staleness.reason || 'Source files modified on disk.')} Re-generation required.</span>
            </div>
          \`;
        }

        // Render Git-Style Diff Review
        html += renderGitDiffReview(rep, state.changeSet, state.staleness);

        if (state.validation) {
          const val = state.validation;
          const isPassed = val.status === 'passed';
          html += \`
            <div style="font-size: 11px; padding: 6px 8px; margin-top: 8px; margin-bottom: 10px; border: 1px solid var(--border-subtle); border-radius: 2px;">
              <span style="color: \${isPassed ? 'var(--success-color)' : 'var(--error-color)'}; font-weight: 600;">Validation \${isPassed ? 'Passed' : 'Failed'} (\${val.duration_ms || 0}ms):</span>
              <span style="color: var(--text-muted);">\${escapeHtml(val.output_summary || '')}</span>
            </div>
          \`;
        }

        // Action Toolbar
        html += \`
          <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-top: 10px;">
            <button class="btn btn-secondary" onclick="openNativeDiff('\${escapeHtml(rep.id)}')" data-action="openNativeDiff" data-repair-id="\${escapeHtml(rep.id)}">Open Native VS Code Diff</button>
            <button class="btn btn-secondary" onclick="validateRepair('\${escapeHtml(rep.id)}')" data-action="validateRepair" data-repair-id="\${escapeHtml(rep.id)}">Run Validation</button>
            <button class="btn btn-secondary" \${canApprove ? '' : 'disabled'} title="\${canApprove ? 'Explicit human approval of proposal patch' : (isApproved ? 'Proposal is already approved' : (isApplied ? 'Proposal is already applied' : 'Cannot approve'))}" onclick="approveRepair('\${escapeHtml(rep.id)}')" data-action="approveRepair" data-repair-id="\${escapeHtml(rep.id)}">
              \${isApproved ? 'Approved ✓' : 'Approve Proposal'}
            </button>
            <button class="btn btn-secondary" \${canReject ? '' : 'disabled'} title="\${canReject ? 'Reject proposal and prevent application' : (isRejected ? 'Already rejected' : 'Cannot reject applied repair')}" onclick="rejectRepair('\${escapeHtml(rep.id)}')" data-action="rejectRepair" data-repair-id="\${escapeHtml(rep.id)}">
              \${isRejected ? 'Rejected ✗' : 'Reject Proposal'}
            </button>
            <button class="btn btn-primary" \${canApply ? '' : 'disabled'} title="\${canApply ? 'Safely apply approved patch to workspace files' : (isApplied ? 'Changes have already been applied' : 'Repair proposal must be in approved status before changes can be applied')}" onclick="applyRepair('\${escapeHtml(rep.id)}')" data-action="applyRepair" data-repair-id="\${escapeHtml(rep.id)}">
              \${isApplied ? 'Applied ✓' : (isApproved ? 'Apply Approved Repair' : 'Apply (Requires Approval)')}
            </button>
            \${isApplied ? \`<button class="btn btn-secondary" onclick="rollbackRepair('\${escapeHtml(rep.id)}')" data-action="rollbackRepair" data-repair-id="\${escapeHtml(rep.id)}">Roll Back</button>\` : ''}
            \${(isRejected || isRolledBack || isStale) ? \`<button class="btn btn-secondary" onclick="proposeRepair('\${escapeHtml(c.id)}')" data-action="proposeRepair" data-change-id="\${escapeHtml(c.id)}">Re-generate Proposal</button>\` : ''}
          </div>
        \`;
      }

      html += '</div>';

      // Lifecycle Actions Card
      const st = (c.status || 'open').toLowerCase();
      html += \`
        <div class="section-card">
          <div class="section-header">
            <span>Incident Lifecycle &amp; State</span>
            <span class="tag status-\${st}">Status: \${escapeHtml(st)}</span>
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px;">
            <button class="btn btn-secondary btn-sm" \${st === 'acknowledged' ? 'disabled' : ''} onclick="ackIncident('\${escapeHtml(c.id)}')" data-action="ackIncident" data-incident-id="\${escapeHtml(c.id)}">Acknowledge</button>
            <button class="btn btn-secondary btn-sm" \${st === 'resolved' ? 'disabled' : ''} onclick="resolveIncident('\${escapeHtml(c.id)}')" data-action="resolveIncident" data-incident-id="\${escapeHtml(c.id)}">Resolve</button>
            <button class="btn btn-secondary btn-sm" \${st === 'reopened' || st === 'open' ? 'disabled' : ''} onclick="reopenIncident('\${escapeHtml(c.id)}')" data-action="reopenIncident" data-incident-id="\${escapeHtml(c.id)}">Reopen</button>
          </div>
          \${c.review_notes ? \`<div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;"><strong>Review Notes:</strong> \${escapeHtml(c.review_notes)}</div>\` : ''}
          \${c.resolution_notes ? \`<div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;"><strong>Resolution Notes:</strong> \${escapeHtml(c.resolution_notes)}</div>\` : ''}
          \${c.occurrence_count && c.occurrence_count > 1 ? \`<div style="font-size: 11px; color: var(--warning-color); margin-top: 4px;">Observed \${c.occurrence_count} times across scans.</div>\` : ''}
        </div>
      \`;

      // Incident Event Timeline
      if (state.events && state.events.length > 0) {
        html += \`
          <div class="section-card">
            <div class="section-header">Audit Timeline &amp; Events (\${state.events.length})</div>
            <div style="display: flex; flex-direction: column; gap: 6px;">
              \${state.events.map(ev => \`
                <div style="display: flex; justify-content: space-between; align-items: flex-start; padding: 4px 6px; background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: 2px;">
                  <div>
                    <span class="tag status-\${(ev.event_type || 'open').toLowerCase()}">\${escapeHtml(ev.event_type)}</span>
                    <span style="font-size: 11px; margin-left: 6px;">\${escapeHtml(ev.message || '')}</span>
                  </div>
                  <span style="font-size: 10px; color: var(--text-muted); white-space: nowrap;">\${new Date(ev.created_at).toLocaleTimeString()}</span>
                </div>
              \`).join('')}
            </div>
          </div>
        \`;
      }

      detailsEl.innerHTML = html;
    }

    function renderBaselines() {
      const activeEl = document.getElementById('activeBaselineDetails');
      const badgeEl = document.getElementById('activeBaselineStatusBadge');
      if (activeEl) {
        if (state.activeBaseline) {
          const ab = state.activeBaseline;
          const epCount = (ab.inventory && ab.inventory.endpoints ? ab.inventory.endpoints.length : (ab.inventory && ab.inventory.discovered_endpoints ? ab.inventory.discovered_endpoints : (ab.contracts && ab.contracts.paths ? Object.keys(ab.contracts.paths).length : 0)));
          if (badgeEl) badgeEl.textContent = 'Active Reference (v' + ab.version_number + ')';
          activeEl.innerHTML = \`
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
              <div><strong>Version:</strong> v\${ab.version_number} (<code>\${escapeHtml(ab.version_tag)}</code>)</div>
              <div><strong>Endpoints Recorded:</strong> \${epCount}</div>
              <div><strong>Promoted At:</strong> \${ab.promoted_at ? new Date(ab.promoted_at).toLocaleString() : 'Active'}</div>
            </div>
            \${ab.description ? \`<div style="margin-top: 6px; color: var(--text-muted);"><strong>Description:</strong> \${escapeHtml(ab.description)}</div>\` : ''}
          \`;
        } else {
          if (badgeEl) badgeEl.textContent = 'No Active Baseline';
          activeEl.innerHTML = '<div style="color: var(--text-muted);">No baseline is currently promoted as active. Click Snapshot Inventory as New Baseline below.</div>';
        }
      }

      // Populate Contract Comparison Studio Dropdowns
      const baseSel = document.getElementById('compareBaseSelect');
      const targetSel = document.getElementById('compareTargetSelect');
      if (baseSel && targetSel) {
        if (!state.baselines || state.baselines.length === 0) {
          baseSel.innerHTML = '<option value="">No baseline snapshots found</option>';
          targetSel.innerHTML = '<option value="">No baseline snapshots found</option>';
        } else {
          const optionsHtml = state.baselines.map(function(b) {
            const isActive = b.is_active || (state.activeBaseline && state.activeBaseline.id === b.id);
            const tag = b.version_tag ? b.version_tag : ('v' + b.version_number);
            return '<option value="' + escapeHtml(b.id) + '">' +
                   'v' + b.version_number + ' (' + escapeHtml(tag) + ')' + (isActive ? ' [Active]' : '') +
                   '</option>';
          }).join('');

          baseSel.innerHTML = optionsHtml;
          targetSel.innerHTML = optionsHtml;

          if (state.activeBaseline) {
            baseSel.value = state.activeBaseline.id;
          } else if (state.baselines.length > 0) {
            baseSel.value = state.baselines[0].id;
          }

          if (state.baselines.length > 1) {
            const other = state.baselines.find(function(b) { return b.id !== baseSel.value; });
            if (other) {
              targetSel.value = other.id;
            } else {
              targetSel.value = state.baselines[1].id;
            }
          } else if (state.baselines.length > 0) {
            targetSel.value = state.baselines[0].id;
          }
        }
      }

      const countEl = document.getElementById('baselinesCount');
      if (countEl) countEl.textContent = state.baselines.length;

      const tblEl = document.getElementById('baselinesTableContainer');
      if (!tblEl) return;
      if (state.baselines.length === 0) {
        tblEl.innerHTML = '<div class="empty-state">No versioned baselines found. Capture a baseline from the current inventory.</div>';
        return;
      }

      tblEl.innerHTML = \`
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 70px;">Version</th>
              <th>Version Tag</th>
              <th>Description</th>
              <th>Endpoints</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            \${state.baselines.map(b => {
              const isActive = b.is_active || (state.activeBaseline && state.activeBaseline.id === b.id);
              const epCount = (b.inventory && b.inventory.endpoints ? b.inventory.endpoints.length : (b.inventory && b.inventory.discovered_endpoints ? b.inventory.discovered_endpoints : (b.contracts && b.contracts.paths ? Object.keys(b.contracts.paths).length : '-')));
              return \`
                <tr>
                  <td><strong>v\${b.version_number}</strong></td>
                  <td><code>\${escapeHtml(b.version_tag)}</code></td>
                  <td>\${escapeHtml(b.description || '-')}</td>
                  <td>\${epCount}</td>
                  <td><span class="tag \${isActive ? 'approved' : 'low'}">\${isActive ? 'Active' : 'Snapshot'}</span></td>
                  <td>\${new Date(b.created_at).toLocaleDateString()}</td>
                  <td>
                    <div style="display: flex; gap: 4px;">
                      \${!isActive ? \`<button class="btn btn-secondary btn-sm" onclick="promoteBaseline('\${escapeHtml(b.id)}')" data-action="promoteBaseline" data-baseline-id="\${escapeHtml(b.id)}">Promote</button>\` : ''}
                      \${state.activeBaseline && state.activeBaseline.id !== b.id ? \`<button class="btn btn-secondary btn-sm" onclick="compareWithActive('\${escapeHtml(b.id)}')" data-action="compareWithActive" data-baseline-id="\${escapeHtml(b.id)}">Compare with Active</button>\` : ''}
                    </div>
                  </td>
                </tr>
              \`;
            }).join('')}
          </tbody>
        </table>
      \`;
    }

    function renderScanHistory() {
      const countEl = document.getElementById('scansCount');
      if (countEl) countEl.textContent = state.scanHistory.length;

      const tblEl = document.getElementById('scansTableContainer');
      if (!tblEl) return;
      if (state.scanHistory.length === 0) {
        tblEl.innerHTML = '<div class="empty-state">No persistent scan runs recorded. Execute an analysis to start recording scan history.</div>';
        return;
      }

      tblEl.innerHTML = \`
        <table class="data-table">
          <thead>
            <tr>
              <th>Run ID</th>
              <th>Type</th>
              <th>Mode</th>
              <th>Duration</th>
              <th>Findings</th>
              <th>Status</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            \${state.scanHistory.map(s => {
              const mode = s.detection_mode || 'algorithmic';
              const modeClass = 'mode-' + mode;
              const statusClass = s.status === 'succeeded' ? 'approved' : (s.status === 'failed' ? 'breaking' : 'medium');
              const findingsTotal = (s.summary_counts && s.summary_counts.findings_total !== undefined) ? s.summary_counts.findings_total : ((s.findings_json || []).length);
              const dur = s.duration_seconds ? (Math.round(s.duration_seconds * 10) / 10 + 's') : '-';
              return \`
                <tr>
                  <td><code>\${escapeHtml((s.client_run_id || s.id || '').slice(0, 18))}</code></td>
                  <td><strong>\${escapeHtml(s.scan_type)}</strong></td>
                  <td><span class="tag \${modeClass}">\${escapeHtml(mode)}</span></td>
                  <td>\${dur}</td>
                  <td>\${findingsTotal}</td>
                  <td><span class="tag \${statusClass}">\${escapeHtml(s.status)}</span></td>
                  <td>\${new Date(s.started_at).toLocaleString()}</td>
                </tr>
              \`;
            }).join('')}
          </tbody>
        </table>
      \`;
    }

    function renderBaselineDiff(diff) {
      const card = document.getElementById('baselineDiffCard');
      const content = document.getElementById('baselineDiffContent');
      if (!card || !content) return;
      card.style.display = 'block';

      if (!diff) {
        content.innerHTML = '<div class="empty-state">No comparison data returned from backend.</div>';
        return;
      }

      const s = diff.summary || {};
      const addedCount = s.added_count !== undefined ? s.added_count : (diff.endpoints_added ? diff.endpoints_added.length : 0);
      const removedCount = s.removed_count !== undefined ? s.removed_count : (diff.endpoints_removed ? diff.endpoints_removed.length : 0);
      const modifiedCount = s.modified_count !== undefined ? s.modified_count : (diff.endpoints_modified ? diff.endpoints_modified.length : 0);
      const hasChanges = (addedCount + removedCount + modifiedCount) > 0;

      let html = \`
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-subtle);">
          <div style="font-size: 12px; font-weight: 600;">
            Comparing Reference <strong>v\${diff.base_version}</strong> ➔ Target <strong>v\${diff.target_version}</strong>
          </div>
          <div style="display: flex; gap: 8px; font-size: 11px;">
            <span class="tag approved">+\${addedCount} Added</span>
            <span class="tag breaking">-\${removedCount} Removed</span>
            <span class="tag medium">~\${modifiedCount} Modified</span>
          </div>
        </div>
      \`;

      if (!hasChanges) {
        html += '<div class="empty-state" style="padding: 16px;">Identical contracts: No endpoints or schema differences detected between v' + diff.base_version + ' and v' + diff.target_version + '.</div>';
      }

      if (diff.endpoints_added && diff.endpoints_added.length > 0) {
        html += \`
          <div style="margin-bottom: 12px;">
            <div style="font-size: 11px; font-weight: 600; color: var(--success-color); margin-bottom: 6px;">[+] Added Endpoints (\${diff.endpoints_added.length}):</div>
            <div class="code-box" style="color: var(--success-color);">
              \${diff.endpoints_added.map(e => '+ ' + (e.method || 'GET').toUpperCase() + ' ' + (e.path || e.endpoint_path || '') + (e.summary ? ' - ' + e.summary : '')).join(String.fromCharCode(10))}
            </div>
          </div>
        \`;
      }

      if (diff.endpoints_removed && diff.endpoints_removed.length > 0) {
        html += \`
          <div style="margin-bottom: 12px;">
            <div style="font-size: 11px; font-weight: 600; color: var(--error-color); margin-bottom: 6px;">[-] Removed Endpoints (\${diff.endpoints_removed.length}):</div>
            <div class="code-box" style="color: var(--error-color);">
              \${diff.endpoints_removed.map(e => '- ' + (e.method || 'GET').toUpperCase() + ' ' + (e.path || e.endpoint_path || '') + (e.summary ? ' - ' + e.summary : '')).join(String.fromCharCode(10))}
            </div>
          </div>
        \`;
      }

      if (diff.endpoints_modified && diff.endpoints_modified.length > 0) {
        html += \`
          <div style="margin-bottom: 12px;">
            <div style="font-size: 11px; font-weight: 600; color: var(--warning-color); margin-bottom: 6px;">[~] Modified Endpoints &amp; Schema Changes (\${diff.endpoints_modified.length}):</div>
            <div style="display: flex; flex-direction: column; gap: 6px;">
              \${diff.endpoints_modified.map(e => \`
                <div style="background: var(--input-bg); border: 1px solid var(--border-subtle); border-radius: 3px; padding: 6px 10px;">
                  <div style="font-weight: 600; font-size: 11px;">\${escapeHtml(e.method || 'GET')} \${escapeHtml(e.path || e.endpoint_path || '')}</div>
                  \${e.changes ? \`<div class="code-box" style="margin-top: 4px; font-size: 10px;">\${escapeHtml(JSON.stringify(e.changes, null, 2))}</div>\` : ''}
                </div>
              \`).join('')}
            </div>
          </div>
        \`;
      }

      if (diff.contract_diffs && Object.keys(diff.contract_diffs).length > 0) {
        html += \`
          <details class="tech-evidence-details" style="margin-top: 8px;">
            <summary>Detailed Contract Specification Diffs</summary>
            <div class="code-box" style="margin-top: 6px; max-height: 200px; overflow-y: auto;">\${escapeHtml(JSON.stringify(diff.contract_diffs, null, 2))}</div>
          </details>
        \`;
      }

      content.innerHTML = html;
      card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function closeBaselineDiff() {
      const card = document.getElementById('baselineDiffCard');
      if (card) card.style.display = 'none';
    }

    function promptCreateBaseline() {
      vscode.postMessage({ command: 'requestCreateBaseline' });
    }

    function promoteBaseline(baselineId) {
      vscode.postMessage({ command: 'promoteBaseline', baselineId: baselineId });
    }

    function compareWithActive(targetId) {
      if (!state.activeBaseline) {
        showToast('No active baseline to compare against.', 'warning');
        return;
      }
      vscode.postMessage({ command: 'compareBaselines', base: state.activeBaseline.id, target: targetId });
    }

    function executeSelectedCompare() {
      const baseSel = document.getElementById('compareBaseSelect');
      const targetSel = document.getElementById('compareTargetSelect');
      if (!baseSel || !targetSel) return;
      const baseId = baseSel.value;
      const targetId = targetSel.value;
      if (!baseId || !targetId) {
        showToast('Please select two baseline snapshots to compare.', 'warning');
        return;
      }
      if (baseId === targetId) {
        showToast('Base and target are identical versions. Diff will show 0 changes.', 'info');
      }
      vscode.postMessage({ command: 'compareBaselines', base: baseId, target: targetId });
    }

    function scrollToCompareStudio() {
      switchTab('baselines');
      const el = document.getElementById('baselineCompareStudio');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }

    function ackIncident(incidentId) {
      vscode.postMessage({ command: 'acknowledgeIncident', incidentId: incidentId });
    }

    function resolveIncident(incidentId) {
      vscode.postMessage({ command: 'requestResolveIncident', incidentId: incidentId });
    }

    function reopenIncident(incidentId) {
      vscode.postMessage({ command: 'requestReopenIncident', incidentId: incidentId });
    }

    function parseUnifiedDiff(diffText, fallbackFile) {
      if (!diffText || typeof diffText !== 'string' || !diffText.trim()) {
        return [];
      }

      var rawLines = diffText.split(String.fromCharCode(10));
      var files = [];
      var currentFile = null;
      var currentHunk = null;

      for (var i = 0; i < rawLines.length; i++) {
        var line = rawLines[i].replace(String.fromCharCode(13), '');

        if (line.indexOf('--- ') === 0) {
          var fromPath = line.substring(4).trim();
          if (fromPath.indexOf('a/') === 0 || fromPath.indexOf('b/') === 0) {
            fromPath = fromPath.substring(2);
          }
          if (!currentFile || currentFile.fromPath) {
            currentFile = {
              fromPath: fromPath,
              toPath: '',
              displayPath: fromPath,
              hunks: [],
              additions: 0,
              deletions: 0
            };
            files.push(currentFile);
          } else {
            currentFile.fromPath = fromPath;
          }
          currentHunk = null;
          continue;
        }

        if (line.indexOf('+++ ') === 0) {
          var toPath = line.substring(4).trim();
          if (toPath.indexOf('a/') === 0 || toPath.indexOf('b/') === 0) {
            toPath = toPath.substring(2);
          }
          if (!currentFile) {
            currentFile = {
              fromPath: '',
              toPath: toPath,
              displayPath: toPath,
              hunks: [],
              additions: 0,
              deletions: 0
            };
            files.push(currentFile);
          } else {
            currentFile.toPath = toPath;
            currentFile.displayPath = toPath === '/dev/null' ? currentFile.fromPath : toPath;
          }
          currentHunk = null;
          continue;
        }

        if (line.indexOf('@@ ') === 0) {
          if (!currentFile) {
            currentFile = {
              fromPath: fallbackFile || 'file',
              toPath: fallbackFile || 'file',
              displayPath: fallbackFile || 'file',
              hunks: [],
              additions: 0,
              deletions: 0
            };
            files.push(currentFile);
          }

          var match = line.match(/^@@ -([0-9]+)(?:,([0-9]+))? [+]([0-9]+)(?:,([0-9]+))? @@(.*)$/);
          var oldStart = 1;
          var newStart = 1;
          var heading = '';
          if (match) {
            oldStart = parseInt(match[1], 10);
            newStart = parseInt(match[3], 10);
            heading = match[5] ? match[5].trim() : '';
          }

          currentHunk = {
            header: line,
            oldStart: oldStart,
            newStart: newStart,
            heading: heading,
            lines: [],
            currentOld: oldStart,
            currentNew: newStart
          };
          currentFile.hunks.push(currentHunk);
          continue;
        }

        if (currentHunk) {
          if (line.indexOf('+') === 0) {
            currentHunk.lines.push({
              type: 'add',
              text: line.substring(1),
              newLine: currentHunk.currentNew++
            });
            currentFile.additions++;
          } else if (line.indexOf('-') === 0) {
            currentHunk.lines.push({
              type: 'del',
              text: line.substring(1),
              oldLine: currentHunk.currentOld++
            });
            currentFile.deletions++;
          } else if (line.indexOf(' ') === 0 || line === '') {
            currentHunk.lines.push({
              type: 'context',
              text: line.indexOf(' ') === 0 ? line.substring(1) : line,
              oldLine: currentHunk.currentOld++,
              newLine: currentHunk.currentNew++
            });
          }
        }
      }

      if (files.length === 0 && rawLines.some(function(l) { return l.indexOf('+') === 0 || l.indexOf('-') === 0; })) {
        var singleFile = {
          fromPath: fallbackFile || 'target-file',
          toPath: fallbackFile || 'target-file',
          displayPath: fallbackFile || 'target-file',
          hunks: [],
          additions: 0,
          deletions: 0
        };
        var fallbackHunk = {
          header: '@@ -1,1 +1,1 @@',
          oldStart: 1,
          newStart: 1,
          lines: [],
          currentOld: 1,
          currentNew: 1
        };
        for (var j = 0; j < rawLines.length; j++) {
          var rl = rawLines[j].replace(String.fromCharCode(13), '');
          if (rl.indexOf('+') === 0) {
            fallbackHunk.lines.push({ type: 'add', text: rl.substring(1), newLine: fallbackHunk.currentNew++ });
            singleFile.additions++;
          } else if (rl.indexOf('-') === 0) {
            fallbackHunk.lines.push({ type: 'del', text: rl.substring(1), oldLine: fallbackHunk.currentOld++ });
            singleFile.deletions++;
          } else {
            fallbackHunk.lines.push({ type: 'context', text: rl.indexOf(' ') === 0 ? rl.substring(1) : rl, oldLine: fallbackHunk.currentOld++, newLine: fallbackHunk.currentNew++ });
          }
        }
        singleFile.hunks.push(fallbackHunk);
        files.push(singleFile);
      }

      return files;
    }

    function buildDiffFromChangeSet(changeSet) {
      if (!changeSet || changeSet.length === 0) return [];
      return changeSet.map(function(cs) {
        var origLines = (cs.originalContent || '').split(String.fromCharCode(10));
        var propLines = (cs.proposedContent || '').split(String.fromCharCode(10));
        var hunk = {
          header: '@@ -1,' + origLines.length + ' +1,' + propLines.length + ' @@',
          oldStart: 1,
          newStart: 1,
          lines: []
        };
        var adds = 0;
        var dels = 0;
        var start = 0;
        while (start < origLines.length && start < propLines.length && origLines[start] === propLines[start]) {
          hunk.lines.push({ type: 'context', text: origLines[start], oldLine: start + 1, newLine: start + 1 });
          start++;
        }
        var endOrig = origLines.length - 1;
        var endProp = propLines.length - 1;
        while (endOrig >= start && endProp >= start && origLines[endOrig] === propLines[endProp]) {
          endOrig--;
          endProp--;
        }
        for (var i = start; i <= endOrig; i++) {
          hunk.lines.push({ type: 'del', text: origLines[i], oldLine: i + 1 });
          dels++;
        }
        for (var j = start; j <= endProp; j++) {
          hunk.lines.push({ type: 'add', text: propLines[j], newLine: j + 1 });
          adds++;
        }
        for (var k = endOrig + 1; k < origLines.length; k++) {
          hunk.lines.push({ type: 'context', text: origLines[k], oldLine: k + 1, newLine: (k - endOrig) + endProp + 1 });
        }
        return {
          fromPath: cs.relativePath,
          toPath: cs.relativePath,
          displayPath: cs.relativePath,
          hunks: [hunk],
          additions: adds,
          deletions: dels
        };
      });
    }

    function alignHunkLines(lines) {
      var rows = [];
      var delQueue = [];
      var addQueue = [];

      function flush() {
        var count = Math.max(delQueue.length, addQueue.length);
        for (var i = 0; i < count; i++) {
          rows.push({
            left: delQueue[i] || { type: 'empty' },
            right: addQueue[i] || { type: 'empty' }
          });
        }
        delQueue = [];
        addQueue = [];
      }

      for (var idx = 0; idx < lines.length; idx++) {
        var line = lines[idx];
        if (line.type === 'del') {
          delQueue.push(line);
        } else if (line.type === 'add') {
          addQueue.push(line);
        } else if (line.type === 'context') {
          flush();
          rows.push({
            left: { type: 'context', lineNum: line.oldLine, text: line.text },
            right: { type: 'context', lineNum: line.newLine, text: line.text }
          });
        }
      }
      flush();
      return rows;
    }

    function renderGitDiffReview(rep, changeSet, staleness) {
      var parsedFiles = parseUnifiedDiff(rep.diff, rep.target_file);
      if (parsedFiles.length === 0 && changeSet && changeSet.length > 0) {
        parsedFiles = buildDiffFromChangeSet(changeSet);
      }

      if (parsedFiles.length === 0) {
        return '<div class="diff-review-container"><div class="empty-state">No diff available for this proposal.</div></div>';
      }

      var selectedIdx = Math.min(Math.max(0, state.selectedDiffFileIndex || 0), parsedFiles.length - 1);
      var activeFile = parsedFiles[selectedIdx];
      var viewMode = state.diffViewMode || 'split';

      var totalAdd = 0;
      var totalDel = 0;
      for (var fi = 0; fi < parsedFiles.length; fi++) {
        totalAdd += parsedFiles[fi].additions;
        totalDel += parsedFiles[fi].deletions;
      }

      var html = '<div class="diff-review-container">';

      // Toolbar
      html += '<div class="diff-review-toolbar">';
      if (parsedFiles.length > 1) {
        html += '<div class="diff-file-tabs">';
        for (var ti = 0; ti < parsedFiles.length; ti++) {
          var f = parsedFiles[ti];
          var isActive = ti === selectedIdx;
          html += '<button class="diff-file-tab ' + (isActive ? 'active' : '') + '" onclick="selectDiffFile(' + ti + ')" data-action="selectDiffFile" data-file-index="' + ti + '">' +
                  '<span>' + escapeHtml(f.displayPath) + '</span>' +
                  '<span class="diff-stat-add">+' + f.additions + '</span>' +
                  '<span class="diff-stat-del">-' + f.deletions + '</span>' +
                  '</button>';
        }
        html += '</div>';
      } else {
        html += '<div style="font-size: 11px; font-weight: 600; color: var(--text-main); font-family: monospace;">' + escapeHtml(activeFile.displayPath) + '</div>';
      }

      html += '<div style="display: flex; gap: 10px; align-items: center; margin-left: auto;">';
      html += '<div class="diff-stats-badge">' +
              '<span>' + parsedFiles.length + ' file' + (parsedFiles.length > 1 ? 's' : '') + ' changed</span>' +
              '<span class="diff-stat-add">+' + totalAdd + '</span>' +
              '<span class="diff-stat-del">-' + totalDel + '</span>' +
              '</div>';
      html += '<div class="diff-view-mode-toggle">';
      html += '<button class="diff-view-mode-btn ' + (viewMode === 'split' ? 'active' : '') + '" onclick="setDiffViewMode(&quot;split&quot;)" data-action="setDiffViewMode" data-mode="split">Side-by-Side</button>';
      html += '<button class="diff-view-mode-btn ' + (viewMode === 'unified' ? 'active' : '') + '" onclick="setDiffViewMode(&quot;unified&quot;)" data-action="setDiffViewMode" data-mode="unified">Unified</button>';
      html += '</div>';
      html += '</div>';
      html += '</div>'; // End toolbar

      if (viewMode === 'split') {
        html += '<div class="diff-split-wrapper">';

        // Left Pane (Original)
        html += '<div class="diff-pane diff-pane-left" id="diffPaneLeft" onscroll="syncDiffScroll(this, &quot;diffPaneRight&quot;)">';
        html += '<div class="diff-pane-header">Original (Baseline): ' + escapeHtml(activeFile.displayPath) + '</div>';
        html += '<table class="diff-table"><tbody>';
        for (var hi = 0; hi < activeFile.hunks.length; hi++) {
          var hunk = activeFile.hunks[hi];
          html += '<tr><td colspan="2" class="diff-hunk-header">' + escapeHtml(hunk.header) + ' ' + escapeHtml(hunk.heading || '') + '</td></tr>';
          var rows = alignHunkLines(hunk.lines);
          for (var ri = 0; ri < rows.length; ri++) {
            var left = rows[ri].left;
            if (left.type === 'del') {
              html += '<tr class="diff-row-del"><td class="diff-gutter">' + (left.oldLine || left.lineNum || '') + '</td><td class="diff-content">' + escapeHtml(left.text || '') + '</td></tr>';
            } else if (left.type === 'context') {
              html += '<tr><td class="diff-gutter">' + (left.oldLine || left.lineNum || '') + '</td><td class="diff-content">' + escapeHtml(left.text || '') + '</td></tr>';
            } else {
              html += '<tr class="diff-row-empty"><td class="diff-gutter"></td><td class="diff-content">&nbsp;</td></tr>';
            }
          }
        }
        html += '</tbody></table>';
        html += '</div>'; // End left pane

        // Right Pane (Proposed)
        html += '<div class="diff-pane diff-pane-right" id="diffPaneRight" onscroll="syncDiffScroll(this, &quot;diffPaneLeft&quot;)">';
        html += '<div class="diff-pane-header">Proposed (Modified): ' + escapeHtml(activeFile.displayPath) + '</div>';
        html += '<table class="diff-table"><tbody>';
        for (var hri = 0; hri < activeFile.hunks.length; hri++) {
          var hunkR = activeFile.hunks[hri];
          html += '<tr><td colspan="2" class="diff-hunk-header">' + escapeHtml(hunkR.header) + ' ' + escapeHtml(hunkR.heading || '') + '</td></tr>';
          var rowsR = alignHunkLines(hunkR.lines);
          for (var rri = 0; rri < rowsR.length; rri++) {
            var right = rowsR[rri].right;
            if (right.type === 'add') {
              html += '<tr class="diff-row-add"><td class="diff-gutter">' + (right.newLine || right.lineNum || '') + '</td><td class="diff-content">' + escapeHtml(right.text || '') + '</td></tr>';
            } else if (right.type === 'context') {
              html += '<tr><td class="diff-gutter">' + (right.newLine || right.lineNum || '') + '</td><td class="diff-content">' + escapeHtml(right.text || '') + '</td></tr>';
            } else {
              html += '<tr class="diff-row-empty"><td class="diff-gutter"></td><td class="diff-content">&nbsp;</td></tr>';
            }
          }
        }
        html += '</tbody></table>';
        html += '</div>'; // End right pane

        html += '</div>'; // End diff-split-wrapper
      } else {
        html += '<div class="diff-unified-wrapper">';
        html += '<table class="diff-unified-table"><tbody>';
        for (var uhi = 0; uhi < activeFile.hunks.length; uhi++) {
          var hunkU = activeFile.hunks[uhi];
          html += '<tr><td colspan="4" class="diff-hunk-header">' + escapeHtml(hunkU.header) + ' ' + escapeHtml(hunkU.heading || '') + '</td></tr>';
          for (var uli = 0; uli < hunkU.lines.length; uli++) {
            var uline = hunkU.lines[uli];
            if (uline.type === 'del') {
              html += '<tr class="diff-row-del">' +
                      '<td class="diff-unified-gutter-old">' + (uline.oldLine || '') + '</td>' +
                      '<td class="diff-unified-gutter-new"></td>' +
                      '<td class="diff-unified-marker">-</td>' +
                      '<td class="diff-content">' + escapeHtml(uline.text || '') + '</td>' +
                      '</tr>';
            } else if (uline.type === 'add') {
              html += '<tr class="diff-row-add">' +
                      '<td class="diff-unified-gutter-old"></td>' +
                      '<td class="diff-unified-gutter-new">' + (uline.newLine || '') + '</td>' +
                      '<td class="diff-unified-marker">+</td>' +
                      '<td class="diff-content">' + escapeHtml(uline.text || '') + '</td>' +
                      '</tr>';
            } else {
              html += '<tr>' +
                      '<td class="diff-unified-gutter-old">' + (uline.oldLine || '') + '</td>' +
                      '<td class="diff-unified-gutter-new">' + (uline.newLine || '') + '</td>' +
                      '<td class="diff-unified-marker">&nbsp;</td>' +
                      '<td class="diff-content">' + escapeHtml(uline.text || '') + '</td>' +
                      '</tr>';
            }
          }
        }
        html += '</tbody></table>';
        html += '</div>'; // End diff-unified-wrapper
      }

      html += '</div>'; // End diff-review-container
      return html;
    }

    function formatDiff(diffText) {
      if (!diffText) return 'No diff available.';
      return diffText.split(String.fromCharCode(10)).map(function(line) {
        if (line.indexOf('+') === 0 && line.indexOf('+++') !== 0) {
          return '<span class="diff-line-add">' + escapeHtml(line) + '</span>';
        }
        if (line.indexOf('-') === 0 && line.indexOf('---') !== 0) {
          return '<span class="diff-line-del">' + escapeHtml(line) + '</span>';
        }
        return escapeHtml(line);
      }).join(String.fromCharCode(10));
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    document.addEventListener('click', function(ev) {
      const target = ev.target.closest('[data-action]');
      if (!target) return;
      const action = target.getAttribute('data-action');
      if (!action) return;

      switch (action) {
        case 'switchTab': {
          const tab = target.getAttribute('data-tab');
          if (tab) switchTab(tab);
          break;
        }
        case 'toggleGraph':
          toggleDependencyGraph();
          break;
        case 'gType': {
          const t = target.getAttribute('data-type');
          if (t) setGraphTypeFilter(t);
          break;
        }
        case 'gStatus': {
          const s = target.getAttribute('data-status');
          if (s) setGraphStatusFilter(s);
          break;
        }
        case 'runAnalysis':
          runAnalysis();
          break;
        case 'scanDependencies':
          scanDependencies();
          break;
        case 'validateExternalApis':
          validateExternalApis();
          break;
        case 'refresh':
          refreshDashboard();
          break;
        case 'filterIncidents': {
          const filter = target.getAttribute('data-filter');
          if (filter) setIncidentFilter(filter);
          break;
        }
        case 'createBaseline':
          createBaseline();
          break;
        case 'promptCreateBaseline':
          promptCreateBaseline();
          break;
        case 'promoteBaseline': {
          const bId = target.getAttribute('data-baseline-id');
          if (bId) promoteBaseline(bId);
          break;
        }
        case 'compareWithActive': {
          const bId = target.getAttribute('data-baseline-id');
          if (bId) compareWithActive(bId);
          break;
        }
        case 'scrollToCompareStudio':
          scrollToCompareStudio();
          break;
        case 'executeSelectedCompare':
          executeSelectedCompare();
          break;
        case 'closeBaselineDiff':
          closeBaselineDiff();
          break;
        case 'selectChange': {
          const changeId = target.getAttribute('data-change-id');
          if (changeId) selectIncident(changeId);
          break;
        }
        case 'proposeRepair': {
          const changeId = target.getAttribute('data-change-id') || (state.selectedChange ? state.selectedChange.id : null);
          if (changeId) proposeRepair(changeId);
          break;
        }
        case 'approveRepair': {
          const repairId = target.getAttribute('data-repair-id') || (state.currentRepair ? state.currentRepair.id : null);
          if (repairId) approveRepair(repairId);
          break;
        }
        case 'rejectRepair': {
          const repairId = target.getAttribute('data-repair-id') || (state.currentRepair ? state.currentRepair.id : null);
          if (repairId) rejectRepair(repairId);
          break;
        }
        case 'applyRepair': {
          const repairId = target.getAttribute('data-repair-id') || (state.currentRepair ? state.currentRepair.id : null);
          if (repairId) applyRepair(repairId);
          break;
        }
        case 'validateRepair': {
          const repairId = target.getAttribute('data-repair-id') || (state.currentRepair ? state.currentRepair.id : null);
          if (repairId) validateRepair(repairId);
          break;
        }
        case 'rollbackRepair': {
          const repairId = target.getAttribute('data-repair-id') || (state.currentRepair ? state.currentRepair.id : null);
          if (repairId) rollbackRepair(repairId);
          break;
        }
        case 'openNativeDiff': {
          const repairId = target.getAttribute('data-repair-id') || (state.currentRepair ? state.currentRepair.id : null);
          if (repairId) openNativeDiff(repairId);
          break;
        }
        case 'setDiffViewMode': {
          const mode = target.getAttribute('data-mode');
          if (mode) setDiffViewMode(mode);
          break;
        }
        case 'selectDiffFile': {
          const idx = parseInt(target.getAttribute('data-file-index') || '0', 10);
          selectDiffFile(idx);
          break;
        }
        case 'openFile': {
          const file = target.getAttribute('data-file');
          const line = parseInt(target.getAttribute('data-line') || '1', 10);
          if (file) openFile(file, line);
          break;
        }
        case 'setupEnv':
          setupEnv();
          break;
        case 'openChat':
          openChat();
          break;
        case 'cancelScan':
          cancelScan();
          break;
        case 'resetDemo':
          resetDemo();
          break;
      }
    });

    try {
      vscode.postMessage({ command: 'webviewReady' });
    } catch (e) {
      console.error('Failed to dispatch webviewReady message:', e);
    }
  </script>
</body>
</html>`;
  }
}
