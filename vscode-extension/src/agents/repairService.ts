import * as fs from "fs";
import * as path from "path";
import * as vscode from "vscode";
import { GuardianClient, RepairProposal, ValidationResult, ChangeItem } from "../api/guardianClient";
import { AgentRunner, RepairOptions } from "./agentRunner";
import { ContractFinding } from "./detectionTypes";
import {
  PatchIntegrityStore,
  patchIntegrityStore,
  ReviewedPatchRecord,
  VerificationResult,
  validateWorkspacePath,
  extractChangeSet,
} from "../patchIntegrity";
import { getGuardianConfig } from "../config";

export interface RepairGenerationOptions {
  provider?: "deterministic" | "ollama";
  testCommand?: string;
  targetFile?: string;
  syncBackend?: boolean;
  timeoutSeconds?: number;
  cancellationToken?: vscode.CancellationToken;
}

export interface RepairLifecycleEvent {
  stage: "generating" | "proposed" | "validating" | "validated" | "approved" | "rejected" | "applied" | "error";
  repairId?: string;
  findingId?: string;
  message: string;
  proposal?: RepairProposal;
  validation?: ValidationResult;
  error?: string;
}

export class RepairService {
  private agentRunner: AgentRunner;
  private client: GuardianClient;
  private integrityStore: PatchIntegrityStore;
  private workspaceRoot: string;
  private outputChannel: vscode.OutputChannel;

  private _onLifecycleEvent: vscode.EventEmitter<RepairLifecycleEvent> =
    new vscode.EventEmitter<RepairLifecycleEvent>();
  public readonly onLifecycleEvent: vscode.Event<RepairLifecycleEvent> =
    this._onLifecycleEvent.event;

  constructor(
    agentRunner: AgentRunner,
    client: GuardianClient,
    workspaceRoot: string,
    outputChannel: vscode.OutputChannel,
    integrityStore: PatchIntegrityStore = patchIntegrityStore
  ) {
    this.agentRunner = agentRunner;
    this.client = client;
    this.workspaceRoot = workspaceRoot;
    this.outputChannel = outputChannel;
    this.integrityStore = integrityStore;
  }

  public setWorkspaceRoot(root: string): void {
    this.workspaceRoot = root;
  }

  /**
   * Normalizes any finding (ChangeItem, ContractFinding, or backend incident) into standard FindingInput payload.
   */
  public normalizeFindingInput(
    findingOrIncident: ChangeItem | ContractFinding | any
  ): {
    id: string;
    rule_id: string;
    path: string;
    method?: string;
    schema_location?: string;
    previous_value?: any;
    current_value?: any;
    message?: string;
    evidence: Record<string, any>;
    compatibility?: string;
    severity?: string;
  } {
    const raw = findingOrIncident || {};
    const ev = raw.evidence || (raw.metadata_json && raw.metadata_json.evidence) || {};

    const id = raw.id || raw.fingerprint || `find_${Date.now()}`;
    const rule_id =
      raw.rule_id ||
      ev.rule_id ||
      raw.change_type ||
      raw.title ||
      "RULE-CONTRACT-DRIFT";

    const pathVal =
      raw.path ||
      ev.path ||
      ev.endpoint ||
      (typeof raw.dependency_id === "string" && raw.dependency_id.startsWith("/") ? raw.dependency_id : "/");

    const methodVal =
      raw.method ||
      ev.method ||
      (typeof raw.probe_id === "string" && raw.probe_id.includes(" ") ? raw.probe_id.split(" ")[0] : undefined);

    const schemaLocation =
      raw.schema_location ||
      ev.schema_location ||
      ev.removed_property ||
      ev.field ||
      "";

    const prevVal = raw.previous_value !== undefined ? raw.previous_value : ev.previous_value;
    const currVal = raw.current_value !== undefined ? raw.current_value : ev.current_value;

    const msg =
      raw.message ||
      raw.description ||
      raw.recommended_action ||
      `Contract drift detected on endpoint ${pathVal} (${rule_id})`;

    const sev = (raw.severity || "high").toLowerCase();
    const comp =
      raw.compatibility ||
      (sev === "critical" || sev === "high" || sev === "blocked"
        ? "breaking"
        : "potentially_breaking");

    return {
      id,
      rule_id,
      path: pathVal,
      method: methodVal,
      schema_location: schemaLocation,
      previous_value: prevVal,
      current_value: currVal,
      message: msg,
      evidence: ev,
      compatibility: comp,
      severity: sev,
    };
  }

