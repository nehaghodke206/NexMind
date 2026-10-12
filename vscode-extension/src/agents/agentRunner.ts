import * as cp from "child_process";
import * as fs from "fs";
import * as path from "path";
import * as vscode from "vscode";
import { getGuardianConfig } from "../config";
import {
  CodebaseScanOptions,
  RepositoryInventoryResult,
  ContractDriftOptions,
  ContractDriftResult,
  ScanProgressEvent,
  LiveValidationOptions,
  LiveValidationReport,
  ContractFinding,
} from "./detectionTypes";

export interface DetectionOptions extends ContractDriftOptions {}

export interface RepairOptions {
  incidentId?: string;
  findingPathOrJson?: string;
  targetFile?: string;
  testCommand?: string;
  provider?: "deterministic" | "ollama";
  syncBackend?: boolean;
  approve?: boolean;
  apply?: boolean;
  timeoutSeconds?: number;
  cancellationToken?: vscode.CancellationToken;
}

export interface EnvironmentCheckResult {
  ok: boolean;
  pythonPath?: string;
  pythonVersion?: string;
  pythonSupported: boolean;
  detectionAgentAvailable: boolean;
  detectionCliWorking: boolean;
  repairAgentAvailable: boolean;
  repairCliWorking: boolean;
  ollamaAvailable: boolean;
  ollamaModelInstalled: boolean;
  message: string;
}

export interface AgentPaths {
  agentRoot?: string;
  detectionDir?: string;
  repairDir?: string;
}

export interface PythonResolutionResult {
  pythonPath: string;
  source: "configured" | "virtualenv" | "system";
  version: string;
  major: number;
  minor: number;
  canImportDetection: boolean;
  canImportRepair: boolean;
}

export class AgentRunner {
  private outputChannel: vscode.OutputChannel;

  constructor(outputChannel: vscode.OutputChannel) {
    this.outputChannel = outputChannel;
  }

  /**
   * Discovers the Agent root, detection directory, and repair directory.
   * Priority:
   * 1. Explicit configuration ('dependencyGuardian.agentPath' or env variables)
   * 2. Upward traversal from current extension location (__dirname)
   * 3. Target workspaceRoot (if it is HackWave or contains agents/detection)
   * 4. Known development paths
   */
  public resolveAgentPaths(workspaceRoot?: string): AgentPaths {
    const config = getGuardianConfig();

    // 1. Explicitly configured path or environment variable
    const explicitCandidates = [
      config.agentPath,
      process.env.DEPENDENCY_GUARDIAN_AGENT_PATH,
      process.env.DEPENDENCY_GUARDIAN_ROOT,
    ].filter((p): p is string => Boolean(p && p.trim()));

    for (const raw of explicitCandidates) {
      const explicit = path.resolve(raw.trim());
      if (fs.existsSync(explicit)) {
        // Direct detection directory containing dependency_guardian/
        if (fs.existsSync(path.join(explicit, "dependency_guardian"))) {
          const parent = path.dirname(explicit);
          const repairCandidate = path.join(parent, "repair");
          return {
            agentRoot: parent,
            detectionDir: explicit,
            repairDir: fs.existsSync(repairCandidate) ? repairCandidate : undefined,
          };
        }
        // Root containing agents/detection:
        const detSub = path.join(explicit, "agents", "detection");
        if (fs.existsSync(detSub)) {
          const repSub = path.join(explicit, "agents", "repair");
          return {
            agentRoot: explicit,
            detectionDir: detSub,
            repairDir: fs.existsSync(repSub) ? repSub : undefined,
          };
        }
        // Direct agents folder containing detection:
        const detDirect = path.join(explicit, "detection");
        if (fs.existsSync(detDirect)) {
          const repDirect = path.join(explicit, "repair");
          return {
            agentRoot: explicit,
            detectionDir: detDirect,
            repairDir: fs.existsSync(repDirect) ? repDirect : undefined,
          };
        }
        // Fallback: treat explicit directory as detectionDir
        return {
          agentRoot: explicit,
          detectionDir: explicit,
        };
      }
    }

    // 2. Upward search from extension directory (__dirname)
    let current = __dirname;
    for (let i = 0; i < 6; i++) {
      const detCand = path.join(current, "agents", "detection");
      if (fs.existsSync(detCand) && fs.existsSync(path.join(detCand, "dependency_guardian"))) {
        const repCand = path.join(current, "agents", "repair");
        return {
          agentRoot: current,
          detectionDir: detCand,
          repairDir: fs.existsSync(repCand) ? repCand : undefined,
        };
      }
      const parent = path.dirname(current);
      if (parent === current) break;
      current = parent;
    }

    // 3. Search inside workspaceRoot if provided
    if (workspaceRoot && fs.existsSync(workspaceRoot)) {
      const wsDet = path.join(workspaceRoot, "agents", "detection");
      if (fs.existsSync(wsDet)) {
        const wsRep = path.join(workspaceRoot, "agents", "repair");
        return {
          agentRoot: workspaceRoot,
          detectionDir: wsDet,
          repairDir: fs.existsSync(wsRep) ? wsRep : undefined,
        };
      }
      if (fs.existsSync(path.join(workspaceRoot, "dependency_guardian"))) {
        return {
          agentRoot: workspaceRoot,
          detectionDir: workspaceRoot,
        };
      }
    }

    // 4. Well-known home development path fallback
    const homeDir = process.env.HOME || process.env.USERPROFILE || "";
    if (homeDir) {
      const defaultDevDetection = path.join(homeDir, "Dnyaneshwar", "HackWave", "agents", "detection");
      if (fs.existsSync(defaultDevDetection)) {
        const defaultDevRoot = path.join(homeDir, "Dnyaneshwar", "HackWave");
        return {
          agentRoot: defaultDevRoot,
          detectionDir: defaultDevDetection,
          repairDir: path.join(defaultDevRoot, "agents", "repair"),
        };
      }
    }

    return {};
  }

