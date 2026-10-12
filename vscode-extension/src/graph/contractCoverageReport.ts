/**
 * Dependency Guardian - API Contract Coverage & Drift Impact Report
 *
 * Calculates contract coverage using real discovered endpoints and reports:
 *  - Documented: covered by contract with no breaking drift
 *  - Undocumented: implemented/consumed in code but missing from contract
 *  - Drifted: contract exists but breaking/drift changes detected
 *  - Unknown: contract status cannot be determined (no contract available)
 *  - Unmatched Contract: contract operations with no code implementation (ghost routes)
 *
 * Identifies affected consumers, source paths, and line numbers using
 * the repository inventory and dependency relationships.
 */

import {
  extractEndpointAndHost,
  normalizePath,
  normalizeRoute,
} from "./dependencyGraph";

export type CoverageStatus =
  | "documented"
  | "undocumented"
  | "drifted"
  | "unknown"
  | "unmatched_contract";

export interface AffectedConsumer {
  filePath: string;
  lineNumber?: number;
  serviceName?: string;
  operations?: string[];
  codeSnippet?: string;
}

export interface EndpointCoverageItem {
  id: string; // e.g. "endpoint:GET:/api/v1/users"
  method: string;
  routePath: string;
  status: CoverageStatus;
  contractPath?: string;
  discoveryMethod?: string;
  sourceFile?: string;
  lineNumber?: number;
  affectedConsumers: AffectedConsumer[];
  issues: string[];
}

export interface ContractCoverageReport {
  isAvailable: boolean;
  totalEndpoints: number; // Discovered endpoints denominator (documented + undocumented + drifted + unknown)
  documentedCount: number;
  undocumentedCount: number;
  driftedCount: number;
  unknownCount: number;
  unmatchedOperationsCount: number;
  coveragePercentage: number | null; // null if totalEndpoints === 0
  items: EndpointCoverageItem[];
  summaryText: string;
  contractSpecs: string[];
}

export interface ContractCoverageInput {
  inventory?: {
    metadata?: {
      scanner_name?: string;
      scanned_path?: string;
      languages_detected?: string[];
      frameworks_detected?: string[];
      openapi_specs_found?: string[];
    };
    integrations?: Array<{
      integration_type?: string;
      service_name?: string;
      target_url_or_host?: string;
      file_path?: string;
      line_number?: number;
      code_snippet?: string;
      operations?: string[];
    }>;
    endpoints?: Array<{
      http_method?: string;
      route_path?: string;
      summary?: string;
      source_file?: string;
      line_number?: number;
      discovery_method?: string;
      evidence_source?: string;
      parameters?: any[];
      responses?: any[];
    }>;
    discrepancies?: Array<{
      discrepancy_type?: string;
      endpoint_path?: string;
      method?: string;
      description?: string;
      spec_evidence?: string;
      code_evidence?: string;
      severity?: string;
      endpoint?: string;
      path?: string;
    }>;
  } | null;
  driftFindings?: Array<{
    id?: string;
    path: string;
    method?: string | null;
    compatibility?: string;
    severity?: string;
    message?: string;
    rule_id?: string;
  }> | null;
  workspaceRoot?: string;
}

/**
 * Calculates deterministic API Contract Coverage & Drift Impact.
 */
