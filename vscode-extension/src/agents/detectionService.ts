import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import { AgentRunner } from "./agentRunner";
import { GuardianClient, ChangeItem } from "../api/guardianClient";
import {
  CodebaseScanOptions,
  RepositoryInventoryResult,
  ContractDriftOptions,
  ContractDriftResult,
  ContractFinding,
  DetectionStateEvent,
  ExecutionState,
  ScanProgressEvent,
  LiveValidationOptions,
  LiveValidationReport,
} from "./detectionTypes";
import { getGuardianConfig } from "../config";

export class DetectionService {
  private _onDidChangeState = new vscode.EventEmitter<DetectionStateEvent>();
  public readonly onDidChangeState = this._onDidChangeState.event;

  private activeScanCts?: vscode.CancellationTokenSource;

  private _codebaseState: {
    state: ExecutionState;
    result?: RepositoryInventoryResult;
    error?: string;
    progress?: ScanProgressEvent;
    lastRun?: Date;
  } = { state: "idle" };

  private _driftState: {
    state: ExecutionState;
    result?: ContractDriftResult;
    error?: string;
    lastRun?: Date;
  } = { state: "idle" };

  private _liveValidationState: {
    state: ExecutionState;
    result?: LiveValidationReport;
    error?: string;
    lastRun?: Date;
  } = { state: "idle" };

  constructor(
    private agentRunner: AgentRunner,
    private client: GuardianClient,
    private workspaceRoot: string,
    private outputChannel: vscode.OutputChannel
  ) {}

  public getLiveValidationState() {
    return { ...this._liveValidationState };
  }

  public getLastLiveValidationResult(): LiveValidationReport | undefined {
    return this._liveValidationState.result;
  }

  public getCodebaseState() {
    return { ...this._codebaseState };
  }

  public getDriftState() {
    return { ...this._driftState };
  }

  public getLastInventory(): RepositoryInventoryResult | undefined {
    return this._codebaseState.result;
  }

  public getLastDriftResult(): ContractDriftResult | undefined {
    return this._driftState.result;
  }

  public cancelCodebaseScan(): boolean {
    if (this.activeScanCts) {
      this.activeScanCts.cancel();
      this.outputChannel.appendLine("[DetectionService] User requested codebase scan cancellation.");
      return true;
    }
    return false;
  }