  /**
   * Constructs environment variables with proper PYTHONPATH for agent imports.
   */
  public buildProcessEnv(workspaceRoot?: string): NodeJS.ProcessEnv {
    const config = getGuardianConfig();
    const agentPaths = this.resolveAgentPaths(workspaceRoot);

    const pythonPathParts: string[] = [];
    if (agentPaths.detectionDir && fs.existsSync(agentPaths.detectionDir)) {
      pythonPathParts.push(agentPaths.detectionDir);
    }
    if (agentPaths.repairDir && fs.existsSync(agentPaths.repairDir)) {
      pythonPathParts.push(agentPaths.repairDir);
    }
    if (agentPaths.agentRoot && fs.existsSync(agentPaths.agentRoot)) {
      pythonPathParts.push(agentPaths.agentRoot);
    }
    if (workspaceRoot && fs.existsSync(workspaceRoot)) {
      pythonPathParts.push(workspaceRoot);
    }
    if (process.env.PYTHONPATH) {
      for (const p of process.env.PYTHONPATH.split(path.delimiter)) {
        if (p && !pythonPathParts.includes(p)) {
          pythonPathParts.push(p);
        }
      }
    }

    const uniqueParts = Array.from(new Set(pythonPathParts)).filter((p) => fs.existsSync(p));

    return {
      ...process.env,
      PYTHONUNBUFFERED: "1",
      PYTHONPATH: uniqueParts.join(path.delimiter),
      BACKEND_BASE_URL: config.backendUrl,
      DEPENDENCY_GUARDIAN_BACKEND_BASE_URL: config.backendUrl,
      OLLAMA_BASE_URL: config.ollamaBaseUrl,
      DEPENDENCY_GUARDIAN_AI_BASE_URL: config.ollamaBaseUrl,
      OLLAMA_MODEL: config.ollamaModel,
      DEPENDENCY_GUARDIAN_AI_MODEL: config.ollamaModel,
    };
  }

  /**
   * Probes a Python interpreter binary to verify executable existence, version (>= 3.11),
   * and importability of dependency_guardian and repair_agent modules.
   */
  public async probePython(
    pythonPath: string,
    env: NodeJS.ProcessEnv,
    cwd?: string
  ): Promise<{
    ok: boolean;
    version: string;
    major: number;
    minor: number;
    micro: number;
    hasDet: boolean;
    hasRep: boolean;
    error?: string;
  }> {
    const probeScript = `
import sys
major, minor, micro = sys.version_info[:3]
has_det = False
has_rep = False
det_err = ""

try:
    import dependency_guardian.cli
    has_det = True
except Exception as e:
    det_err = f"{type(e).__name__}: {e}"

try:
    import repair_agent.cli
    has_rep = True
except Exception:
    pass

print(f"{major}.{minor}.{micro}|{major}|{minor}|{micro}|{has_det}|{has_rep}|{det_err}")
`;

    return new Promise((resolve) => {
      cp.execFile(
        pythonPath,
        ["-c", probeScript],
        { env, cwd: cwd || process.cwd(), timeout: 10000 },
        (err, stdout, stderr) => {
          if (err) {
            resolve({
              ok: false,
              version: "unknown",
              major: 0,
              minor: 0,
              micro: 0,
              hasDet: false,
              hasRep: false,
              error: (stderr || err.message).trim(),
            });
            return;
          }

          const parts = stdout.trim().split("|");
          if (parts.length < 5) {
            resolve({
              ok: false,
              version: "unknown",
              major: 0,
              minor: 0,
              micro: 0,
              hasDet: false,
              hasRep: false,
              error: `Unexpected probe output: ${stdout.trim()}`,
            });
            return;
          }

          resolve({
            ok: true,
            version: parts[0] || "unknown",
            major: parseInt(parts[1] || "0", 10),
            minor: parseInt(parts[2] || "0", 10),
            micro: parseInt(parts[3] || "0", 10),
            hasDet: parts[4] === "True",
            hasRep: parts[5] === "True",
            error: parts[6] ? parts[6].trim() : undefined,
          });
        }
      );
    });
  }

  /**
   * Discovers candidate virtual environment python interpreter paths.
   */
  public findVirtualEnvCandidates(workspaceRoot?: string): string[] {
    const isWindows = process.platform === "win32";
    const pyBinRelative = isWindows
      ? [path.join("Scripts", "python.exe"), path.join("Scripts", "python3.exe")]
      : [path.join("bin", "python"), path.join("bin", "python3")];

    const searchRoots: string[] = [];
    const agentPaths = this.resolveAgentPaths(workspaceRoot);

    if (agentPaths.detectionDir) searchRoots.push(agentPaths.detectionDir);
    if (agentPaths.agentRoot) searchRoots.push(agentPaths.agentRoot);
    if (workspaceRoot) searchRoots.push(workspaceRoot);

    let cur = __dirname;
    for (let i = 0; i < 5; i++) {
      searchRoots.push(cur);
      const parent = path.dirname(cur);
      if (parent === cur) break;
      cur = parent;
    }

    const venvFolderNames = [".venv", "venv", "env", ".env"];
    const candidates: string[] = [];

    for (const root of searchRoots) {
      if (!fs.existsSync(root)) continue;
      for (const venvName of venvFolderNames) {
        const venvDir = path.join(root, venvName);
        for (const pyRel of pyBinRelative) {
          const candidate = path.join(venvDir, pyRel);
          if (fs.existsSync(candidate) && !candidates.includes(candidate)) {
            candidates.push(candidate);
          }
        }
      }

      const subdirs = [path.join(root, "agents", "detection"), path.join(root, "services", "backend")];
      for (const sub of subdirs) {
        if (!fs.existsSync(sub)) continue;
        for (const venvName of venvFolderNames) {
          const venvDir = path.join(sub, venvName);
          for (const pyRel of pyBinRelative) {
            const candidate = path.join(venvDir, pyRel);
            if (fs.existsSync(candidate) && !candidates.includes(candidate)) {
              candidates.push(candidate);
            }
          }
        }
      }
    }

    return candidates;
  }

