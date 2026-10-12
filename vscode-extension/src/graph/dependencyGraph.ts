/**
 * Dependency Guardian - API Dependency Graph Module
 *
 * Constructs a deterministic, deduplicated, and honest API Dependency Graph
 * from repository intelligence inventory, discovered endpoints, external integrations,
 * and contract drift findings.
 *
 * Relationships:
 *  - source file -> calls endpoint -> belongs to service
 *  - endpoint -> validated against contract
 *
 * If contract or relationship data is unavailable, it is honestly represented
 * as 'unknown' or 'unavailable' rather than hallucinating edges.
 */

export type GraphNodeType = "service" | "endpoint" | "source_file" | "contract";
export type GraphValidationStatus = "breaking" | "drift" | "clean" | "unknown";
export type GraphEdgeType = "calls" | "belongs_to" | "validated_by";

export interface GraphNode {
  id: string;
  type: GraphNodeType;
  label: string;
  subLabel?: string;
  status: GraphValidationStatus;
  filePath?: string;
  lineNumber?: number;
  method?: string;
  routePath?: string;
  serviceName?: string;
  contractPath?: string;
  discoveryMethod?: string;
  callCount?: number;
  callLocations?: Array<{ file: string; line: number }>;
  metadata: Record<string, any>;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
}

export interface GraphEdge {
  id: string;
  type: GraphEdgeType;
  source: string;
  target: string;
  label?: string;
  status: GraphValidationStatus;
  lineNumbers?: number[];
  operations?: string[];
  metadata?: Record<string, any>;
}

export interface DependencyGraphSummary {
  totalNodes: number;
  totalEdges: number;
  servicesCount: number;
  endpointsCount: number;
  sourceFilesCount: number;
  contractsCount: number;
  breakingCount: number;
  driftCount: number;
  cleanCount: number;
  unknownCount: number;
}

export interface DependencyGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  summary: DependencyGraphSummary;
  bounds: { width: number; height: number };
}

export interface GraphFilterOptions {
  searchQuery?: string;
  nodeType?: "all" | GraphNodeType;
  status?: "all" | "issues" | GraphValidationStatus;
}

export interface BuildGraphInput {
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
 * Normalizes file paths for stable node keys and display.
 */
export function normalizePath(rawPath: string, workspaceRoot?: string): string {
  if (!rawPath) return "";
  let p = rawPath.replace(/\\/g, "/");
  if (workspaceRoot) {
    const root = workspaceRoot.replace(/\\/g, "/");
    if (p.startsWith(root)) {
      p = p.substring(root.length);
      if (p.startsWith("/")) p = p.substring(1);
    }
  }
  if (p.startsWith("./")) {
    p = p.substring(2);
  }
  return p;
}

/**
 * Extracts route path and host from URL or host string.
 */
export function extractEndpointAndHost(urlOrHost: string): { routePath: string; hostOrService: string } {
  if (!urlOrHost) return { routePath: "/", hostOrService: "" };
  let trimmed = urlOrHost.trim();

  // Strip template vars like {var}/api/v1/... or {base_url}/...
  if (trimmed.startsWith("{") && trimmed.includes("}/")) {
    const idx = trimmed.indexOf("}/");
    return {
      routePath: trimmed.substring(idx + 1),
      hostOrService: trimmed.substring(0, idx + 1),
    };
  }

  try {
    if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
      const parsed = new URL(trimmed);
      return {
        routePath: decodeURIComponent(parsed.pathname) || "/",
        hostOrService: parsed.origin,
      };
    }
  } catch {
    // If not a full URL, split on first slash
  }

  const slashIdx = trimmed.indexOf("/");
  if (slashIdx >= 0) {
    return {
      routePath: trimmed.substring(slashIdx),
      hostOrService: trimmed.substring(0, slashIdx),
    };
  }

  return { routePath: trimmed.startsWith("/") ? trimmed : `/${trimmed}`, hostOrService: "" };
}

/**
 * Normalizes HTTP route paths for comparison.
 */
