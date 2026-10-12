const { describe, it } = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const Module = require("node:module");

const mockVscode = {
  ViewColumn: { One: 1, Two: 2 },
  Uri: {
    file: (p) => ({ fsPath: p, toString: () => `file://${p}` }),
    parse: (u) => ({ fsPath: u, toString: () => u }),
  },
  window: {
    activeTextEditor: undefined,
    createWebviewPanel: (viewType, title, showOptions, options) => {
      let htmlContent = "";
      const messageListeners = [];
      return {
        viewType,
        title,
        options,
        reveal: () => {},
        dispose: () => {},
        onDidDispose: () => ({ dispose: () => {} }),
        webview: {
          options: {},
          set html(val) {
            htmlContent = val;
          },
          get html() {
            return htmlContent;
          },
          postMessage: () => Promise.resolve(true),
          onDidReceiveMessage: (fn) => {
            messageListeners.push(fn);
            return { dispose: () => {} };
          },
        },
      };
    },
    showInformationMessage: () => Promise.resolve(undefined),
    showWarningMessage: () => Promise.resolve(undefined),
    showErrorMessage: () => Promise.resolve(undefined),
    createOutputChannel: () => ({
      appendLine: () => {},
      show: () => {},
      dispose: () => {},
    }),
  },
  workspace: {
    getConfiguration: () => ({
      get: (_k, def) => def,
      update: () => Promise.resolve(),
    }),
  },
};

const originalLoad = Module._load;
Module._load = function (request, parent, isMain) {
  if (request === "vscode") {
    return mockVscode;
  }
  return originalLoad.apply(this, arguments);
};

const {
  buildDependencyGraph,
  filterDependencyGraph,
  normalizeRoute,
  extractEndpointAndHost,
  normalizePath,
} = require("../dist/graph/dependencyGraph.js");