  /**
   * Discovers candidate system python binaries.
   */
  public findSystemPythonCandidates(): string[] {
    const isWindows = process.platform === "win32";
    const candidates: string[] = [];

    try {
      const probeCmd = isWindows
        ? "where python"
        : "which -a python3 python 2>/dev/null || which python3 2>/dev/null || which python 2>/dev/null";
      const out = cp.execSync(probeCmd, { encoding: "utf-8", stdio: ["ignore", "pipe", "ignore"] });
      for (const line of out.split("\n")) {
        const p = line.trim();
        if (p && fs.existsSync(p) && !candidates.includes(p)) {
          candidates.push(p);
        }
      }
    } catch {}

    const standardLocations = isWindows
      ? [
          "C:\\Python313\\python.exe",
          "C:\\Python312\\python.exe",
          "C:\\Python311\\python.exe",
        ]
      : [
          "/usr/bin/python3",
          "/usr/local/bin/python3",
          "/usr/bin/python",
          "/opt/homebrew/bin/python3",
        ];

    for (const loc of standardLocations) {
      if (fs.existsSync(loc) && !candidates.includes(loc)) {
        candidates.push(loc);
      }
    }

    return candidates;
  }

  /**
   * Resolves and validates Python interpreter according to strict priority order:
   * 1. Explicitly configured Detector Agent Python interpreter ('dependencyGuardian.pythonPath')
   * 2. Valid Detector Agent virtual environment (checking existence and imports)
   * 3. Validated system Python fallback (STRICTLY requires that it can import dependency_guardian)
   */
  public async resolveAndValidatePython(workspaceRoot: string): Promise<PythonResolutionResult> {
    const config = getGuardianConfig();
    const env = this.buildProcessEnv(workspaceRoot);
    const agentPaths = this.resolveAgentPaths(workspaceRoot);
    const checkedInterpreters: string[] = [];

    // Priority 1: Explicitly configured interpreter
    if (config.pythonPath && config.pythonPath.trim()) {
      const configured = path.resolve(config.pythonPath.trim());
      checkedInterpreters.push(`Configured: ${configured}`);

      if (!fs.existsSync(configured)) {
        throw new Error(
          `Configured Python interpreter does not exist: "${configured}".\n` +
          `Please check the 'dependencyGuardian.pythonPath' setting in VS Code Settings.`
        );
      }

      const probe = await this.probePython(configured, env, workspaceRoot);
      if (!probe.ok || !probe.hasDet || probe.major < 3 || probe.minor < 11) {
        const issues: string[] = [];
        if (probe.major < 3 || probe.minor < 11) {
          issues.push(`Unsupported Python version ${probe.version} (requires Python >= 3.11).`);
        }
        if (!probe.hasDet) {
          issues.push(
            `Cannot import 'dependency_guardian' module (${probe.error || "ModuleNotFoundError"}).`
          );
        }
        if (!probe.ok && probe.error) {
          issues.push(`Execution error: ${probe.error}`);
        }

        throw new Error(
          `Configured Python interpreter "${configured}" failed validation:\n` +
          issues.map((i) => `  • ${i}`).join("\n") +
          `\n\nActionable fix:\n` +
          `1. Ensure 'dependency-guardian' is installed: pip install -e /path/to/agents/detection\n` +
          `2. Or configure 'dependencyGuardian.agentPath' in Settings to your agents checkout directory.\n` +
          `3. Or update 'dependencyGuardian.pythonPath' to a valid virtualenv with Python >= 3.11.`
        );
      }

      return {
        pythonPath: configured,
        source: "configured",
        version: probe.version,
        major: probe.major,
        minor: probe.minor,
        canImportDetection: probe.hasDet,
        canImportRepair: probe.hasRep,
      };
    }

    // Priority 2: Valid Detector Agent virtual environment
    const venvCandidates = this.findVirtualEnvCandidates(workspaceRoot);
    for (const venvPy of venvCandidates) {
      checkedInterpreters.push(`Virtualenv candidate: ${venvPy}`);
      const probe = await this.probePython(venvPy, env, workspaceRoot);
      if (probe.ok && probe.hasDet && probe.major === 3 && probe.minor >= 11) {
        return {
          pythonPath: venvPy,
          source: "virtualenv",
          version: probe.version,
          major: probe.major,
          minor: probe.minor,
          canImportDetection: probe.hasDet,
          canImportRepair: probe.hasRep,
        };
      }
    }

    // Priority 3: Validated system Python fallback
    const systemCandidates = this.findSystemPythonCandidates();
    for (const sysPy of systemCandidates) {
      checkedInterpreters.push(`System candidate: ${sysPy}`);
      const probe = await this.probePython(sysPy, env, workspaceRoot);
      // Strictly require that the system python can import dependency_guardian!
      if (probe.ok && probe.hasDet && probe.major === 3 && probe.minor >= 11) {
        return {
          pythonPath: sysPy,
          source: "system",
          version: probe.version,
          major: probe.major,
          minor: probe.minor,
          canImportDetection: probe.hasDet,
          canImportRepair: probe.hasRep,
        };
      }
    }

    // None passed
    const agentPathStatus = agentPaths.detectionDir
      ? `Discovered at "${agentPaths.detectionDir}"`
      : "Not found (missing agents/detection in repo or install)";

    const diagnostics = [
      "Failed to locate a Python environment capable of executing Dependency Guardian Detection Agent.",
      "",
      `Target Workspace:  ${workspaceRoot}`,
      `Agent Directory:   ${agentPathStatus}`,
      `Interpreters checked:`,
      ...checkedInterpreters.map((c) => `  - ${c}`),
      "",
      "Root Cause:",
      "No Python interpreter (>= 3.11) could import 'dependency_guardian.cli'.",
      "",
      "How to resolve:",
      "1. If using a source checkout or external project, set 'dependencyGuardian.agentPath' in Settings:",
      "   e.g. /home/user/HackWave/agents/detection",
      "2. Or configure 'dependencyGuardian.pythonPath' in Settings to your virtual environment:",
      "   e.g. /home/user/HackWave/agents/detection/.venv/bin/python",
      "3. Or install the Detection Agent in your Python environment:",
      "   pip install -e /path/to/agents/detection",
    ].join("\n");

    throw new Error(diagnostics);
  }

  /**
   * Synchronous candidate resolution for legacy callers or status checks.
   */
  public resolvePython(workspaceRoot: string): string | null {
    const config = getGuardianConfig();

    // 1. Explicitly configured path
    if (config.pythonPath && fs.existsSync(config.pythonPath)) {
      return config.pythonPath;
    }

    // 2. Candidate virtual environments
    const venvCandidates = this.findVirtualEnvCandidates(workspaceRoot);
    if (venvCandidates.length > 0) {
      return venvCandidates[0];
    }

    // 3. Fallback system candidate
    const systemCandidates = this.findSystemPythonCandidates();
    if (systemCandidates.length > 0) {
      return systemCandidates[0];
    }

    return null;
  }