  /**
   * Generates a structured repair proposal for a finding using the Repair Agent.
   * Never modifies workspace source files during proposal generation.
   */
  public async generateRepairProposal(
    findingOrIncident: ChangeItem | ContractFinding | any,
    options: RepairGenerationOptions = {}
  ): Promise<RepairProposal> {
    const findingInput = this.normalizeFindingInput(findingOrIncident);
    const incidentId = findingOrIncident.id || findingInput.id;

    this.outputChannel.appendLine(`\n[RepairService] Generating proposal for finding '${findingInput.id}' (${findingInput.rule_id})`);
    this._onLifecycleEvent.fire({
      stage: "generating",
      findingId: findingInput.id,
      message: `Analyzing finding ${findingInput.id.slice(0, 8)} and generating compatibility repair...`,
    });

    // Determine target file from affected_files or evidence
    let targetFile = options.targetFile;
    if (!targetFile) {
      if (Array.isArray(findingOrIncident.affected_files) && findingOrIncident.affected_files.length > 0) {
        targetFile = findingOrIncident.affected_files[0];
      } else if (findingInput.evidence && findingInput.evidence.target_file) {
        targetFile = findingInput.evidence.target_file;
      }
    }

    const config = getGuardianConfig();
    const runnerOptions: RepairOptions = {
      incidentId: incidentId,
      findingPathOrJson: JSON.stringify(findingInput),
      targetFile: targetFile,
      testCommand: options.testCommand,
      provider: options.provider || "deterministic",
      syncBackend: options.syncBackend !== undefined ? options.syncBackend : config.autoSyncBackend,
      timeoutSeconds: options.timeoutSeconds || 60,
      cancellationToken: options.cancellationToken,
    };

    let rawResult: any;
    try {
      rawResult = await this.agentRunner.runRepair(this.workspaceRoot, runnerOptions);
    } catch (err: any) {
      this.outputChannel.appendLine(`[RepairService Error] Agent execution failed: ${err.message}`);
      this._onLifecycleEvent.fire({
        stage: "error",
        findingId: findingInput.id,
        message: `Repair agent failed: ${err.message}`,
        error: err.message,
      });
      throw err;
    }

    // Map into RepairProposal format
    const proposalId = rawResult.repair_id || `rep_${Date.now()}`;
    const fileChanges = rawResult.file_changes || [];
    const primaryChange = fileChanges.length > 0 ? fileChanges[0] : null;

    const proposal: RepairProposal = {
      id: proposalId,
      change_id: incidentId,
      repair_type: rawResult.strategy || "compatibility_adapter",
      target_file: rawResult.target_file || (primaryChange ? primaryChange.file_path : (targetFile || "")),
      original_code_snippet: primaryChange ? primaryChange.original_content : (rawResult.original_content || ""),
      proposed_code_snippet: primaryChange ? primaryChange.proposed_content : (rawResult.proposed_content || ""),
      diff: rawResult.diff || (primaryChange ? primaryChange.diff : ""),
      evidence: {
        ...findingInput.evidence,
        target_file: rawResult.target_file || targetFile,
        file_changes: fileChanges,
        likely_root_cause: rawResult.likely_root_cause,
        affected_symbols: rawResult.affected_symbols || [],
        rationale: rawResult.rationale,
        assumptions: rawResult.assumptions || [],
        risks: rawResult.risks || [],
        alternatives_considered: rawResult.alternatives_considered || [],
        line_ranges: rawResult.line_ranges || [],
        suggested_validation_command: rawResult.suggested_validation_command || options.testCommand,
      },
      assumptions: rawResult.assumptions || [],
      confidence: rawResult.validation?.status === "success" ? 0.98 : 0.90,
      status: rawResult.status || "proposed",
      created_at: rawResult.created_at || new Date().toISOString(),
      error_message: rawResult.error_message,
      likely_root_cause: rawResult.likely_root_cause,
      affected_symbols: rawResult.affected_symbols || [],
      rationale: rawResult.rationale || rawResult.explanation,
      risks: rawResult.risks || [],
      alternatives_considered: rawResult.alternatives_considered || [],
      line_ranges: rawResult.line_ranges || [],
      suggested_validation_command: rawResult.suggested_validation_command || options.testCommand,
    };

    this.outputChannel.appendLine(
      `[RepairService] Proposal generated: '${proposal.id}' (Status: ${proposal.status}, Files: ${fileChanges.length})`
    );

    this._onLifecycleEvent.fire({
      stage: "proposed",
      repairId: proposal.id,
      findingId: findingInput.id,
      message: `Proposal created (Status: ${proposal.status})`,
      proposal,
    });

    return proposal;
  }

  /**
   * Records explicit human diff review in the PatchIntegrityStore and snapshots original disk file state.
   */
  public recordDiffReview(proposal: RepairProposal): ReviewedPatchRecord {
    return this.integrityStore.recordReview(proposal, this.workspaceRoot);
  }