describe("API Dependency Graph Suite", () => {
  const realInventoryPath = path.resolve(__dirname, "../../reports/repository-inventory/repository-inventory.json");
  const hasRealInventory = fs.existsSync(realInventoryPath);

  it("Test 1: Builds graph from real repository inventory with four entity types and valid relationships", () => {
    if (!hasRealInventory) {
      return;
    }

    const realInventory = JSON.parse(fs.readFileSync(realInventoryPath, "utf8"));
    const graph = buildDependencyGraph({
      inventory: realInventory,
      workspaceRoot: "/home/last-hope/Dnyaneshwar/HackWave",
    });

    assert.ok(graph, "Graph must be defined");
    assert.ok(graph.nodes.length > 0, "Graph must contain nodes");
    assert.ok(graph.edges.length > 0, "Graph must contain edges");

    // Verify entity types
    const types = new Set(graph.nodes.map((n) => n.type));
    assert.ok(types.has("service"), "Graph must contain service nodes");
    assert.ok(types.has("endpoint"), "Graph must contain endpoint nodes");
    assert.ok(types.has("source_file"), "Graph must contain source_file nodes");
    assert.ok(types.has("contract"), "Graph must contain contract nodes");

    // Verify relationships: source file -> calls endpoint -> belongs to service, endpoint -> validated against contract
    const edgeTypes = new Set(graph.edges.map((e) => e.type));
    assert.ok(edgeTypes.has("calls"), "Graph must contain 'calls' edges");
    assert.ok(edgeTypes.has("belongs_to"), "Graph must contain 'belongs_to' edges");
    assert.ok(edgeTypes.has("validated_by"), "Graph must contain 'validated_by' edges");

    // Verify deterministic layout positioning
    for (const node of graph.nodes) {
      assert.strictEqual(typeof node.x, "number", `Node ${node.id} must have numeric x`);
      assert.strictEqual(typeof node.y, "number", `Node ${node.id} must have numeric y`);
      assert.strictEqual(typeof node.width, "number", `Node ${node.id} must have numeric width`);
      assert.strictEqual(typeof node.height, "number", `Node ${node.id} must have numeric height`);
      assert.ok(node.x >= 0, "Node x must be non-negative");
      assert.ok(node.y >= 0, "Node y must be non-negative");
    }

    // Verify summary matches node counts
    assert.strictEqual(graph.summary.totalNodes, graph.nodes.length);
    assert.strictEqual(graph.summary.totalEdges, graph.edges.length);
    assert.strictEqual(graph.summary.servicesCount, graph.nodes.filter((n) => n.type === "service").length);
    assert.strictEqual(graph.summary.endpointsCount, graph.nodes.filter((n) => n.type === "endpoint").length);
    assert.strictEqual(graph.summary.sourceFilesCount, graph.nodes.filter((n) => n.type === "source_file").length);
    assert.strictEqual(graph.summary.contractsCount, graph.nodes.filter((n) => n.type === "contract").length);
  });

  it("Test 2: Deduplicates repeated discoveries and aggregates call sites", () => {
    const mockInventory = {
      metadata: {
        openapi_specs_found: ["contracts/sample.json"],
      },
      integrations: [
        {
          service_name: "Order Service",
          target_url_or_host: "http://api.internal/orders",
          file_path: "src/client.ts",
          line_number: 42,
          operations: ["GET"],
        },
        {
          service_name: "Order Service",
          target_url_or_host: "http://api.internal/orders",
          file_path: "src/client.ts",
          line_number: 88,
          operations: ["GET"],
        },
        {
          service_name: "Order Service",
          target_url_or_host: "http://api.internal/orders",
          file_path: "src/client.ts",
          line_number: 42, // exact duplicate line
          operations: ["GET"],
        },
      ],
      endpoints: [],
      discrepancies: [],
    };

    const graph = buildDependencyGraph({ inventory: mockInventory });

    // Should have only 1 file node, 1 endpoint node, 1 service node
    const fileNodes = graph.nodes.filter((n) => n.type === "source_file");
    const endpointNodes = graph.nodes.filter((n) => n.type === "endpoint");
    const serviceNodes = graph.nodes.filter((n) => n.type === "service");

    assert.strictEqual(fileNodes.length, 1, "Must deduplicate source_file node");
    assert.strictEqual(endpointNodes.length, 1, "Must deduplicate endpoint node");
    assert.strictEqual(serviceNodes.length, 1, "Must deduplicate service node");

    // Must have exactly 1 'calls' edge between client.ts and GET /orders
    const callEdges = graph.edges.filter((e) => e.type === "calls");
    assert.strictEqual(callEdges.length, 1, "Must deduplicate calls edge");

    // Edge must aggregate line numbers without duplicates: [42, 88]
    assert.deepStrictEqual(callEdges[0].lineNumbers, [42, 88]);
    assert.ok(callEdges[0].label.includes("42, 88"));
  });

  it("Test 3: Honestly represents unavailable contracts as unknown without inventing edges", () => {
    const mockInventory = {
      metadata: {
        openapi_specs_found: [], // No contracts discovered
      },
      integrations: [
        {
          service_name: "Adhoc Legacy API",
          target_url_or_host: "https://legacy.example.com/v1/status",
          file_path: "src/legacy.ts",
          line_number: 15,
          operations: ["GET"],
        },
      ],
      endpoints: [
        {
          http_method: "POST",
          route_path: "/internal/debug",
          source_file: "src/server.ts",
          line_number: 100,
          discovery_method: "framework_ast",
        },
      ],
      discrepancies: [],
    };

    const graph = buildDependencyGraph({ inventory: mockInventory });

    // Verify 0 contracts discovered
    assert.strictEqual(graph.summary.contractsCount, 0);

    // Verify endpoint nodes have status 'unknown' and contractPath 'unavailable'
    for (const ep of graph.nodes.filter((n) => n.type === "endpoint")) {
      assert.strictEqual(ep.status, "unknown", `Endpoint ${ep.id} status must be unknown`);
      assert.strictEqual(ep.contractPath, "unavailable", `Endpoint ${ep.id} contract must be unavailable`);
    }

    // Verify NO 'validated_by' edges were invented
    const validatedEdges = graph.edges.filter((e) => e.type === "validated_by");
    assert.strictEqual(validatedEdges.length, 0, "No validated_by edges should exist when contracts are missing");
  });

  it("Test 4: Propagates breaking contract findings and discrepancies accurately", () => {
    const mockInventory = {
      metadata: {
        openapi_specs_found: ["contracts/v1.json"],
      },
      endpoints: [
        {
          http_method: "GET",
          route_path: "/users/{id}",
          source_file: "contracts/v1.json",
          discovery_method: "openapi_spec",
        },
        {
          http_method: "POST",
          route_path: "/users",
          source_file: "contracts/v1.json",
          discovery_method: "openapi_spec",
        },
      ],
      integrations: [
        {
          service_name: "User Service",
          target_url_or_host: "http://api/users/{id}",
          file_path: "src/userClient.ts",
          line_number: 25,
          operations: ["GET"],
        },
      ],
      discrepancies: [
        {
          discrepancy_type: "ghost_endpoint",
          endpoint_path: "/users/{id}",
          method: "GET",
          description: "Endpoint removed in backend",
          severity: "high",
        },
      ],
    };

    const graph = buildDependencyGraph({
      inventory: mockInventory,
      driftFindings: [
        {
          path: "/users/{id}",
          method: "GET",
          compatibility: "breaking",
          message: "Breaking removal",
        },
      ],
    });

    const brokenEp = graph.nodes.find((n) => n.id === "endpoint:GET:/users/{id}");
    assert.ok(brokenEp, "Broken endpoint must exist");
    assert.strictEqual(brokenEp.status, "breaking", "Endpoint with breaking finding must have status 'breaking'");

    const cleanEp = graph.nodes.find((n) => n.id === "endpoint:POST:/users");
    assert.ok(cleanEp, "Clean endpoint must exist");
    assert.strictEqual(cleanEp.status, "clean", "Endpoint without drift must have status 'clean'");

    // Source file calling broken endpoint should reflect breaking status
    const fileNode = graph.nodes.find((n) => n.id === "file:src/userClient.ts");
    assert.ok(fileNode);
    assert.strictEqual(fileNode.status, "breaking", "Consumer file calling breaking endpoint must propagate status");
  });

  it("Test 5: Node details, search filter, and type/status filtering", () => {
    const mockInventory = {
      metadata: { openapi_specs_found: ["contracts/orders.json"] },
      endpoints: [
        { http_method: "GET", route_path: "/orders", source_file: "contracts/orders.json" },
        { http_method: "POST", route_path: "/orders", source_file: "contracts/orders.json" },
      ],
      integrations: [
        {
          service_name: "Order API",
          target_url_or_host: "http://orders/orders",
          file_path: "client/orders.ts",
          line_number: 10,
          operations: ["GET"],
        },
      ],
      discrepancies: [],
    };

    const graph = buildDependencyGraph({ inventory: mockInventory });

    // Filter by type: endpoint
    const endpointsOnly = filterDependencyGraph(graph, { nodeType: "endpoint" });
    assert.ok(endpointsOnly.nodes.every((n) => n.type === "endpoint"));
    assert.strictEqual(endpointsOnly.nodes.length, 2);

    // Filter by type: service
    const servicesOnly = filterDependencyGraph(graph, { nodeType: "service" });
    assert.ok(servicesOnly.nodes.every((n) => n.type === "service"));

    // Search query filter: "client"
    const searched = filterDependencyGraph(graph, { searchQuery: "client" });
    assert.strictEqual(searched.nodes.length, 1);
    assert.strictEqual(searched.nodes[0].id, "file:client/orders.ts");

    // Search query filter: "orders"
    const searchedOrders = filterDependencyGraph(graph, { searchQuery: "orders" });
    assert.ok(searchedOrders.nodes.length > 0);
  });

  it("Test 6: Gracefully handles empty, missing, or malformed data", () => {
    // Null input
    const empty1 = buildDependencyGraph({ inventory: null });
    assert.strictEqual(empty1.nodes.length, 0);
    assert.strictEqual(empty1.edges.length, 0);
    assert.strictEqual(empty1.summary.totalNodes, 0);

    // Empty object
    const empty2 = buildDependencyGraph({ inventory: {} });
    assert.strictEqual(empty2.nodes.length, 0);

    // Large scale data resilience (300 endpoints, 100 integrations)
    const largeInventory = {
      metadata: { openapi_specs_found: ["contracts/large.json"] },
      endpoints: Array.from({ length: 300 }, (_, i) => ({
        http_method: i % 2 === 0 ? "GET" : "POST",
        route_path: `/api/v1/resource_${i}`,
        source_file: "contracts/large.json",
      })),
      integrations: Array.from({ length: 100 }, (_, i) => ({
        service_name: `Service_${i % 5}`,
        target_url_or_host: `http://srv${i % 5}/api/v1/resource_${i}`,
        file_path: `src/consumer_${i % 10}.ts`,
        line_number: i + 1,
        operations: ["GET"],
      })),
      discrepancies: [],
    };

    const start = Date.now();
    const largeGraph = buildDependencyGraph({ inventory: largeInventory });
    const elapsed = Date.now() - start;

    assert.ok(largeGraph.nodes.length >= 300, "Large graph must construct all nodes");
    assert.ok(elapsed < 200, `Graph construction should be fast (took ${elapsed}ms)`);
    assert.ok(largeGraph.bounds.height > 1000, "Bounds should adapt to row count");
  });

  it("Test 7: URL and route path extraction helpers handle edge cases safely", () => {
    assert.strictEqual(normalizeRoute(""), "/");
    assert.strictEqual(normalizeRoute("api/users"), "/api/users");
    assert.strictEqual(normalizeRoute("/api/users/"), "/api/users");

    const host1 = extractEndpointAndHost("http://localhost:8000/api/v1/health");
    assert.strictEqual(host1.routePath, "/api/v1/health");
    assert.strictEqual(host1.hostOrService, "http://localhost:8000");

    const host2 = extractEndpointAndHost("{var}/api/v1/projects");
    assert.strictEqual(host2.routePath, "/api/v1/projects");
    assert.strictEqual(host2.hostOrService, "{var}");

    const normP = normalizePath("/home/last-hope/Dnyaneshwar/HackWave/client.py", "/home/last-hope/Dnyaneshwar/HackWave");
    assert.strictEqual(normP, "client.py");
  });

  it("Test 8: Manifest declares dependencyGuardian.openDependencyGraph command", () => {
    const pkgPath = path.resolve(__dirname, "../package.json");
    const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
    const cmd = pkg.contributes.commands.find((c) => c.command === "dependencyGuardian.openDependencyGraph");
    assert.ok(cmd, "dependencyGuardian.openDependencyGraph must be registered in contributes.commands");
    assert.strictEqual(cmd.title, "Dependency Guardian: View API Dependency Graph");
  });

  it("Test 9: Webview HTML renders collapsed-by-default API Dependency Graph with SVG canvas and details drawer", () => {
    const { GuardianDashboardPanel } = require("../dist/webview/guardianPanel.js");
    const { GuardianClient } = require("../dist/api/guardianClient.js");

    GuardianDashboardPanel.currentPanel = undefined;
    const mockUri = { fsPath: "/ext" };
    const client = new GuardianClient("http://localhost:8000");

    GuardianDashboardPanel.createOrShow(mockUri, client, undefined, undefined, "/dummy/workspace");
    const panel = GuardianDashboardPanel.currentPanel;
    assert.ok(panel, "Panel must be initialized");

    const html = panel._panel.webview.html;

    // Check section container
    assert.ok(html.includes('id="apiDependencyGraphSection"'), "Must contain #apiDependencyGraphSection");
    assert.ok(html.includes('id="graphHeaderToggle"'), "Must contain header toggle");
    assert.ok(html.includes('id="btnToggleGraph"'), "Must contain expand/collapse button");
    assert.ok(html.includes('id="graphContainerBody" style="display: none;'), "Must be collapsed by default");

    // Check summary pills
    assert.ok(html.includes('id="pillGraphServices"'), "Must contain services summary pill");
    assert.ok(html.includes('id="pillGraphEndpoints"'), "Must contain endpoints summary pill");
    assert.ok(html.includes('id="pillGraphConsumers"'), "Must contain consumers summary pill");
    assert.ok(html.includes('id="pillGraphContracts"'), "Must contain contracts summary pill");

    // Check interactive toolbar controls
    assert.ok(html.includes('id="graphSearchInput"'), "Must contain graph search input");
    assert.ok(html.includes('data-action="gType"'), "Must contain type filter buttons");
    assert.ok(html.includes('data-action="gStatus"'), "Must contain status filter buttons");
    assert.ok(html.includes('graphZoom(1.2)'), "Must contain zoom in button");
    assert.ok(html.includes('graphZoom(0.8)'), "Must contain zoom out button");
    assert.ok(html.includes('graphFitView()'), "Must contain fit view button");
    assert.ok(html.includes('graphResetView()'), "Must contain reset view button");
    assert.ok(html.includes('requestRefreshGraph()'), "Must contain refresh button");

    // Check SVG canvas and details drawer
    assert.ok(html.includes('id="dependencyGraphSvg"'), "Must contain #dependencyGraphSvg element");
    assert.ok(html.includes('id="graphEdgesLayer"'), "Must contain edges SVG layer");
    assert.ok(html.includes('id="graphNodesLayer"'), "Must contain nodes SVG layer");
    assert.ok(html.includes('id="graphNodeDetailsDrawer"'), "Must contain node details drawer");
    assert.ok(html.includes('id="graphDrawerEmpty"'), "Must contain empty drawer message");
    assert.ok(html.includes('id="graphDrawerContent"'), "Must contain drawer content container");
  });
});