  /**
   * Probes Ollama service connectivity and checks if the configured model is installed.
   * Does NOT download models automatically.
   */
  public async probeOllama(
    baseUrl: string,
    modelName: string
  ): Promise<{ reachable: boolean; modelInstalled: boolean; installedModels: string[] }> {
    try {
      const cleanUrl = baseUrl.replace(/\/+$/, "");
      const res = await fetch(`${cleanUrl}/api/tags`, {
        signal: AbortSignal.timeout(3000),
      });

      if (!res.ok) {
        return { reachable: false, modelInstalled: false, installedModels: [] };
      }

      const data = (await res.json()) as any;
      const models: string[] = (data.models || []).map((m: any) => m.name || "");
      const modelPrefix = modelName.split(":")[0];
      const modelInstalled = models.some(
        (m) => m === modelName || m.startsWith(`${modelPrefix}:`) || m === modelPrefix
      );

      return { reachable: true, modelInstalled, installedModels: models };
    } catch {
      return { reachable: false, modelInstalled: false, installedModels: [] };
    }
  }

  /**
   * Verifies Python environment, genuine version support (Python >= 3.11),
   * module imports, and actual CLI entry points for both agents.
   */
  public async checkEnvironment(workspaceRoot: string): Promise<EnvironmentCheckResult> {
    const config = getGuardianConfig();
    const pythonPath = this.resolvePython(workspaceRoot);

    if (!pythonPath) {
      return {
        ok: false,
        pythonSupported: false,
        detectionAgentAvailable: false,
        detectionCliWorking: false,
        repairAgentAvailable: false,
        repairCliWorking: false,
        ollamaAvailable: false,
        ollamaModelInstalled: false,
        message:
          "Python interpreter not found.\n\nSetup instructions:\n" +
          "1. Install Python 3.11 - 3.13 on your machine.\n" +
          "2. Create a virtual environment: python3 -m venv .venv\n" +
          "3. Install agents: pip install -e agents/detection -e agents/repair\n" +
          "4. Or configure 'dependencyGuardian.pythonPath' in VS Code Settings.",
      };
    }

    const env = this.buildProcessEnv(workspaceRoot);

    // 1. Probe version and module imports
    const probeScript = `
import sys
major, minor, micro = sys.version_info[:3]
has_det = False
has_rep = False

try:
    import dependency_guardian
    has_det = True
except Exception:
    pass

try:
    import repair_agent
    has_rep = True
except Exception:
    pass

print(f"{major}.{minor}.{micro}|{major}|{minor}|{has_det}|{has_rep}")
`;

    const probeResult = await new Promise<{
      pyVersion: string;
      major: number;
      minor: number;
      hasDet: boolean;
      hasRep: boolean;
      err?: Error;
    }>((resolve) => {
      cp.execFile(
        pythonPath,
        ["-c", probeScript],
        { env, cwd: workspaceRoot, timeout: 10000 },
        (err, stdout) => {
          if (err) {
            resolve({ pyVersion: "unknown", major: 0, minor: 0, hasDet: false, hasRep: false, err });
            return;
          }
          const parts = stdout.trim().split("|");
          resolve({
            pyVersion: parts[0] || "unknown",
            major: parseInt(parts[1] || "0", 10),
            minor: parseInt(parts[2] || "0", 10),
            hasDet: parts[3] === "True",
            hasRep: parts[4] === "True",
          });
        }
      );
    });

    if (probeResult.err) {
      return {
        ok: false,
        pythonPath,
        pythonSupported: false,
        detectionAgentAvailable: false,
        detectionCliWorking: false,
        repairAgentAvailable: false,
        repairCliWorking: false,
        ollamaAvailable: false,
        ollamaModelInstalled: false,
        message: `Failed to execute Python (${pythonPath}): ${probeResult.err.message}`,
      };
    }

    // Version compatibility evaluation based on pyproject.toml requirements (requires-python = ">=3.11")
    const isSupported = probeResult.major === 3 && probeResult.minor >= 11;
    let versionStatus = "Supported (Production 3.11 - 3.13)";
    if (!isSupported) {
      versionStatus = "UNSUPPORTED (Requires Python >= 3.11)";
    } else if (probeResult.minor === 14) {
      versionStatus = "Supported (Experimental 3.14 detected. Production range: 3.11 - 3.13)";
    }

    // 2. Validate actual CLI entry point invocations
    const detCliWorking = await new Promise<boolean>((resolve) => {
      cp.execFile(
        pythonPath,
        ["-m", "dependency_guardian.cli", "--version"],
        { env, cwd: workspaceRoot, timeout: 8000 },
        (err) => resolve(!err)
      );
    });

    const repCliWorking = await new Promise<boolean>((resolve) => {
      cp.execFile(
        pythonPath,
        ["-m", "repair_agent.cli", "--version"],
        { env, cwd: workspaceRoot, timeout: 8000 },
        (err) => resolve(!err)
      );
    });

    // 3. Probe Ollama diagnostic without failing deterministic mode
    const ollamaProbe = await this.probeOllama(config.ollamaBaseUrl, config.ollamaModel);

    // Build diagnostic summary report
    const lines = [
      "============================================================",
      " DEPENDENCY GUARDIAN ENVIRONMENT DIAGNOSTIC",
      "============================================================",
      ` Python Path:        ${pythonPath}`,
      ` Python Version:     ${probeResult.pyVersion} [${versionStatus}]`,
      ` Detection Agent:    ${probeResult.hasDet ? "Available" : "Missing"} (CLI: ${detCliWorking ? "Functional" : "Failed"})`,
      ` Repair Agent:       ${probeResult.hasRep ? "Available" : "Missing"} (CLI: ${repCliWorking ? "Functional" : "Failed"})`,
      ` Backend Endpoint:   ${config.backendUrl}`,
      ` AI Provider:        ${config.aiProvider}`,
      ` Ollama Endpoint:    ${config.ollamaBaseUrl} [${ollamaProbe.reachable ? "Reachable" : "Offline"}]`,
      ` Ollama Model:       ${config.ollamaModel} [${ollamaProbe.modelInstalled ? "Available" : "Not Found locally"}]`,
      ` Deterministic Mode: Fully functional (Runs offline without Ollama)`,
      "============================================================",
    ];

    if (!isSupported) {
      lines.push(
        "",
        `[!] Python ${probeResult.pyVersion} is NOT officially supported.`,
        "    Dependency Guardian agents require Python >= 3.11 (3.11, 3.12, or 3.13).",
        "    Please configure a virtual environment with Python 3.11 - 3.13."
      );
    }

    if (!probeResult.hasDet || !detCliWorking || !probeResult.hasRep || !repCliWorking) {
      lines.push(
        "",
        "[!] Agent dependencies or CLI entry points failed verification.",
        "    Ensure dependencies are installed in your active virtual environment:",
        "    source <venv>/bin/activate && pip install -e agents/detection -e agents/repair"
      );
    }

    if (!ollamaProbe.reachable && config.detectionMode !== "algorithmic") {
      lines.push(
        "",
        `[NOTE] Ollama is not running at ${config.ollamaBaseUrl}.`,
        "       Deterministic repair mode and algorithmic detection remain fully usable.",
        "       To enable local AI explanation/repair, start Ollama via: ollama serve"
      );
    } else if (ollamaProbe.reachable && !ollamaProbe.modelInstalled) {
      lines.push(
        "",
        `[NOTE] Configured model '${config.ollamaModel}' was not found in local Ollama repository.`,
        `       You can pull it explicitly using: ollama pull ${config.ollamaModel}`
      );
    }

    const overallOk =
      isSupported &&
      probeResult.hasDet &&
      probeResult.hasRep &&
      detCliWorking &&
      repCliWorking;

    return {
      ok: overallOk,
      pythonPath,
      pythonVersion: probeResult.pyVersion,
      pythonSupported: isSupported,
      detectionAgentAvailable: probeResult.hasDet,
      detectionCliWorking: detCliWorking,
      repairAgentAvailable: probeResult.hasRep,
      repairCliWorking: repCliWorking,
      ollamaAvailable: ollamaProbe.reachable,
      ollamaModelInstalled: ollamaProbe.modelInstalled,
      message: lines.join("\n"),
    };
  }