export function normalizeRoute(route: string): string {
  if (!route) return "/";
  let r = route.trim();
  if (!r.startsWith("/")) r = `/${r}`;
  if (r.length > 1 && r.endsWith("/")) r = r.slice(0, -1);
  return r;
}

/**
 * Builds the API Dependency Graph from actual discovered data.
 */
export function buildDependencyGraph(input: BuildGraphInput): DependencyGraphData {
  const nodesMap = new Map<string, GraphNode>();
  const edgesMap = new Map<string, GraphEdge>();

  const inv = input.inventory;
  const driftFindings = input.driftFindings || [];
  const workspaceRoot = input.workspaceRoot || "";

  if (!inv) {
    return createEmptyGraph();
  }

  const openApiSpecs = inv.metadata?.openapi_specs_found || [];

  // 1. Register API Contracts
  for (const specPath of openApiSpecs) {
    const normSpec = normalizePath(specPath, workspaceRoot);
    if (!normSpec) continue;
    const contractId = `contract:${normSpec}`;
    if (!nodesMap.has(contractId)) {
      const basename = normSpec.split("/").pop() || normSpec;
      nodesMap.set(contractId, {
        id: contractId,
        type: "contract",
        label: basename,
        subLabel: normSpec,
        status: "clean",
        filePath: normSpec,
        metadata: {
          specPath: normSpec,
          specFormat: normSpec.endsWith(".json") ? "OpenAPI JSON" : normSpec.endsWith(".yaml") || normSpec.endsWith(".yml") ? "OpenAPI YAML" : "API Specification",
        },
      });
    }
  }

  // Helper to index contract finding statuses by method + route
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

  // Helper to index discrepancies
  const discIndex = new Map<string, Array<{ type?: string; severity?: string; desc?: string; spec?: string }>>();
  if (inv.discrepancies && Array.isArray(inv.discrepancies)) {
    for (const d of inv.discrepancies) {
      const r = normalizeRoute(d.endpoint_path || d.endpoint || d.path || "");
      const m = d.method ? d.method.toUpperCase() : "*";
      const key = `${m}:${r}`;
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

  // Helper to assess validation status honestly
  function evaluateEndpointStatus(
    method: string,
    route: string,
    hasContract: boolean
  ): { status: GraphValidationStatus; reasons: string[] } {
    const reasons: string[] = [];
    const key = `${method}:${route}`;
    const findings = findingsIndex.get(key) || [];
    const discs = discIndex.get(key) || [];

    let isBreaking = false;
    let isDrift = false;

    for (const f of findings) {
      if (f.compatibility === "breaking" || f.severity === "critical" || f.severity === "high") {
        isBreaking = true;
        reasons.push(f.message || "Breaking contract change");
      } else {
        isDrift = true;
        reasons.push(f.message || "Contract drift detected");
      }
    }

    for (const d of discs) {
      if (d.severity === "high" || d.type === "ghost_endpoint") {
        isBreaking = true;
        reasons.push(d.desc || `Discrepancy: ${d.type}`);
      } else {
        isDrift = true;
        reasons.push(d.desc || `Discrepancy: ${d.type}`);
      }
    }

    if (isBreaking) return { status: "breaking", reasons };
    if (isDrift) return { status: "drift", reasons };
    if (hasContract) return { status: "clean", reasons: ["Validated against contract specification"] };
    return { status: "unknown", reasons: ["No validating contract specification available"] };
  }

  // 2. Process Discovered Endpoints
  const endpointsList = inv.endpoints || [];
  for (const ep of endpointsList) {
    const method = (ep.http_method || "GET").toUpperCase();
    const route = normalizeRoute(ep.route_path || "/");
    const epId = `endpoint:${method}:${route}`;

    let contractId: string | undefined;
    let contractPath: string | undefined;

    // Check if source_file or evidence_source points to a contract
    const src = normalizePath(ep.source_file || "", workspaceRoot);
    if (src && openApiSpecs.some((s) => normalizePath(s, workspaceRoot) === src)) {
      contractPath = src;
      contractId = `contract:${src}`;
    } else if (ep.evidence_source && ep.evidence_source.includes("contracts/")) {
      for (const s of openApiSpecs) {
        const normS = normalizePath(s, workspaceRoot);
        if (ep.evidence_source.includes(normS)) {
          contractPath = normS;
          contractId = `contract:${normS}`;
          break;
        }
      }
    }

    // Determine default service for locally declared endpoints
    let serviceName = "Local Application Service";
    if (contractPath && !src.endsWith(".py") && !src.endsWith(".ts") && !src.endsWith(".js")) {
      serviceName = "Upstream Contract API";
    }

    const serviceId = `service:${serviceName.toLowerCase().replace(/[^a-z0-9_-]/g, "_")}`;
    if (!nodesMap.has(serviceId)) {
      nodesMap.set(serviceId, {
        id: serviceId,
        type: "service",
        label: serviceName,
        subLabel: contractPath ? "Contract Target" : "Local Workspace Service",
        status: "clean",
        metadata: {
          serviceName,
          isInternal: serviceName === "Local Application Service",
        },
      });
    }

    const hasContract = Boolean(contractId);
    const { status, reasons } = evaluateEndpointStatus(method, route, hasContract);

    if (!nodesMap.has(epId)) {
      nodesMap.set(epId, {
        id: epId,
        type: "endpoint",
        label: `${method} ${route}`,
        subLabel: method,
        method,
        routePath: route,
        serviceName,
        contractPath: contractPath || "unavailable",
        status,
        discoveryMethod: ep.discovery_method || "unknown",
        filePath: src || (contractPath ? contractPath : undefined),
        lineNumber: ep.line_number,
        callCount: 0,
        callLocations: [],
        metadata: {
          summary: ep.summary,
          parametersCount: ep.parameters?.length || 0,
          responsesCount: ep.responses?.length || 0,
          statusReasons: reasons,
          hasContract,
        },
      });
    }

    // Relationship: endpoint -> belongs to service
    const belongsEdgeId = `belongs:${epId}->${serviceId}`;
    if (!edgesMap.has(belongsEdgeId)) {
      edgesMap.set(belongsEdgeId, {
        id: belongsEdgeId,
        type: "belongs_to",
        source: epId,
        target: serviceId,
        status: "clean",
        label: "belongs to",
      });
    }

    // Relationship: endpoint -> validated against contract
    if (contractId) {
      const validatedEdgeId = `validated:${epId}->${contractId}`;
      if (!edgesMap.has(validatedEdgeId)) {
        edgesMap.set(validatedEdgeId, {
          id: validatedEdgeId,
          type: "validated_by",
          source: epId,
          target: contractId,
          status,
          label: "validated against",
        });
      }
    }
  }

  // 3. Process External Integrations (Consumer files calling endpoints & services)
  const integrationsList = inv.integrations || [];
  for (const item of integrationsList) {
    const rawFilePath = item.file_path || "unknown_consumer";
    const srcFileNorm = normalizePath(rawFilePath, workspaceRoot);
    const srcFileId = `file:${srcFileNorm}`;

    // Source File Node
    if (!nodesMap.has(srcFileId)) {
      const base = srcFileNorm.split("/").pop() || srcFileNorm;
      nodesMap.set(srcFileId, {
        id: srcFileId,
        type: "source_file",
        label: base,
        subLabel: srcFileNorm,
        status: "clean",
        filePath: srcFileNorm,
        callCount: 0,
        callLocations: [],
        metadata: {
          path: srcFileNorm,
          consumerFile: true,
        },
      });
    }

    const { routePath, hostOrService } = extractEndpointAndHost(item.target_url_or_host || "");
    const route = normalizeRoute(routePath);
    const operations = (item.operations && item.operations.length > 0) ? item.operations : ["GET"];

    // Service identification
    let serviceName = (item.service_name || hostOrService || "External HTTP Service").trim();
    if (hostOrService && hostOrService.startsWith("http")) {
      serviceName = `${item.service_name || "External Service"} (${hostOrService.replace(/^https?:\/\//, "")})`;
    }
    const serviceId = `service:${serviceName.toLowerCase().replace(/[^a-z0-9_-]/g, "_")}`;
    if (!nodesMap.has(serviceId)) {
      nodesMap.set(serviceId, {
        id: serviceId,
        type: "service",
        label: serviceName,
        subLabel: hostOrService || "External Host",
        status: "clean",
        metadata: {
          serviceName,
          targetUrlOrHost: item.target_url_or_host,
          integrationType: item.integration_type || "http_service",
        },
      });
    }

    for (const rawOp of operations) {
      const method = rawOp.toUpperCase();
      const epId = `endpoint:${method}:${route}`;

      // Check if endpoint exists or register it
      let epNode = nodesMap.get(epId);
      if (!epNode) {
        // Match with openapi contracts if possible
        let matchedContractId: string | undefined;
        let matchedContractPath: string | undefined;

        // Honest contract matching: check if discrepancies link this endpoint to a spec
        const key = `${method}:${route}`;
        const discs = discIndex.get(key) || [];
        for (const d of discs) {
          if (d.spec) {
            for (const s of openApiSpecs) {
              const normS = normalizePath(s, workspaceRoot);
              if (d.spec.includes(normS)) {
                matchedContractPath = normS;
                matchedContractId = `contract:${normS}`;
                break;
              }
            }
          }
        }

        const hasContract = Boolean(matchedContractId);
        const { status, reasons } = evaluateEndpointStatus(method, route, hasContract);

        epNode = {
          id: epId,
          type: "endpoint",
          label: `${method} ${route}`,
          subLabel: method,
          method,
          routePath: route,
          serviceName,
          contractPath: matchedContractPath || "unavailable",
          status,
          discoveryMethod: "external_call",
          filePath: srcFileNorm,
          lineNumber: item.line_number,
          callCount: 0,
          callLocations: [],
          metadata: {
            statusReasons: reasons,
            hasContract,
            codeSnippet: item.code_snippet,
          },
        };
        nodesMap.set(epId, epNode);

        if (matchedContractId) {
          const valEdgeId = `validated:${epId}->${matchedContractId}`;
          if (!edgesMap.has(valEdgeId)) {
            edgesMap.set(valEdgeId, {
              id: valEdgeId,
              type: "validated_by",
              source: epId,
              target: matchedContractId,
              status,
              label: "validated against",
            });
          }
        }
      }

      // Track call location on endpoint node
      if (item.line_number) {
        epNode.callCount = (epNode.callCount || 0) + 1;
        epNode.callLocations = epNode.callLocations || [];
        if (!epNode.callLocations.some((c) => c.file === srcFileNorm && c.line === item.line_number)) {
          epNode.callLocations.push({ file: srcFileNorm, line: item.line_number });
        }
      }

      // Relationship: endpoint -> belongs to service
      const belongsEdgeId = `belongs:${epId}->${serviceId}`;
      if (!edgesMap.has(belongsEdgeId)) {
        edgesMap.set(belongsEdgeId, {
          id: belongsEdgeId,
          type: "belongs_to",
          source: epId,
          target: serviceId,
          status: "clean",
          label: "belongs to",
        });
      }

      // Relationship: source file -> calls endpoint
      const callEdgeId = `call:${srcFileId}->${epId}`;
      const existingCallEdge = edgesMap.get(callEdgeId);
      if (existingCallEdge) {
        // Deduplicate repeated calls: accumulate lines and operations
        if (item.line_number && !existingCallEdge.lineNumbers?.includes(item.line_number)) {
          existingCallEdge.lineNumbers = existingCallEdge.lineNumbers || [];
          existingCallEdge.lineNumbers.push(item.line_number);
          existingCallEdge.lineNumbers.sort((a, b) => a - b);
          existingCallEdge.label = `calls (${existingCallEdge.lineNumbers.join(", ")})`;
        }
        if (!existingCallEdge.operations?.includes(method)) {
          existingCallEdge.operations = existingCallEdge.operations || [];
          existingCallEdge.operations.push(method);
        }
      } else {
        const lineNumbers = item.line_number ? [item.line_number] : [];
        edgesMap.set(callEdgeId, {
          id: callEdgeId,
          type: "calls",
          source: srcFileId,
          target: epId,
          status: epNode.status,
          lineNumbers,
          operations: [method],
          label: lineNumbers.length > 0 ? `calls (line ${lineNumbers.join(", ")})` : "calls",
        });
      }

      // Track calls on source file node
      const fileNode = nodesMap.get(srcFileId);
      if (fileNode) {
        fileNode.callCount = (fileNode.callCount || 0) + 1;
        fileNode.callLocations = fileNode.callLocations || [];
        if (item.line_number && !fileNode.callLocations.some((c) => c.line === item.line_number)) {
          fileNode.callLocations.push({ file: srcFileNorm, line: item.line_number });
        }
      }
    }
  }

  // 4. Propagate Status to Services, Source Files, and Contracts
  for (const node of nodesMap.values()) {
    if (node.type === "service") {
      const childEndpoints = Array.from(edgesMap.values())
        .filter((e) => e.type === "belongs_to" && e.target === node.id)
        .map((e) => nodesMap.get(e.source))
        .filter(Boolean) as GraphNode[];

      if (childEndpoints.some((e) => e.status === "breaking")) {
        node.status = "breaking";
      } else if (childEndpoints.some((e) => e.status === "drift")) {
        node.status = "drift";
      } else if (childEndpoints.length > 0 && childEndpoints.every((e) => e.status === "clean")) {
        node.status = "clean";
      } else {
        node.status = "unknown";
      }
      node.metadata.endpointCount = childEndpoints.length;
    } else if (node.type === "source_file") {
      const calledEndpoints = Array.from(edgesMap.values())
        .filter((e) => e.type === "calls" && e.source === node.id)
        .map((e) => nodesMap.get(e.target))
        .filter(Boolean) as GraphNode[];

      if (calledEndpoints.some((e) => e.status === "breaking")) {
        node.status = "breaking";
      } else if (calledEndpoints.some((e) => e.status === "drift")) {
        node.status = "drift";
      } else if (calledEndpoints.length > 0 && calledEndpoints.every((e) => e.status === "clean")) {
        node.status = "clean";
      } else {
        node.status = "unknown";
      }
      node.metadata.targetEndpointCount = calledEndpoints.length;
    } else if (node.type === "contract") {
      const validatedEndpoints = Array.from(edgesMap.values())
        .filter((e) => e.type === "validated_by" && e.target === node.id)
        .map((e) => nodesMap.get(e.source))
        .filter(Boolean) as GraphNode[];

      if (validatedEndpoints.some((e) => e.status === "breaking")) {
        node.status = "breaking";
      } else if (validatedEndpoints.some((e) => e.status === "drift")) {
        node.status = "drift";
      } else {
        node.status = "clean";
      }
      node.metadata.validatedEndpointCount = validatedEndpoints.length;
    }
  }

  // 5. Compute Deterministic Layout (DAG Columns)
  const nodes = Array.from(nodesMap.values());
  const edges = Array.from(edgesMap.values());

  const layoutBounds = computeLayout(nodes);

  // 6. Compute Summary Metrics
  const summary: DependencyGraphSummary = {
    totalNodes: nodes.length,
    totalEdges: edges.length,
    servicesCount: nodes.filter((n) => n.type === "service").length,
    endpointsCount: nodes.filter((n) => n.type === "endpoint").length,
    sourceFilesCount: nodes.filter((n) => n.type === "source_file").length,
    contractsCount: nodes.filter((n) => n.type === "contract").length,
    breakingCount: nodes.filter((n) => n.status === "breaking").length,
    driftCount: nodes.filter((n) => n.status === "drift").length,
    cleanCount: nodes.filter((n) => n.status === "clean").length,
    unknownCount: nodes.filter((n) => n.status === "unknown").length,
  };

  return {
    nodes,
    edges,
    summary,
    bounds: layoutBounds,
  };
}

/**
 * Computes deterministic X and Y coordinates for all graph nodes in a 4-column layout.
 *
 * Column 0: Source Files (Consumers)
 * Column 1: Endpoints
 * Column 2: Services
 * Column 3: Contracts
 */
function computeLayout(nodes: GraphNode[]): { width: number; height: number } {
  const col0 = nodes.filter((n) => n.type === "source_file");
  const col1 = nodes.filter((n) => n.type === "endpoint");
  const col2 = nodes.filter((n) => n.type === "service");
  const col3 = nodes.filter((n) => n.type === "contract");

  const colWidths = [220, 260, 220, 220];
  const colX = [40, 320, 640, 920];
  const nodeHeight = 44;
  const gapY = 22;
  const startY = 40;

  const positionColumn = (list: GraphNode[], columnIndex: number) => {
    const x = colX[columnIndex];
    const width = colWidths[columnIndex];
    list.forEach((node, idx) => {
      node.x = x;
      node.y = startY + idx * (nodeHeight + gapY);
      node.width = width;
      node.height = nodeHeight;
    });
  };

  positionColumn(col0, 0);
  positionColumn(col1, 1);
  positionColumn(col2, 2);
  positionColumn(col3, 3);

  const maxRows = Math.max(col0.length, col1.length, col2.length, col3.length, 1);
  const totalHeight = Math.max(500, startY + maxRows * (nodeHeight + gapY) + 60);
  const totalWidth = 1200;

  return { width: totalWidth, height: totalHeight };
}

/**
 * Filters graph data based on search queries and type/status filters.
 */
export function filterDependencyGraph(data: DependencyGraphData, options: GraphFilterOptions): DependencyGraphData {
  if (!data || !data.nodes) return createEmptyGraph();

  let filteredNodes = [...data.nodes];

  // Type filter
  if (options.nodeType && options.nodeType !== "all") {
    filteredNodes = filteredNodes.filter((n) => n.type === options.nodeType);
  }

  // Status filter
  if (options.status && options.status !== "all") {
    if (options.status === "issues") {
      filteredNodes = filteredNodes.filter((n) => n.status === "breaking" || n.status === "drift");
    } else {
      filteredNodes = filteredNodes.filter((n) => n.status === options.status);
    }
  }

  // Search query filter
  if (options.searchQuery && options.searchQuery.trim()) {
    const q = options.searchQuery.trim().toLowerCase();
    filteredNodes = filteredNodes.filter(
      (n) =>
        n.label.toLowerCase().includes(q) ||
        (n.subLabel && n.subLabel.toLowerCase().includes(q)) ||
        (n.routePath && n.routePath.toLowerCase().includes(q)) ||
        (n.filePath && n.filePath.toLowerCase().includes(q)) ||
        (n.serviceName && n.serviceName.toLowerCase().includes(q))
    );
  }

  const visibleNodeIds = new Set(filteredNodes.map((n) => n.id));

  // Include edges whose source and target are both visible
  const filteredEdges = data.edges.filter((e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target));

  return {
    nodes: filteredNodes,
    edges: filteredEdges,
    summary: data.summary,
    bounds: data.bounds,
  };
}

/**
 * Creates an empty graph payload.
 */
function createEmptyGraph(): DependencyGraphData {
  return {
    nodes: [],
    edges: [],
    summary: {
      totalNodes: 0,
      totalEdges: 0,
      servicesCount: 0,
      endpointsCount: 0,
      sourceFilesCount: 0,
      contractsCount: 0,
      breakingCount: 0,
      driftCount: 0,
      cleanCount: 0,
      unknownCount: 0,
    },
    bounds: { width: 1200, height: 500 },
  };
}