export function calculateContractCoverage(
  input: ContractCoverageInput
): ContractCoverageReport {
  const inv = input.inventory;
  const driftFindings = input.driftFindings || [];
  const workspaceRoot = input.workspaceRoot || "";

  if (!inv) {
    return {
      isAvailable: false,
      totalEndpoints: 0,
      documentedCount: 0,
      undocumentedCount: 0,
      driftedCount: 0,
      unknownCount: 0,
      unmatchedOperationsCount: 0,
      coveragePercentage: null,
      items: [],
      summaryText: "Contract Coverage · No scan data available",
      contractSpecs: [],
    };
  }

  const openApiSpecs = (inv.metadata?.openapi_specs_found || []).map((s) =>
    normalizePath(s, workspaceRoot)
  );
  const hasSpecs = openApiSpecs.length > 0;

  // Index drift findings by method + normalized route
  const findingsIndex = new Map<string, Array<{ compatibility?: string; severity?: string; message?: string }>>();
  for (const finding of driftFindings) {
    const route = normalizeRoute(finding.path);
    const method = finding.method ? finding.method.toUpperCase() : "*";
    const key = `${method}:${route}`;
    if (!findingsIndex.has(key)) findingsIndex.set(key, []);
    findingsIndex.get(key)!.push(finding);
    if (method !== "*") {
      const anyKey = `*:${route}`;
      if (!findingsIndex.has(anyKey)) findingsIndex.set(anyKey, []);
      findingsIndex.get(anyKey)!.push(finding);
    }
  }

  // Index discrepancies
  const discIndex = new Map<string, Array<{ type?: string; severity?: string; desc?: string; spec?: string }>>();
  const ghostDiscrepancies: Array<{ method: string; route: string; desc: string; spec?: string }> = [];

  if (inv.discrepancies && Array.isArray(inv.discrepancies)) {
    for (const d of inv.discrepancies) {
      const r = normalizeRoute(d.endpoint_path || d.endpoint || d.path || "");
      const m = d.method ? d.method.toUpperCase() : "*";
      const key = `${m}:${r}`;

      if (d.discrepancy_type === "ghost_endpoint") {
        ghostDiscrepancies.push({
          method: m === "*" ? "ANY" : m,
          route: r,
          desc: d.description || "Documented in contract but not implemented in code",
          spec: d.spec_evidence,
        });
        continue;
      }

      if (!discIndex.has(key)) discIndex.set(key, []);
      discIndex.get(key)!.push({
        type: d.discrepancy_type,
        severity: d.severity,
        desc: d.description,
        spec: d.spec_evidence,
      });

      if (m !== "*") {
        const anyKey = `*:${r}`;
        if (!discIndex.has(anyKey)) discIndex.set(anyKey, []);
        discIndex.get(anyKey)!.push({
          type: d.discrepancy_type,
          severity: d.severity,
          desc: d.description,
          spec: d.spec_evidence,
        });
      }
    }
  }

  // Map to accumulate deduplicated discovered endpoints
  // Key: `${method} ${route}`
  const endpointMap = new Map<
    string,
    {
      method: string;
      routePath: string;
      sourceFile?: string;
      lineNumber?: number;
      discoveryMethod?: string;
      contractPath?: string;
      affectedConsumers: Map<string, AffectedConsumer>;
      issues: Set<string>;
      explicitContract: boolean;
      explicitUndocumented: boolean;
    }
  >();

  // 1. Ingest declared server endpoints from AST
  const endpointsList = inv.endpoints || [];
  for (const ep of endpointsList) {
    const method = (ep.http_method || "GET").toUpperCase();
    const route = normalizeRoute(ep.route_path || "/");
    const key = `${method} ${route}`;

    let contractPath: string | undefined;
    const src = normalizePath(ep.source_file || "", workspaceRoot);
    const isContractFile = Boolean(src && (openApiSpecs.includes(src) || src.endsWith('.json') || src.endsWith('.yaml') || src.endsWith('.yml')));

    if (isContractFile) {
      contractPath = src;
    } else if (ep.discovery_method === "openapi_spec" || ep.discovery_method === "hybrid") {
      if (ep.evidence_source) {
        for (const s of openApiSpecs) {
          const basename = s.split("/").pop() || s;
          if (ep.evidence_source.includes(s) || ep.evidence_source.includes(basename)) {
            contractPath = s;
            break;
          }
        }
      }
      if (!contractPath && openApiSpecs.length > 0) {
        contractPath = openApiSpecs[0];
      }
    } else if (ep.evidence_source) {
      for (const s of openApiSpecs) {
        const basename = s.split("/").pop() || s;
        if (ep.evidence_source.includes(s) || ep.evidence_source.includes(basename)) {
          contractPath = s;
          break;
        }
      }
    }

    const isFromContract = Boolean(contractPath) || ep.discovery_method === "openapi_spec" || ep.discovery_method === "hybrid";

    if (!endpointMap.has(key)) {
      endpointMap.set(key, {
        method,
        routePath: route,
        sourceFile: isContractFile ? undefined : src,
        lineNumber: isContractFile ? undefined : ep.line_number,
        discoveryMethod: ep.discovery_method || "route_declaration",
        contractPath,
        affectedConsumers: new Map(),
        issues: new Set(),
        explicitContract: isFromContract,
        explicitUndocumented: false,
      });
    } else {
      const existing = endpointMap.get(key)!;
      if (!isContractFile && src) {
        existing.sourceFile = src;
        existing.lineNumber = ep.line_number;
      }
      if (isFromContract) {
        existing.explicitContract = true;
        if (!existing.contractPath && contractPath) {
          existing.contractPath = contractPath;
        }
      }
    }
  }

  // 2. Ingest external integrations (Consumers calling endpoints)
  const integrationsList = inv.integrations || [];
  for (const item of integrationsList) {
    const rawFilePath = item.file_path || "";
    const srcFileNorm = normalizePath(rawFilePath, workspaceRoot);
    const { routePath } = extractEndpointAndHost(item.target_url_or_host || "");
    const route = normalizeRoute(routePath);
    const operations = item.operations && item.operations.length > 0 ? item.operations : ["GET"];

    for (const rawOp of operations) {
      const method = rawOp.toUpperCase();
      const key = `${method} ${route}`;

      let entry = endpointMap.get(key);
      if (!entry) {
        entry = {
          method,
          routePath: route,
          discoveryMethod: "external_call",
          affectedConsumers: new Map(),
          issues: new Set(),
          explicitContract: false,
          explicitUndocumented: false,
        };
        endpointMap.set(key, entry);
      }

      if (srcFileNorm) {
        const consumerKey = `${srcFileNorm}:${item.line_number || 1}`;
        if (!entry.affectedConsumers.has(consumerKey)) {
          entry.affectedConsumers.set(consumerKey, {
            filePath: srcFileNorm,
            lineNumber: item.line_number,
            serviceName: item.service_name,
            operations: [method],
            codeSnippet: item.code_snippet,
          });
        }
      }
    }
  }

  // 3. Mark discrepancies (undocumented endpoints from scanner)
  if (inv.discrepancies) {
    for (const d of inv.discrepancies) {
      if (d.discrepancy_type === "undocumented_endpoint") {
        const method = (d.method || "ALL").toUpperCase();
        const route = normalizeRoute(d.endpoint_path || d.endpoint || d.path || "/");
        const key = `${method} ${route}`;
        let entry = endpointMap.get(key);
        if (!entry) {
          entry = {
            method: method === "ALL" ? "GET" : method,
            routePath: route,
            discoveryMethod: "discrepancy",
            affectedConsumers: new Map(),
            issues: new Set(),
            explicitContract: false,
            explicitUndocumented: true,
          };
          endpointMap.set(key, entry);
        } else {
          entry.explicitUndocumented = true;
        }
        entry.issues.add(d.description || "Endpoint is missing from OpenAPI specification.");
      }
    }
  }

  // 4. Classify each discovered endpoint
  let documentedCount = 0;
  let undocumentedCount = 0;
  let driftedCount = 0;
  let unknownCount = 0;

  const items: EndpointCoverageItem[] = [];

  for (const [, entry] of endpointMap.entries()) {
    const key = `${entry.method}:${entry.routePath}`;
    const findings = findingsIndex.get(key) || [];
    const discs = discIndex.get(key) || [];

    // Attach issues
    for (const f of findings) {
      entry.issues.add(f.message || "Contract drift detected");
    }
    for (const d of discs) {
      entry.issues.add(d.desc || `Discrepancy: ${d.type}`);
    }

    let status: CoverageStatus = "unknown";

    const hasDriftFinding = findings.some(
      (f) => f.compatibility === "breaking" || f.severity === "high" || f.severity === "critical"
    );
    const hasDriftDiscrepancy = discs.some((d) => d.type === "parameter_mismatch" || d.type === "response_mismatch");

    if (hasDriftFinding || hasDriftDiscrepancy || findings.length > 0) {
      status = "drifted";
      driftedCount++;
    } else if (entry.explicitUndocumented || discs.some((d) => d.type === "undocumented_endpoint")) {
      status = "undocumented";
      undocumentedCount++;
    } else if (entry.explicitContract || (entry.contractPath && entry.contractPath !== "unavailable")) {
      status = "documented";
      documentedCount++;
    } else if (hasSpecs) {
      // Contracts exist in workspace, but this endpoint is not in them
      status = "undocumented";
      entry.issues.add("Endpoint is not documented in any active contract specification.");
      undocumentedCount++;
    } else {
      // No contract specs exist in workspace
      status = "unknown";
      entry.issues.add("No API contract specification available in repository.");
      unknownCount++;
    }

    items.push({
      id: `endpoint:${entry.method}:${entry.routePath}`,
      method: entry.method,
      routePath: entry.routePath,
      status,
      contractPath: entry.contractPath,
      discoveryMethod: entry.discoveryMethod,
      sourceFile: entry.sourceFile,
      lineNumber: entry.lineNumber,
      affectedConsumers: Array.from(entry.affectedConsumers.values()),
      issues: Array.from(entry.issues),
    });
  }

  // 5. Ingest unmatched contract operations (ghost routes)
  let unmatchedOperationsCount = 0;
  for (const ghost of ghostDiscrepancies) {
    unmatchedOperationsCount++;
    items.push({
      id: `unmatched:${ghost.method}:${ghost.route}`,
      method: ghost.method,
      routePath: ghost.route,
      status: "unmatched_contract",
      contractPath: ghost.spec ? normalizePath(ghost.spec, workspaceRoot) : undefined,
      discoveryMethod: "contract_specification",
      affectedConsumers: [],
      issues: [ghost.desc],
    });
  }

  // Denominator: Total discovered endpoints in code
  const totalEndpoints = documentedCount + undocumentedCount + driftedCount + unknownCount;
  const coveragePercentage =
    totalEndpoints > 0 ? Math.round((documentedCount / totalEndpoints) * 100) : null;

  // Generate compact summary text
  let summaryText = "";
  if (totalEndpoints === 0) {
    summaryText = "Contract Coverage · 0 endpoints discovered";
  } else if (undocumentedCount === 0 && driftedCount === 0) {
    summaryText = `Contract Coverage · ${coveragePercentage}% · All endpoints documented`;
  } else {
    summaryText = `Contract Coverage · ${coveragePercentage}% · ${undocumentedCount} undocumented · ${driftedCount} drifted`;
  }

  return {
    isAvailable: true,
    totalEndpoints,
    documentedCount,
    undocumentedCount,
    driftedCount,
    unknownCount,
    unmatchedOperationsCount,
    coveragePercentage,
    items,
    summaryText,
    contractSpecs: openApiSpecs,
  };
}