  /**
   * Runs the Detection Agent CLI and parses its JSON output.
   */
  /**
   * Runs the Detection Agent Repository Intelligence Scanner (`scan-repo`)
   * and returns the comprehensive repository inventory.
   */
  public async runCodebaseScan(
    workspaceRoot: string,
    options: CodebaseScanOptions
  ): Promise<RepositoryInventoryResult> {
    const pyResolution = await this.resolveAndValidatePython(workspaceRoot);
    const pythonPath = pyResolution.pythonPath;

    const repoPath = options.repositoryPath || workspaceRoot;
    if (!fs.existsSync(repoPath)) {
      throw new Error(`Target repository path does not exist: ${repoPath}`);
    }

    const config = getGuardianConfig();
    const outDir = options.outputDir || path.join(workspaceRoot, "reports", "repository-inventory");
    const invJsonFile = path.join(outDir, "repository-inventory.json");

    const args: string[] = ["-m", "dependency_guardian.cli", "scan-repo", repoPath];
    args.push("--output", outDir);
    args.push("--format", "json");

    const mode = options.mode || config.detectionMode || "algorithmic";
    args.push("--mode", mode);

    if (mode !== "algorithmic") {
      args.push("--provider", config.aiProvider);
      args.push("--model", config.ollamaModel);
      args.push("--base-url", config.ollamaBaseUrl);
    }

    if (options.enrichOpenApi === false) {
      args.push("--no-enrichment");
    }

    this.outputChannel.appendLine(`[Codebase Scan] Executing: ${pythonPath} ${args.join(" ")}`);

    const spawnCwd = fs.existsSync(workspaceRoot) ? workspaceRoot : (fs.existsSync(repoPath) ? repoPath : process.cwd());

    const result = await this.spawnProcess(
      pythonPath,
      args,
      spawnCwd,
      options.timeoutSeconds || 90,
      options.cancellationToken,
      invJsonFile,
      options.onProgress,
      options.onLog
    );

    if (!result || typeof result !== "object" || (!result.metadata && !result.endpoints && !result.dependencies)) {
      throw new Error(`Repository scan did not produce a valid inventory report.`);
    }

    const inventory: RepositoryInventoryResult = {
      metadata: result.metadata || {
        scanner_name: "Dependency Guardian Repository Intelligence",
        scanner_version: "0.2.0",
        scanned_path: repoPath,
        scan_timestamp: new Date().toISOString(),
        languages_detected: [],
        frameworks_detected: [],
        total_files_scanned: 0,
        openapi_specs_found: [],
      },
      dependencies: result.dependencies || [],
      unused_dependencies: result.unused_dependencies || [],
      integrations: result.integrations || [],
      endpoints: result.endpoints || [],
      discrepancies: result.discrepancies || [],
      test_coverage: result.test_coverage || {
        total_endpoints: 0,
        tested_endpoints: 0,
        untested_endpoints: 0,
        coverage_percentage: 0,
        endpoint_coverage_map: {},
        integration_tests_found: [],
      },
      ai_insights: result.ai_insights,
      output_dir: outDir,
    };

    return inventory;
  }

