import * as vscode from "vscode";

export interface GuardianConfig {
  backendUrl: string;
  pythonPath: string;
  agentPath: string;
  detectionMode: "algorithmic" | "ai" | "hybrid";
  aiProvider: string;
  ollamaModel: string;
  ollamaBaseUrl: string;
  projectId: string;
  dependencyId: string;
  autoSyncBackend: boolean;
  liveValidationConfigPath: string;
  liveValidationTimeoutSeconds: number;
  liveValidationConcurrency: number;
}

export const DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000/api/v1";
export const DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434";
export const DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:3b";

/**
 * Normalizes backend URL ensuring no trailing slashes and default port.
 */
export function normalizeBackendUrl(url: string): string {
  let cleaned = (url || "").trim().replace(/\/+$/, "");
  if (!cleaned) {
    return DEFAULT_BACKEND_BASE_URL;
  }
  // Standardize /api/v1 prefix
  if (!cleaned.endsWith("/api/v1") && !cleaned.includes("/api/")) {
    cleaned = `${cleaned}/api/v1`;
  }
  return cleaned;
}

/**
 * Normalizes Ollama base URL by stripping trailing slashes.
 */
export function normalizeOllamaUrl(url: string): string {
  let cleaned = (url || "").trim().replace(/\/+$/, "");
  return cleaned || DEFAULT_OLLAMA_BASE_URL;
}

/**
 * Updates the detection mode setting in VS Code configuration.
 */
export async function updateDetectionMode(mode: "algorithmic" | "ai" | "hybrid"): Promise<void> {
  if (typeof vscode !== "undefined" && vscode.workspace) {
    const cfg = vscode.workspace.getConfiguration("dependencyGuardian");
    await cfg.update("detectionMode", mode, vscode.ConfigurationTarget.Global);
  }
}

/**
 * Retrieves centralized settings with environment variable fallbacks and legacy compatibility.
 */
export function getGuardianConfig(): GuardianConfig {
  const cfg = typeof vscode !== "undefined" && vscode?.workspace ? vscode.workspace.getConfiguration("dependencyGuardian") : null;
  const envBackend = process.env.BACKEND_BASE_URL || process.env.DEPENDENCY_GUARDIAN_BACKEND_BASE_URL;
  const envOllamaUrl = process.env.OLLAMA_BASE_URL || process.env.DEPENDENCY_GUARDIAN_AI_BASE_URL;
  const envOllamaModel = process.env.OLLAMA_MODEL || process.env.DEPENDENCY_GUARDIAN_AI_MODEL;
  const envPython = process.env.PYTHON_PATH;
  const envAgent = process.env.DEPENDENCY_GUARDIAN_AGENT_PATH || process.env.DEPENDENCY_GUARDIAN_ROOT;
  const envProjectId = process.env.DEPENDENCY_GUARDIAN_PROJECT_ID || process.env.PROJECT_ID;
  const envDependencyId = process.env.DEPENDENCY_GUARDIAN_DEPENDENCY_ID || process.env.DEPENDENCY_ID;

  const rawBackend = (cfg ? cfg.get<string>("backendUrl") : null) || envBackend || DEFAULT_BACKEND_BASE_URL;
  const rawModel = (cfg ? cfg.get<string>("ollamaModel") : null) || envOllamaModel || DEFAULT_OLLAMA_MODEL;
  const rawOllamaUrl = (cfg ? cfg.get<string>("ollamaBaseUrl") : null) || envOllamaUrl || DEFAULT_OLLAMA_BASE_URL;
  const rawAgentPath = (cfg ? (cfg.get<string>("agentPath") || cfg.get<string>("detectionAgentPath")) : null) || envAgent || "";

  return {
    backendUrl: normalizeBackendUrl(rawBackend),
    pythonPath: ((cfg ? cfg.get<string>("pythonPath") : null) || envPython || "").trim(),
    agentPath: rawAgentPath.trim(),
    detectionMode: (cfg ? cfg.get<"algorithmic" | "ai" | "hybrid">("detectionMode") : null) || "algorithmic",
    aiProvider: (cfg ? cfg.get<string>("aiProvider") : null) || "ollama",
    ollamaModel: rawModel.trim(),
    ollamaBaseUrl: normalizeOllamaUrl(rawOllamaUrl),
    projectId: ((cfg ? cfg.get<string>("projectId") : null) || envProjectId || "").trim(),
    dependencyId: ((cfg ? cfg.get<string>("dependencyId") : null) || envDependencyId || "").trim(),
    autoSyncBackend: cfg ? cfg.get<boolean>("autoSyncBackend") !== false : true,
    liveValidationConfigPath: (cfg ? cfg.get<string>("liveValidationConfigPath") : null) || "dependency-guardian.yml",
    liveValidationTimeoutSeconds: (cfg ? cfg.get<number>("liveValidationTimeoutSeconds") : null) || 5,
    liveValidationConcurrency: (cfg ? cfg.get<number>("liveValidationConcurrency") : null) || 5,
  };
}