  /**
   * Executes codebase repository intelligence scan with asynchronous lifecycle.
   */
  public async scanCodebase(
    targetPath?: string,
    options: Partial<CodebaseScanOptions> = {}
  ): Promise<RepositoryInventoryResult> {
    const resolvedTarget = targetPath || this.workspaceRoot;

    if (!fs.existsSync(resolvedTarget)) {
      const err = `Scanned directory does not exist: ${resolvedTarget}`;
      this._codebaseState = { state: "failed", error: err, lastRun: new Date() };
      this._onDidChangeState.fire({ capability: "codebase_scan", state: "failed", error: err });
      throw new Error(err);
    }

    const cts = new vscode.CancellationTokenSource();
    if (options.cancellationToken) {
      options.cancellationToken.onCancellationRequested(() => cts.cancel());
    }
    this.activeScanCts = cts;

    const initialProgress: ScanProgressEvent = {
      phase: "starting",
      message: `Starting codebase scan for ${path.basename(resolvedTarget)}...`,
      elapsedSeconds: 0,
    };
    this._codebaseState = { state: "running", progress: initialProgress, lastRun: new Date() };
    this._onDidChangeState.fire({
      capability: "codebase_scan",
      state: "running",
      progress: initialProgress,
    });

    try {
      const config = getGuardianConfig();
      const outDir = options.outputDir || path.join(this.workspaceRoot, "reports", "repository-inventory");

      const result = await this.agentRunner.runCodebaseScan(this.workspaceRoot, {
        repositoryPath: resolvedTarget,
        outputDir: outDir,
        mode: options.mode || (config.detectionMode as any) || "algorithmic",
        enrichOpenApi: options.enrichOpenApi !== false,
        timeoutSeconds: options.timeoutSeconds || 90,
        cancellationToken: cts.token,
        onProgress: (prog) => {
          this._codebaseState = {
            ...this._codebaseState,
            progress: prog,
          };
          this._onDidChangeState.fire({
            capability: "codebase_scan",
            state: "running",
            progress: prog,
          });
          options.onProgress?.(prog);
        },
        onLog: options.onLog,
      });

      this._codebaseState = {
        state: "succeeded",
        result,
        lastRun: new Date(),
      };

      // Ingest scan run into backend history and incidents if backend is accessible
      try {
        const config = getGuardianConfig();
        const shouldSync = options.syncBackend !== undefined ? options.syncBackend : config.autoSyncBackend;
        if (shouldSync) {
          const projects = await this.client.getProjects();
          if (projects && projects.length > 0) {
            const pId = options.projectId || config.projectId || projects[0].id;
            const findings: any[] = [];
            if (result.discrepancies && Array.isArray(result.discrepancies)) {
              for (const disc of result.discrepancies) {
                findings.push({
                  title: disc.message || `API Discrepancy on ${disc.endpoint || disc.path || "endpoint"}`,
                  severity: disc.severity || "medium",
                  category: "drift",
                  provenance: "codebase_scanner",
                  fingerprint: disc.fingerprint || `codebase:${disc.endpoint || disc.path || ""}:${disc.type || ""}`,
                  confidence: 0.9,
                  description: disc.details || disc.message || "Discrepancy detected during repository scan",
                  evidence: disc,
                });
              }
            }
            if (result.undocumented_endpoints && Array.isArray(result.undocumented_endpoints)) {
              for (const undoc of result.undocumented_endpoints) {
                const epPath = undoc.path || undoc.endpoint || "/";
                const epMethod = (undoc.method || "ALL").toUpperCase();
                findings.push({
                  title: `Undocumented endpoint ${epMethod} ${epPath}`,
                  severity: "medium",
                  category: "undocumented_api",
                  provenance: "codebase_scanner",
                  fingerprint: `undoc:${epMethod}:${epPath}`,
                  confidence: 0.95,
                  description: `Discovered endpoint ${epMethod} ${epPath} in source code but missing from OpenAPI specification.`,
                  evidence: undoc,
                });
              }
            }
            const clientRunId = `scan-codebase-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
            await this.client.ingestScanRun(pId, {
              client_run_id: clientRunId,
              scan_type: "codebase",
              detection_mode: options.mode || config.detectionMode || "algorithmic",
              capabilities_executed: ["codebase_scanner"],
              summary_counts: {
                discovered_endpoints: result.endpoints?.length || result.discovered_endpoints || 0,
                discrepancies: (result.discrepancies || []).length,
                undocumented_endpoints: (result.undocumented_endpoints || []).length,
                findings_total: findings.length,
              },
              findings,
              inventory: result,
              status: "succeeded",
            });
            this.outputChannel.appendLine(`[DetectionService] Ingested scan run ${clientRunId} to project ${pId}`);
          }
        }
      } catch (ingestErr: any) {
        this.outputChannel.appendLine(`[DetectionService] Offline/Ingest notice: ${ingestErr.message}`);
      }

      this._onDidChangeState.fire({
        capability: "codebase_scan",
        state: "succeeded",
        codebaseResult: result,
      });

      return result;
    } catch (err: any) {
      const isCanceled =
        cts.token.isCancellationRequested ||
        options.cancellationToken?.isCancellationRequested ||
        err.message?.includes("cancelled by the user");
      const finalState: ExecutionState = isCanceled ? "canceled" : "failed";
      const errorMsg = isCanceled ? "Codebase scan canceled." : err.message;

      this._codebaseState = {
        state: finalState,
        error: errorMsg,
        lastRun: new Date(),
      };

      this._onDidChangeState.fire({
        capability: "codebase_scan",
        state: finalState,
        error: errorMsg,
      });

      throw err;
    } finally {
      this.activeScanCts = undefined;
      cts.dispose();
    }
  }

  /**
   * Executes contract drift detection between baseline and current OpenAPI specifications.
   */
  public async detectContractDrift(
    options: ContractDriftOptions
  ): Promise<ContractDriftResult> {
    if (!options.baselinePath || !fs.existsSync(options.baselinePath)) {
      const err = `Baseline contract file not found: ${options.baselinePath || "(not provided)"}`;
      this._driftState = { state: "failed", error: err, lastRun: new Date() };
      this._onDidChangeState.fire({ capability: "contract_drift", state: "failed", error: err });
      throw new Error(err);
    }

    if (!options.currentPath || !fs.existsSync(options.currentPath)) {
      const err = `Current contract file not found: ${options.currentPath || "(not provided)"}`;
      this._driftState = { state: "failed", error: err, lastRun: new Date() };
      this._onDidChangeState.fire({ capability: "contract_drift", state: "failed", error: err });
      throw new Error(err);
    }

    this._driftState = { state: "running", lastRun: new Date() };
    this._onDidChangeState.fire({ capability: "contract_drift", state: "running" });

    try {
      const config = getGuardianConfig();
      const isSyncExplicit = options.syncBackend === true;
      let shouldSync = options.syncBackend !== undefined ? options.syncBackend : config.autoSyncBackend;

      let syncProjectId = (options.projectId || config.projectId || "").trim();
      let syncDependencyId = (options.dependencyId || config.dependencyId || "").trim();

      if (shouldSync) {
        try {
          const resolved = await this.resolveSyncIdentifiers(syncProjectId, syncDependencyId);
          syncProjectId = resolved.projectId;
          syncDependencyId = resolved.dependencyId;
        } catch (syncErr: any) {
          if (isSyncExplicit) {
            // Synchronization was explicitly required; do not silently skip
            throw syncErr;
          } else {
            // Auto-sync was default config; preserve local offline usability
            this.outputChannel.appendLine(`[DetectionService] Backend sync skipped: ${syncErr.message}`);
            shouldSync = false;
          }
        }
      }

      const result = await this.agentRunner.runDetection(this.workspaceRoot, {
        baselinePath: options.baselinePath,
        currentPath: options.currentPath,
        mode: options.mode || (config.detectionMode as any) || "algorithmic",
        syncBackend: shouldSync,
        projectId: syncProjectId,
        dependencyId: syncDependencyId,
        proposeRepairs: options.proposeRepairs,
        testCmd: options.testCmd,
        outputFile: options.outputFile,
        insightsOutputFile: options.insightsOutputFile,
        timeoutSeconds: options.timeoutSeconds || 60,
        cancellationToken: options.cancellationToken,
      });

      this._driftState = {
        state: "succeeded",
        result,
        lastRun: new Date(),
      };

      // Ingest contract drift scan into backend history and incidents
      try {
        if (shouldSync && syncProjectId) {
          const findings: any[] = [];
          for (const f of result.findings || []) {
            findings.push({
              title: f.message || `Contract drift on ${f.path || ""}`,
              severity: f.severity || "high",
              category: "contract_drift",
              provenance: "external_api_drift",
              confidence: f.confidence !== undefined ? f.confidence : 0.95,
              fingerprint: f.fingerprint || `drift:${f.rule_id || ""}:${f.method || ""}:${f.path || ""}`,
              description: f.message,
              recommended_action: f.recommended_action,
              evidence: f.evidence || {},
            });
          }
          const clientRunId = `scan-drift-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
          await this.client.ingestScanRun(syncProjectId, {
            client_run_id: clientRunId,
            scan_type: "contract_drift",
            detection_mode: options.mode || config.detectionMode || "algorithmic",
            capabilities_executed: ["contract_drift"],
            summary_counts: {
              findings_total: findings.length,
              breaking_changes: findings.filter((x) => x.severity === "high" || x.severity === "critical").length,
            },
            findings,
            status: "succeeded",
          });
          this.outputChannel.appendLine(`[DetectionService] Ingested contract drift scan ${clientRunId} to project ${syncProjectId}`);
        }
      } catch (ingestErr: any) {
        this.outputChannel.appendLine(`[DetectionService] Offline/Ingest notice: ${ingestErr.message}`);
      }

      this._onDidChangeState.fire({
        capability: "contract_drift",
        state: "succeeded",
        driftResult: result,
      });

      return result;
    } catch (err: any) {
      const isCanceled =
        options.cancellationToken?.isCancellationRequested ||
        err.message?.includes("cancelled by the user");
      const finalState: ExecutionState = isCanceled ? "canceled" : "failed";
      const errorMsg = isCanceled ? "Contract drift detection canceled." : err.message;

      this._driftState = {
        state: finalState,
        error: errorMsg,
        lastRun: new Date(),
      };

      this._onDidChangeState.fire({
        capability: "contract_drift",
        state: finalState,
        error: errorMsg,
      });

      throw err;
    }
  }

  /**
   * Executes external API intelligence and live validation against configured endpoints.
   */
  public async validateExternalApis(
    options: Partial<LiveValidationOptions> = {}
  ): Promise<LiveValidationReport> {
    this._liveValidationState = { state: "running", lastRun: new Date() };
    this._onDidChangeState.fire({ capability: "live_validation", state: "running" });

    try {
      const config = getGuardianConfig();
      const report = await this.agentRunner.runLiveValidation(this.workspaceRoot, {
        ...options,
        mode: options.mode || (config.detectionMode as any) || "algorithmic",
      });

      this._liveValidationState = {
        state: "succeeded",
        result: report,
        lastRun: new Date(),
      };

      this._onDidChangeState.fire({
        capability: "live_validation",
        state: "succeeded",
        liveValidationResult: report,
      });

      return report;
    } catch (err: any) {
      const isCanceled =
        options.cancellationToken?.isCancellationRequested ||
        err.message?.includes("cancelled by the user");
      const finalState: ExecutionState = isCanceled ? "canceled" : "failed";
      const errorMsg = isCanceled ? "Live API validation canceled." : err.message;

      this._liveValidationState = {
        state: finalState,
        error: errorMsg,
        lastRun: new Date(),
      };

      this._onDidChangeState.fire({
        capability: "live_validation",
        state: finalState,
        error: errorMsg,
      });

      throw err;
    }
  }

  /**
   * Executes unified end-to-end analysis:
   * 1. Codebase repository intelligence scan
   * 2. Contract drift detection (if contracts found)
   * 3. External API live validation (if dependency-guardian.yml found)
   */
  public async runUnifiedAnalysis(
    options: {
      mode?: "algorithmic" | "ai" | "hybrid";
      cancellationToken?: vscode.CancellationToken;
    } = {}
  ): Promise<{
    codebase: RepositoryInventoryResult | null;
    drift: ContractDriftResult | null;
    liveValidation: LiveValidationReport | null;
  }> {
    const config = getGuardianConfig();
    const effectiveMode = options.mode || config.detectionMode || "algorithmic";

    this._onDidChangeState.fire({ capability: "unified_analysis", state: "running" });

    let codebase: RepositoryInventoryResult | null = null;
    let drift: ContractDriftResult | null = null;
    let liveValidation: LiveValidationReport | null = null;

    // 1. Codebase scan
    try {
      codebase = await this.scanCodebase(this.workspaceRoot, {
        mode: effectiveMode,
        cancellationToken: options.cancellationToken,
      });
    } catch (err: any) {
      this.outputChannel.appendLine(`[Unified Analysis] Codebase scan notice: ${err.message}`);
    }

    // 2. Contract drift (find baseline and current specs if available)
    const driftCandidates = [
      {
        base: path.join(this.workspaceRoot, "demo-app", "specs", "users-api-v1.json"),
        curr: path.join(this.workspaceRoot, "demo-app", "specs", "users-api-v2.json"),
      },
      {
        base: path.join(this.workspaceRoot, "demo", "sample-api", "openapi-v1.json"),
        curr: path.join(this.workspaceRoot, "demo", "sample-api", "openapi-v2.json"),
      },
      {
        base: path.join(this.workspaceRoot, "specs", "baseline.json"),
        curr: path.join(this.workspaceRoot, "specs", "current.json"),
      },
    ];

    const foundSpecPair = driftCandidates.find((c) => fs.existsSync(c.base) && fs.existsSync(c.curr));
    if (foundSpecPair) {
      try {
        drift = await this.detectContractDrift({
          baselinePath: foundSpecPair.base,
          currentPath: foundSpecPair.curr,
          mode: effectiveMode,
          cancellationToken: options.cancellationToken,
        });
      } catch (err: any) {
        this.outputChannel.appendLine(`[Unified Analysis] Drift detection notice: ${err.message}`);
      }
    }

    // 3. Live validation (check for dependency-guardian.yml)
    const liveCfgCandidates = [
      path.join(this.workspaceRoot, "dependency-guardian.yml"),
      path.join(this.workspaceRoot, ".dependency-guardian.yml"),
      path.join(this.workspaceRoot, "demo-app", "dependency-guardian.yml"),
    ];
    const foundLiveCfg = liveCfgCandidates.find((c) => fs.existsSync(c));
    if (foundLiveCfg) {
      try {
        liveValidation = await this.validateExternalApis({
          configPath: foundLiveCfg,
          mode: effectiveMode,
          cancellationToken: options.cancellationToken,
        });
      } catch (err: any) {
        this.outputChannel.appendLine(`[Unified Analysis] Live validation notice: ${err.message}`);
      }
    }

    this._onDidChangeState.fire({
      capability: "unified_analysis",
      state: "succeeded",
      codebaseResult: codebase || undefined,
      driftResult: drift || undefined,
      liveValidationResult: liveValidation || undefined,
    });

    return { codebase, drift, liveValidation };
  }

  /**
   * Maps ContractFindings to standard ChangeItems used by the dashboard and tree views.
   */
  public mapFindingsToChanges(findings: ContractFinding[], dependencyId?: string): ChangeItem[] {
    return findings.map((f) => {
      let severity: "low" | "medium" | "high" | "critical" | "blocked" = "medium";
      if (f.compatibility === "breaking" || f.severity === "critical" || f.severity === "high") {
        severity = f.severity === "critical" ? "critical" : "high";
      } else if (f.compatibility === "potentially_breaking") {
        severity = "medium";
      } else {
        severity = "low";
      }

      // Check if evidence links to any affected files
      const affectedFiles: string[] = [];
      if (f.evidence && typeof f.evidence === "object") {
        if (f.evidence.file) {
          affectedFiles.push(String(f.evidence.file));
        }
        if (Array.isArray(f.evidence.affected_files)) {
          for (const af of f.evidence.affected_files) {
            if (typeof af === "string" && !affectedFiles.includes(af)) {
              affectedFiles.push(af);
            }
          }
        }
      }

      return {
        id: f.id,
        scan_id: f.id,
        dependency_id: dependencyId || f.path || "external-api",
        probe_id: `${f.method || "ALL"} ${f.path}`,
        change_type: f.rule_id,
        severity,
        evidence: {
          ...f.evidence,
          message: f.message,
          rule_id: f.rule_id,
          compatibility: f.compatibility,
          provenance: f.provenance || "contract_diff",
          confidence: f.confidence !== undefined ? f.confidence : 1.0,
          recommended_action: f.recommended_action || null,
          ai_reasoning: f.ai_reasoning,
        },
        status: f.compatibility,
        created_at: new Date().toISOString(),
        affected_files: affectedFiles,
        affected_workflows: [],
      };
    });
  }

  /**
   * Discovers and extracts workspace configuration metadata from dependency-guardian.yml if present.
   */
  public extractWorkspaceMetadata(): {
    projectName?: string;
    dependencyName?: string;
    dependencyBaseUrl?: string;
  } {
    const candidates = [
      path.join(this.workspaceRoot, "dependency-guardian.yml"),
      path.join(this.workspaceRoot, ".dependency-guardian.yml"),
      path.join(this.workspaceRoot, "demo-app", "dependency-guardian.yml"),
      path.join(this.workspaceRoot, "demo", "sample-api", "dependency-guardian.yml"),
    ];

    for (const cand of candidates) {
      if (fs.existsSync(cand)) {
        try {
          const raw = fs.readFileSync(cand, "utf-8");
          const pMatch = raw.match(/^\s*project:\s*\n(?:\s+.*\n)*?\s+name:\s*["']?([^"'\n\r#]+)["']?/m);
          const projectName = pMatch ? pMatch[1].trim() : undefined;

          const depIdMatch = raw.match(/^\s*-\s*id:\s*["']?([^"'\n\r#]+)["']?/m);
          const depNameMatch = raw.match(/^\s*name:\s*["']?([^"'\n\r#]+)["']?/m);
          const urlMatch = raw.match(/^\s*base_url:\s*["']?([^"'\n\r#]+)["']?/m);

          const dependencyName =
            (depNameMatch ? depNameMatch[1].trim() : undefined) ||
            (depIdMatch ? depIdMatch[1].trim() : undefined);
          const dependencyBaseUrl = urlMatch ? urlMatch[1].trim() : undefined;

          return { projectName, dependencyName, dependencyBaseUrl };
        } catch {
          // ignore read error
        }
      }
    }

    return {
      projectName: path.basename(this.workspaceRoot) || undefined,
      dependencyName: undefined,
      dependencyBaseUrl: undefined,
    };
  }

  /**
   * Resolves, registers, and persists Project ID and Dependency ID required for backend synchronization.
   */
  public async resolveSyncIdentifiers(
    preferredProjectId?: string,
    preferredDependencyId?: string
  ): Promise<{ projectId: string; dependencyId: string }> {
    const config = getGuardianConfig();
    let projectId = (preferredProjectId || config.projectId || "").trim();
    let dependencyId = (preferredDependencyId || config.dependencyId || "").trim();

    // If both IDs already provided/configured, return immediately
    if (projectId && dependencyId) {
      return { projectId, dependencyId };
    }

    // Query backend to discover or register missing IDs
    let projects: any[] = [];
    try {
      projects = await this.client.getProjects();
    } catch (err: any) {
      throw new Error(
        `Backend synchronization requires valid Project ID and Dependency ID, but backend is unreachable at ${this.client.getBaseUrl()} (${err.message}). ` +
        `Please ensure the Dependency Guardian backend service is running, or disable backend synchronization.`
      );
    }

    const wsMeta = this.extractWorkspaceMetadata();

    // 1. Resolve Project ID
    if (!projectId) {
      const targetProjectName = wsMeta.projectName || path.basename(this.workspaceRoot) || "Default Project";
      const matched = projects.find(
        (p) => p.name && p.name.toLowerCase() === targetProjectName.toLowerCase()
      );

      if (matched && matched.id) {
        projectId = matched.id;
      } else if (projects.length > 0 && projects[0].id) {
        projectId = projects[0].id;
      } else {
        try {
          const created = await this.client.createProject(
            targetProjectName,
            "Auto-registered project from VS Code workspace"
          );
          projectId = created.id;
        } catch (createErr: any) {
          throw new Error(
            `Backend synchronization requires a Project ID, but registering project '${targetProjectName}' on ${this.client.getBaseUrl()} failed: ${createErr.message}`
          );
        }
      }

      // Persist to workspace settings if available
      if (projectId && typeof vscode !== "undefined" && vscode?.workspace) {
        try {
          const wsCfg = vscode.workspace.getConfiguration("dependencyGuardian");
          await wsCfg.update("projectId", projectId, vscode.ConfigurationTarget.Workspace);
        } catch {}
      }
    }

    // 2. Resolve Dependency ID
    if (!dependencyId) {
      let deps: any[] = [];
      try {
        deps = await this.client.getProjectDependencies(projectId);
      } catch {
        deps = [];
      }

      const targetDepName = wsMeta.dependencyName || "Root API";
      const matchedDep = deps.find(
        (d) =>
          (d.name && d.name.toLowerCase() === targetDepName.toLowerCase()) ||
          (d.id && d.id.toLowerCase() === targetDepName.toLowerCase())
      );

      if (matchedDep && matchedDep.id) {
        dependencyId = matchedDep.id;
      } else if (deps.length > 0 && deps[0].id) {
        dependencyId = deps[0].id;
      } else {
        try {
          const createdDep = await this.client.createDependency(projectId, {
            name: targetDepName,
            kind: "rest_api",
            base_url: wsMeta.dependencyBaseUrl,
          });
          dependencyId = createdDep.id;
        } catch (createDepErr: any) {
          throw new Error(
            `Backend synchronization requires a Dependency ID, but registering dependency '${targetDepName}' for project '${projectId}' on ${this.client.getBaseUrl()} failed: ${createDepErr.message}`
          );
        }
      }

      // Persist to workspace settings if available
      if (dependencyId && typeof vscode !== "undefined" && vscode?.workspace) {
        try {
          const wsCfg = vscode.workspace.getConfiguration("dependencyGuardian");
          await wsCfg.update("dependencyId", dependencyId, vscode.ConfigurationTarget.Workspace);
        } catch {}
      }
    }

    if (!projectId || !dependencyId) {
      throw new Error(
        `Backend synchronization failed: unable to resolve required Project ID and Dependency ID ` +
        `(projectId='${projectId}', dependencyId='${dependencyId}'). Check backend at ${this.client.getBaseUrl()}.`
      );
    }

    return { projectId, dependencyId };
  }
}