  /**
   * Runs the Detection Agent CLI and parses its JSON output into ContractDriftResult.
   */
  public async runDetection(
    workspaceRoot: string,
    options: DetectionOptions = {}
  ): Promise<ContractDriftResult> {
    const pyResolution = await this.resolveAndValidatePython(workspaceRoot);
    const pythonPath = pyResolution.pythonPath;

    if (options.baselinePath && !fs.existsSync(options.baselinePath)) {
      throw new Error(`Baseline specification file not found: ${options.baselinePath}`);
    }
    if (options.currentPath && !fs.existsSync(options.currentPath)) {
      throw new Error(`Current specification file not found: ${options.currentPath}`);
    }

    const config = getGuardianConfig();
    const args: string[] = ["-m", "dependency_guardian.cli"];

    if (options.baselinePath && options.currentPath) {
      args.push(options.baselinePath, options.currentPath);
    }

    const mode = options.mode || config.detectionMode || "algorithmic";
    args.push("--mode", mode);
    args.push("--format", "json");

    if (mode !== "algorithmic") {
      args.push("--provider", config.aiProvider);
      args.push("--model", config.ollamaModel);
      args.push("--base-url", config.ollamaBaseUrl);
    }

    const isSyncExplicitlyRequested = options.syncBackend === true;
    const shouldSync =
      options.syncBackend === true ||
      (options.syncBackend !== false &&
        config.autoSyncBackend &&
        Boolean((options.projectId || config.projectId || "").trim()) &&
        Boolean((options.dependencyId || config.dependencyId || "").trim()));

    if (shouldSync || isSyncExplicitlyRequested) {
      const effectiveProjectId = (options.projectId || config.projectId || "").trim();
      const effectiveDependencyId = (options.dependencyId || config.dependencyId || "").trim();

      if (!effectiveProjectId || !effectiveDependencyId) {
        throw new Error(
          `Backend synchronization requested, but both Project ID and Dependency ID are required. ` +
          `(Resolved projectId='${effectiveProjectId}', dependencyId='${effectiveDependencyId}'). ` +
          `Please configure dependencyGuardian.projectId and dependencyGuardian.dependencyId or disable backend synchronization.`
        );
      }

      args.push("--sync-backend");
      args.push("--backend-url", config.backendUrl);
      args.push("--project-id", effectiveProjectId);
      args.push("--dependency-id", effectiveDependencyId);
      if (options.proposeRepairs) {
        args.push("--propose-repairs");
      }
    }

    if (options.testCmd) {
      args.push("--test-cmd", options.testCmd);
    }
    if (options.outputFile) {
      args.push("--output", options.outputFile);
    }
    if (options.insightsOutputFile) {
      args.push("--insights-output", options.insightsOutputFile);
    }

    this.outputChannel.appendLine(`[Detection] Executing: ${pythonPath} ${args.join(" ")}`);

    const spawnCwd = fs.existsSync(workspaceRoot) ? workspaceRoot : process.cwd();

    const raw = await this.spawnProcess(
      pythonPath,
      args,
      spawnCwd,
      options.timeoutSeconds || 60,
      options.cancellationToken,
      options.outputFile
    );

    const findings: ContractFinding[] = (raw.findings || []).map((f: any) => ({
      id: f.id || `${f.rule_id}-${f.path}`,
      rule_id: f.rule_id || "RULE-UNKNOWN",
      compatibility: f.compatibility || "unknown",
      severity: f.severity || "medium",
      path: f.path || "/",
      method: f.method || null,
      message: f.message || "Contract drift detected",
      evidence: f.evidence || {},
      provenance: f.provenance || "contract_diff",
      recommended_action: f.recommended_action || null,
      confidence: f.confidence !== undefined ? f.confidence : 1.0,
      ai_reasoning: f.ai_reasoning || null,
      impact: f.impact || {},
    }));

    const summary = raw.summary || {
      total_findings: findings.length,
      breaking_count: findings.filter((f: any) => f.compatibility === "breaking").length,
      potentially_breaking_count: findings.filter((f: any) => f.compatibility === "potentially_breaking").length,
      non_breaking_count: findings.filter((f: any) => f.compatibility === "non_breaking").length,
      unknown_count: findings.filter((f: any) => f.compatibility === "unknown").length,
      by_severity: {
        critical: findings.filter((f: any) => f.severity === "critical").length,
        high: findings.filter((f: any) => f.severity === "high").length,
        medium: findings.filter((f: any) => f.severity === "medium").length,
        low: findings.filter((f: any) => f.severity === "low").length,
      },
    };

    return {
      mode: raw.mode || mode,
      execution_time_ms: raw.execution_time_ms || 0,
      success: raw.success !== undefined ? raw.success : true,
      findings,
      summary,
      ai_provider: raw.ai_provider || null,
      ai_model: raw.ai_model || null,
      ai_status: raw.ai_status || null,
      ai_error: raw.ai_error || null,
      ai_insights: raw.ai_insights || null,
      backend_sync: raw.backend_sync,
    };
  }