  /**
   * Approves a repair proposal with strict binding to the reviewed patch hash.
   * Requires explicit prior diff review and confirms backend synchronization.
   */
  public async approveRepairProposal(
    proposal: RepairProposal,
    reviewerId: string = "vscode-developer",
    comment?: string
  ): Promise<string> {
    const record = this.integrityStore.getRecord(proposal.id);
    if (!record || !record.isDiffReviewed) {
      throw new Error(
        `Cannot approve repair: Proposal '${proposal.id.slice(0, 8)}' must be reviewed before approval.`
      );
    }

    const patchHash = record.patchHash;

    // Synchronize approval with backend
    try {
      await this.client.approveRepair(
        proposal.id,
        reviewerId,
        comment || `Approved patch hash: ${patchHash}`
      );
    } catch (backendErr: any) {
      this.integrityStore.revokeApproval(proposal.id);
      this.outputChannel.appendLine(
        `[RepairService] Backend rejected approval for proposal '${proposal.id}': ${backendErr.message}`
      );
      this._onLifecycleEvent.fire({
        stage: "error",
        repairId: proposal.id,
        message: `Backend approval rejected: ${backendErr.message}`,
        error: backendErr.message,
      });
      throw backendErr;
    }

    // Bind approval locally only after backend confirmation
    const approvedHash = this.integrityStore.recordApproval(proposal.id);
    proposal.status = "approved";

    this.outputChannel.appendLine(
      `[RepairService] Proposal '${proposal.id}' approved (Bound Patch Hash: ${approvedHash})`
    );

    this._onLifecycleEvent.fire({
      stage: "approved",
      repairId: proposal.id,
      message: `Proposal approved with hash ${approvedHash.slice(0, 8)}`,
      proposal,
    });

    return approvedHash;
  }

  /**
   * Rejects a repair proposal locally and on the backend.
   */
  public async rejectRepairProposal(
    proposalId: string,
    reason: string = "Rejected by developer."
  ): Promise<void> {
    try {
      await this.client.rejectRepair(proposalId);
    } catch (err: any) {
      this.outputChannel.appendLine(`[RepairService Warning] Backend reject call returned: ${err.message}`);
    }

    this.integrityStore.revokeApproval(proposalId);

    this._onLifecycleEvent.fire({
      stage: "rejected",
      repairId: proposalId,
      message: `Proposal rejected: ${reason}`,
    });
  }

  /**
   * Runs isolated AST & test validation for candidate repair proposal.
   */
  public async validateRepairProposal(
    proposalId: string,
    testCommand?: string
  ): Promise<ValidationResult> {
    this._onLifecycleEvent.fire({
      stage: "validating",
      repairId: proposalId,
      message: "Executing validation in isolated sandbox...",
    });

    try {
      const result = await this.client.validateRepair(proposalId);
      this._onLifecycleEvent.fire({
        stage: "validated",
        repairId: proposalId,
        message: `Validation ${result.status.toUpperCase()} (${result.duration_ms}ms)`,
        validation: result,
      });
      return result;
    } catch (err: any) {
      this._onLifecycleEvent.fire({
        stage: "error",
        repairId: proposalId,
        message: `Validation execution failed: ${err.message}`,
        error: err.message,
      });
      throw err;
    }
  }

  /**
   * Safely applies the approved repair changes to workspace files.
   * Verifies backend approval status, canonical patch hash, workspace boundaries, and TOCTOU disk state.
   * Executes multi-file atomic write with full rollback protection.
   */
  public async applyApprovedRepair(
    proposal: RepairProposal,
    agentId: string = "vscode-developer"
  ): Promise<string[]> {
    // 1. Backend verification: proposal must be in approved status on backend
    let liveProposal: RepairProposal;
    try {
      liveProposal = await this.client.getRepair(proposal.id);
    } catch (err: any) {
      throw new Error(`Cannot verify backend proposal state: ${err.message}`);
    }

    if (liveProposal.status !== "approved") {
      throw new Error(
        `Cannot apply repair: Proposal '${liveProposal.id.slice(0, 8)}' status is '${liveProposal.status}'. It must be 'approved' before applying.`
      );
    }

    // 2. Patch Integrity and TOCTOU verification
    const verification = this.integrityStore.verifyBeforeApplication(liveProposal, this.workspaceRoot);
    if (!verification.ok) {
      throw new Error(`Integrity verification failed: ${verification.reason}`);
    }

    const changes = verification.changes!;
    const approvedHash = verification.approvedHash!;

    // 3. Multi-file atomic apply with rollback protection
    const writtenFiles = this.integrityStore.applyApprovedChangesSafely(
      changes,
      this.workspaceRoot,
      liveProposal.id
    );

    // 4. Report application to backend only after verified disk write
    try {
      await this.client.applyRepair(
        liveProposal.id,
        agentId,
        "applied",
        this.workspaceRoot,
        `Applied patch hash: ${approvedHash}`
      );
    } catch (backendErr: any) {
      this.outputChannel.appendLine(
        `[RepairService Warning] Reporting application to backend returned: ${backendErr.message}`
      );
    }

    this.integrityStore.recordApplied(liveProposal.id);
    proposal.status = "applied";

    this._onLifecycleEvent.fire({
      stage: "applied",
      repairId: liveProposal.id,
      message: `Applied repair to ${writtenFiles.length} file(s) [Hash: ${approvedHash.slice(0, 8)}]`,
      proposal,
    });

    return writtenFiles;
  }

  /**
   * Rolls back an applied repair.
   */
  public async rollbackRepair(repairId: string): Promise<any> {
    return this.client.rollbackRepair(repairId);
  }
}