  /**
   * Runs the Detection Agent External API Intelligence & Live Validation (`validate-api`)
   * and returns the categorized LiveValidationReport.
   */
  public async runLiveValidation(
    workspaceRoot: string,
    options: LiveValidationOptions = {}
  ): Promise<LiveValidationReport> {
    const pyResolution = await this.resolveAndValidatePython(workspaceRoot);
    const pythonPath = pyResolution.pythonPath;
    const config = getGuardianConfig();

    const args: string[] = ["-m", "dependency_guardian.cli", "validate-api"];

    if (options.url) {
      args.push("--url", options.url);
      if (options.method) {
        args.push("--method", options.method);
      }
      if (options.serviceName) {
        args.push("--service-name", options.serviceName);
      }
      if (options.authEnvVar) {
        args.push("--auth-env-var", options.authEnvVar);
      }
      if (options.expectedStatus) {
        args.push("--expected-status", options.expectedStatus.toString());
      }
      if (options.expectedFields && options.expectedFields.length > 0) {
        args.push("--expected-fields", ...options.expectedFields);
      }
    } else {
      const cfgCandidate = options.configPath || config.liveValidationConfigPath || "dependency-guardian.yml";
      let resolvedCfg = path.isAbsolute(cfgCandidate)
        ? cfgCandidate
        : path.resolve(workspaceRoot, cfgCandidate);
      if (!fs.existsSync(resolvedCfg)) {
        const fallbacks = [
          path.resolve(workspaceRoot, "demo/sample-api/dependency-guardian.yml"),
          path.resolve(workspaceRoot, "demo-app/dependency-guardian.yml"),
          path.resolve(workspaceRoot, "..", "dependency-guardian.yml"),
        ];
        for (const fb of fallbacks) {
          if (fs.existsSync(fb)) {
            resolvedCfg = fb;
            break;
          }
        }
      }
      if (fs.existsSync(resolvedCfg)) {
        args.push("--config", resolvedCfg);
      }
    }

    args.push("--workspace-dir", workspaceRoot);

    const mode = options.mode || config.detectionMode || "algorithmic";
    args.push("--mode", mode);
    args.push("--format", "json");

    if (mode !== "algorithmic") {
      args.push("--provider", config.aiProvider);
      args.push("--model", config.ollamaModel);
      args.push("--base-url", config.ollamaBaseUrl);
    }

    const timeoutSec = options.timeoutSeconds || config.liveValidationTimeoutSeconds || 5;
    args.push("--timeout", timeoutSec.toString());

    const concurrency = options.concurrency || config.liveValidationConcurrency || 5;
    args.push("--concurrency", concurrency.toString());

    if (options.maxRequests) {
      args.push("--max-requests", options.maxRequests.toString());
    }

    let outJsonFile: string | undefined = options.outputFile;
    if (!outJsonFile) {
      const reportsDir = path.join(workspaceRoot, "reports");
      try {
        if (!fs.existsSync(reportsDir)) {
          fs.mkdirSync(reportsDir, { recursive: true });
        }
        outJsonFile = path.join(reportsDir, "live-validation-report.json");
        args.push("--output", outJsonFile);
      } catch {
        // Fall back to stdout
      }
    } else {
      args.push("--output", outJsonFile);
    }

    this.outputChannel.appendLine(`[Live API Validation] Executing: ${pythonPath} ${args.join(" ")}`);

    const spawnCwd = fs.existsSync(workspaceRoot) ? workspaceRoot : process.cwd();

    const raw = await this.spawnProcess(
      pythonPath,
      args,
      spawnCwd,
      timeoutSec * 4 + 15,
      options.cancellationToken,
      outJsonFile,
      options.onProgress,
      options.onLog
    );

    if (!raw || typeof raw !== "object" || !Array.isArray(raw.results)) {
      throw new Error("Live API validation did not produce a valid report.");
    }

    const findings: ContractFinding[] = (raw.findings || []).map((f: any) => ({
      id: f.id || `${f.rule_id}-${f.path}`,
      rule_id: f.rule_id || "RULE-UNKNOWN",
      compatibility: f.compatibility || "breaking",
      severity: f.severity || "medium",
      path: f.path || "/",
      method: f.method || null,
      message: f.message || "Live API validation issue detected",
      evidence: f.evidence || {},
      provenance: f.provenance || "live_probe",
      recommended_action: f.recommended_action || null,
      confidence: f.confidence !== undefined ? f.confidence : 1.0,
      ai_reasoning: f.ai_reasoning || null,
      impact: f.impact || {},
    }));

    const report: LiveValidationReport = {
      total_probes: raw.total_probes !== undefined ? raw.total_probes : raw.results.length,
      reachable_count: raw.reachable_count || 0,
      auth_failure_count: raw.auth_failure_count || 0,
      client_error_count: raw.client_error_count || 0,
      server_failure_count: raw.server_failure_count || 0,
      unreachable_count: raw.unreachable_count || 0,
      contract_mismatch_count: raw.contract_mismatch_count || 0,
      security_blocked_count: raw.security_blocked_count || 0,
      duration_seconds: raw.duration_seconds || 0,
      results: raw.results || [],
      findings,
      config_source: raw.config_source || null,
      mode: raw.mode || mode,
      ai_status: raw.ai_status || null,
      ai_provider: raw.ai_provider || null,
      ai_model: raw.ai_model || null,
      ai_error: raw.ai_error || null,
      timestamp: raw.timestamp || new Date().toISOString(),
    };

    return report;
  }

  /**
   * Runs the Repair Agent CLI and parses its JSON output.
   */
  public async runRepair(
    workspaceRoot: string,
    options: RepairOptions = {}
  ): Promise<any> {
    const pyResolution = await this.resolveAndValidatePython(workspaceRoot);
    const pythonPath = pyResolution.pythonPath;

    const config = getGuardianConfig();
    const args: string[] = ["-m", "repair_agent.cli"];

    if (options.incidentId) {
      args.push("--incident-id", options.incidentId);
    }
    if (options.findingPathOrJson) {
      args.push("--finding", options.findingPathOrJson);
    }
    if (options.targetFile) {
      args.push("--file", options.targetFile);
    }

    args.push("--workspace", workspaceRoot);
    args.push("--format", "json");
    args.push("--backend-url", config.backendUrl);

    const shouldSync = options.syncBackend !== undefined ? options.syncBackend : config.autoSyncBackend;
    if (shouldSync) {
      args.push("--sync-backend");
    }

    if (options.provider) {
      args.push("--provider", options.provider);
      if (options.provider === "ollama") {
        args.push("--model", config.ollamaModel);
        args.push("--base-url", config.ollamaBaseUrl);
      }
    }
    if (options.testCommand) {
      args.push("--test-cmd", options.testCommand);
    }
    if (options.approve) {
      args.push("--approve");
    }
    if (options.apply) {
      args.push("--apply");
    }

    this.outputChannel.appendLine(`[Repair] Executing: ${pythonPath} ${args.join(" ")}`);

    return this.spawnProcess(
      pythonPath,
      args,
      workspaceRoot,
      options.timeoutSeconds || 60,
      options.cancellationToken
    );
  }

  /**
   * Validates an existing repair proposal in a sandbox using the Repair Agent CLI.
   */
  public async runRepairValidation(
    workspaceRoot: string,
    repairId: string,
    testCommand?: string,
    cancellationToken?: vscode.CancellationToken
  ): Promise<any> {
    const pyResolution = await this.resolveAndValidatePython(workspaceRoot);
    const pythonPath = pyResolution.pythonPath;
    const config = getGuardianConfig();

    const args: string[] = [
      "-m",
      "repair_agent.cli",
      "--validate-proposal",
      repairId,
      "--workspace",
      workspaceRoot,
      "--backend-url",
      config.backendUrl,
      "--format",
      "json",
    ];

    if (testCommand) {
      args.push("--test-cmd", testCommand);
    }

    this.outputChannel.appendLine(`[Repair Validation] Executing: ${pythonPath} ${args.join(" ")}`);

    return this.spawnProcess(
      pythonPath,
      args,
      workspaceRoot,
      60,
      cancellationToken
    );
  }

  /**
   * Executes a process with timeout and cancellation support, returning parsed JSON stdout.
   */
  private spawnProcess(
    command: string,
    args: string[],
    cwd: string,
    timeoutSeconds: number,
    cancellationToken?: vscode.CancellationToken,
    fallbackOutputFile?: string,
    onProgress?: (progress: ScanProgressEvent) => void,
    onLog?: (line: string) => void
  ): Promise<any> {
    return new Promise<any>((resolve, reject) => {
      const env = this.buildProcessEnv(cwd);
      let isSettled = false;
      const startTime = Date.now();
      let lastActivityTime = Date.now();
      let currentPhase = "starting";
      let warnedQuiet = false;

      const child = cp.spawn(command, args, { cwd, env, shell: false });

      let stdout = "";
      let stderr = "";
      let stderrBuffer = "";

      const timeoutTimer = setTimeout(() => {
        if (!isSettled) {
          cleanup();
          isSettled = true;
          child.kill("SIGTERM");
          this.outputChannel.appendLine(`[Process Error] Timed out after ${timeoutSeconds}s.`);
          reject(new Error(`Agent process timed out after ${timeoutSeconds} seconds.`));
        }
      }, timeoutSeconds * 1000);

      // Periodic heartbeat check for quiet processes (every 3 seconds)
      const heartbeatInterval = setInterval(() => {
        if (isSettled) return;
        const now = Date.now();
        const elapsedSeconds = Math.round((now - startTime) / 1000);
        const quietDuration = now - lastActivityTime;

        if (quietDuration >= 15000) {
          if (!warnedQuiet) {
            warnedQuiet = true;
            this.outputChannel.appendLine(
              `[Scan Notice] Process running quietly for ${Math.round(quietDuration / 1000)}s (still active, analyzing)...`
            );
          }
          if (onProgress) {
            onProgress({
              phase: currentPhase,
              message: `Scan in progress (${elapsedSeconds}s elapsed)...`,
              elapsedSeconds,
              quietWarning: true,
            });
          }
        }
      }, 3000);

      const cleanup = () => {
        clearTimeout(timeoutTimer);
        clearInterval(heartbeatInterval);
      };

      if (cancellationToken) {
        cancellationToken.onCancellationRequested(() => {
          if (!isSettled) {
            cleanup();
            isSettled = true;
            child.kill("SIGTERM");
            this.outputChannel.appendLine("[Process] Cancelled by user.");
            reject(new Error("Agent process was cancelled by the user."));
          }
        });
      }

      child.stdout.on("data", (data) => {
        stdout += data.toString();
        lastActivityTime = Date.now();
      });

      child.stderr.on("data", (data) => {
        const text = data.toString();
        stderr += text;
        lastActivityTime = Date.now();
        warnedQuiet = false;

        stderrBuffer += text;
        const lines = stderrBuffer.split("\n");
        stderrBuffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;

          // Check for JSON progress event
          if (trimmed.startsWith("{") && trimmed.includes('"type"') && trimmed.includes('"progress"')) {
            try {
              const parsed = JSON.parse(trimmed) as ScanProgressEvent;
              if (parsed && (parsed.type === "progress" || parsed.phase)) {
                if (parsed.phase) {
                  currentPhase = parsed.phase;
                }
                parsed.elapsedSeconds = Math.round((Date.now() - startTime) / 1000);
                parsed.quietWarning = false;
                this.outputChannel.appendLine(`[Scan Progress] [${parsed.phase}] ${parsed.message}`);
                onProgress?.(parsed);
                continue;
              }
            } catch {
              // Not valid JSON, fall through to regular log
            }
          }

          onLog?.(trimmed);
          this.outputChannel.appendLine(`[Agent Stderr] ${trimmed}`);
        }
      });

      child.on("error", (err) => {
        if (!isSettled) {
          cleanup();
          isSettled = true;
          this.outputChannel.appendLine(`[Process Error] Spawn failed: ${err.message}`);
          reject(new Error(`Failed to launch agent process: ${err.message}`));
        }
      });

      child.on("close", (code) => {
        if (!isSettled) {
          cleanup();
          isSettled = true;

          // Flush remaining stderr buffer
          if (stderrBuffer.trim()) {
            const trimmed = stderrBuffer.trim();
            if (trimmed.startsWith("{") && trimmed.includes('"type"') && trimmed.includes('"progress"')) {
              try {
                const parsed = JSON.parse(trimmed) as ScanProgressEvent;
                if (parsed && (parsed.type === "progress" || parsed.phase)) {
                  parsed.elapsedSeconds = Math.round((Date.now() - startTime) / 1000);
                  onProgress?.(parsed);
                }
              } catch {}
            } else {
              onLog?.(trimmed);
              this.outputChannel.appendLine(`[Agent Stderr] ${trimmed}`);
            }
          }

          const tryFallbackFile = (): any | null => {
            if (fallbackOutputFile && fs.existsSync(fallbackOutputFile)) {
              try {
                const content = fs.readFileSync(fallbackOutputFile, "utf-8");
                return JSON.parse(content);
              } catch {}
            }
            return null;
          };

          // Locate JSON block in stdout if preceded by logs
          const jsonStart = stdout.indexOf("{");
          const jsonEnd = stdout.lastIndexOf("}");
          if (jsonStart !== -1 && jsonEnd !== -1 && jsonEnd > jsonStart) {
            try {
              const jsonStr = stdout.substring(jsonStart, jsonEnd + 1);
              const parsed = JSON.parse(jsonStr);
              return resolve(parsed);
            } catch (err: any) {
              const fileData = tryFallbackFile();
              if (fileData) {
                return resolve(fileData);
              }
              this.outputChannel.appendLine(`[JSON Parse Error] ${err.message}\nRaw Output: ${stdout}`);
              return reject(new Error(`Agent output could not be parsed as JSON: ${err.message}`));
            }
          }

          const fileData = tryFallbackFile();
          if (fileData) {
            return resolve(fileData);
          }

          if (code !== 0) {
            this.outputChannel.appendLine(`[Process Exit] Code ${code}. Stderr: ${stderr}`);
            if (stderr.includes("ModuleNotFoundError: No module named 'dependency_guardian'")) {
              return reject(
                new Error(
                  `Agent process failed: Module 'dependency_guardian' not found.\n` +
                  `Please configure 'dependencyGuardian.agentPath' in Settings or install with 'pip install -e agents/detection'.\n` +
                  `Stderr: ${stderr.trim()}`
                )
              );
            }
            return reject(
              new Error(
                `Agent process exited with code ${code}. Stderr: ${stderr.trim() || "No error details recorded."}`
              )
            );
          }

          if (!stdout.trim()) {
            return resolve({});
          }

          return resolve({ raw_output: stdout });
        }
      });
    });
  }
}
