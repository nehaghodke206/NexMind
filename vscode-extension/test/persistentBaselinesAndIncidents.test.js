const test = require("node:test");
const assert = require("node:assert");
const path = require("node:path");
const Module = require("node:module");

// Setup lightweight vscode mock for Node test runner
const mockConfigStore = new Map([
  ["dependencyGuardian.backendUrl", "http://localhost:8000"],
  ["dependencyGuardian.projectId", "proj_test_123"],
  ["dependencyGuardian.autoSyncBackend", true],
  ["dependencyGuardian.detectionMode", "hybrid"],
]);

const mockVscode = {
  ViewColumn: { One: 1, Two: 2 },
  Uri: {
    file: (p) => ({ fsPath: p, toString: () => `file://${p}` }),
    parse: (u) => ({ fsPath: u, toString: () => u }),
  },
  ConfigurationTarget: {
    Global: 1,
    Workspace: 2,
    WorkspaceFolder: 3,
  },
  window: {
    createOutputChannel: () => ({
      append: () => {},
      appendLine: () => {},
      show: () => {},
      dispose: () => {},
    }),
    showInformationMessage: () => Promise.resolve(undefined),
    showWarningMessage: () => Promise.resolve(undefined),
    showErrorMessage: () => Promise.resolve(undefined),
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
  },
  workspace: {
    workspaceFolders: [{ uri: { fsPath: path.resolve(__dirname, "..", "..") } }],
    getConfiguration: (section) => ({
      get: (key, def) => {
        const fullKey = section ? `${section}.${key}` : key;
        return mockConfigStore.has(fullKey) ? mockConfigStore.get(fullKey) : def;
      },
      update: (key, val) => {
        const fullKey = section ? `${section}.${key}` : key;
        mockConfigStore.set(fullKey, val);
        return Promise.resolve();
      },
    }),
  },
};

// Patch module loader to provide mock vscode
const originalRequire = Module.prototype.require;
Module.prototype.require = function (id) {
  if (id === "vscode") return mockVscode;
  return originalRequire.apply(this, arguments);
};

// Import compiled extension modules
const { GuardianClient } = require("../dist/api/guardianClient");
const { GuardianDashboardPanel } = require("../dist/webview/guardianPanel");

test.describe("Persistent Baselines, Scan History, and Incident Management Suite", () => {
  let originalFetch;
  let interceptedRequests = [];

  test.beforeEach(() => {
    interceptedRequests = [];
    originalFetch = global.fetch;
  });

  test.afterEach(() => {
    global.fetch = originalFetch;
  });

  function setupFetchMock(mockResponses) {
    global.fetch = async (url, options = {}) => {
      const parsedUrl = new URL(url);
      const pathname = parsedUrl.pathname;
      const search = parsedUrl.search;
      const method = (options.method || "GET").toUpperCase();
      let body = null;
      if (options.body) {
        try {
          body = JSON.parse(options.body);
        } catch {
          body = options.body;
        }
      }

      interceptedRequests.push({
        url: url.toString(),
        pathname,
        search,
        method,
        headers: options.headers,
        body,
      });

      // Match handler
      for (const rule of mockResponses) {
        const matchPath = rule.pathname instanceof RegExp ? rule.pathname.test(pathname) : pathname === rule.pathname;
        const matchMethod = !rule.method || rule.method.toUpperCase() === method;
        if (matchPath && matchMethod) {
          const status = rule.status || 200;
          const data = typeof rule.response === "function" ? rule.response({ url, options, body }) : rule.response;
          return {
            ok: status >= 200 && status < 300,
            status,
            statusText: status === 200 ? "OK" : "Error",
            json: async () => data,
            text: async () => JSON.stringify(data),
          };
        }
      }

      return {
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: async () => ({ detail: `No mock for ${method} ${pathname}` }),
      };
    };
  }

  // =========================================================================
  // 1. Project Baselines API
  // =========================================================================
  test.it("Baselines: getProjectBaselines requests correct endpoint and returns list", async () => {
    setupFetchMock([
      {
        pathname: "/api/v1/projects/proj_test_123/baselines",
        method: "GET",
        response: {
          items: [
            {
              id: "bl_001",
              project_id: "proj_test_123",
              version_number: 1,
              version_tag: "v1.0.0",
              is_active: true,
              is_promoted: true,
              contracts: { "/api/users": { get: {} } },
              inventory: { endpoints: [{ route_path: "/api/users" }] },
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          ],
          total: 1,
          active_baseline: { id: "bl_001", version_number: 1, version_tag: "v1.0.0" },
        },
      },
    ]);

    const client = new GuardianClient("http://localhost:8000");
    const result = await client.getProjectBaselines("proj_test_123");

    assert.strictEqual(interceptedRequests.length, 1);
    assert.strictEqual(interceptedRequests[0].pathname, "/api/v1/projects/proj_test_123/baselines");
    assert.strictEqual(result.items.length, 1);
    assert.strictEqual(result.items[0].version_tag, "v1.0.0");
    assert.strictEqual(result.active_baseline.id, "bl_001");
  });

  test.it("Baselines: getActiveProjectBaseline returns the currently promoted baseline", async () => {
    setupFetchMock([
      {
        pathname: "/api/v1/projects/proj_test_123/baselines/active",
        method: "GET",
        response: {
          id: "bl_active_99",
          project_id: "proj_test_123",
          version_number: 2,
          version_tag: "v2.0.0",
          is_active: true,
          is_promoted: true,
        },
      },
    ]);

    const client = new GuardianClient("http://localhost:8000");
    const active = await client.getActiveProjectBaseline("proj_test_123");

    assert.strictEqual(interceptedRequests.length, 1);
    assert.strictEqual(interceptedRequests[0].pathname, "/api/v1/projects/proj_test_123/baselines/active");
    assert.strictEqual(active.id, "bl_active_99");
    assert.strictEqual(active.version_number, 2);
  });

  test.it("Baselines: createProjectBaseline posts snapshot payload without auto-promoting", async () => {
    setupFetchMock([
      {
        pathname: "/api/v1/projects/proj_test_123/baselines",
        method: "POST",
        response: (req) => ({
          id: "bl_new_101",
          project_id: "proj_test_123",
          version_number: 3,
          version_tag: req.body.version_tag,
          description: req.body.description,
          contracts: req.body.contracts,
          inventory: req.body.inventory,
          is_active: false,
          is_promoted: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }),
      },
    ]);

    const client = new GuardianClient("http://localhost:8000");
    const created = await client.createProjectBaseline("proj_test_123", {
      version_tag: "v3.0.0-rc1",
      description: "Pre-release snapshot",
      contracts: { "/api/orders": { post: {} } },
      inventory: { endpoints: [{ route_path: "/api/orders" }] },
    });

    assert.strictEqual(interceptedRequests.length, 1);
    assert.strictEqual(interceptedRequests[0].method, "POST");
    assert.strictEqual(interceptedRequests[0].pathname, "/api/v1/projects/proj_test_123/baselines");
    assert.strictEqual(interceptedRequests[0].body.version_tag, "v3.0.0-rc1");
    assert.strictEqual(created.id, "bl_new_101");
    assert.strictEqual(created.is_active, false);
  });

  test.it("Baselines: createBaseline resolves project ID and dispatches to /api/v1/projects/{id}/baselines without 404", async () => {
    setupFetchMock([
      {
        pathname: "/api/v1/projects/proj_test_123/baselines",
        method: "POST",
        response: (req) => ({
          id: "bl_created_404_fix",
          project_id: "proj_test_123",
          version_number: 1,
          version: 1,
          version_tag: req.body.version_tag,
          description: req.body.description,
          contracts: req.body.contracts,
          inventory: req.body.inventory,
          is_active: false,
          is_promoted: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }),
      },
    ]);

    const client = new GuardianClient("http://localhost:8000");
    const result = await client.createBaseline("proj_test_123", {
      version_tag: "v1.0.0-fixed",
      description: "Baseline via createBaseline method",
      inventory: { endpoints: [{ route_path: "/api/health" }] },
    });

    assert.strictEqual(interceptedRequests.length, 1);
    assert.strictEqual(interceptedRequests[0].method, "POST");
    assert.strictEqual(interceptedRequests[0].pathname, "/api/v1/projects/proj_test_123/baselines");
    assert.strictEqual(interceptedRequests[0].body.version_tag, "v1.0.0-fixed");
    assert.strictEqual(result.id, "bl_created_404_fix");
    assert.strictEqual(result.version_number, 1);
  });

  test.it("Baselines: promoteProjectBaseline marks baseline as active and deactivates others", async () => {
    setupFetchMock([
      {
        pathname: "/api/v1/projects/proj_test_123/baselines/bl_002/promote",
        method: "POST",
        response: {
          id: "bl_002",
          project_id: "proj_test_123",
          version_number: 2,
          version_tag: "v2.0.0",
          is_active: true,
          is_promoted: true,
          promoted_by: "dev_lead",
          notes: "Approved production contract baseline",
        },
      },
    ]);

    const client = new GuardianClient("http://localhost:8000");
    const promoted = await client.promoteProjectBaseline("proj_test_123", "bl_002", "dev_lead");

    assert.strictEqual(interceptedRequests.length, 1);
    assert.strictEqual(interceptedRequests[0].method, "POST");
    assert.strictEqual(interceptedRequests[0].pathname, "/api/v1/projects/proj_test_123/baselines/bl_002/promote");
    assert.match(interceptedRequests[0].search, /promoted_by=dev_lead/);
    assert.strictEqual(promoted.is_active, true);
    assert.strictEqual(promoted.is_promoted, true);
  });

  test.it("Baselines: compareProjectBaselines queries diff between version pairs", async () => {
    setupFetchMock([
      {
        pathname: "/api/v1/projects/proj_test_123/baselines/compare",
        method: "GET",
        response: {
          project_id: "proj_test_123",
          base_version: 1,
          target_version: 2,
          base_id: "bl_001",
          target_id: "bl_002",
          endpoints_added: [{ method: "POST", path: "/api/v2/payments" }],
          endpoints_removed: [],
          endpoints_modified: [{ method: "GET", path: "/api/users", changes: ["response_field_removed"] }],
          contract_diffs: {},
          summary: { added_count: 1, removed_count: 0, modified_count: 1 },
        },
      },
    ]);

    const client = new GuardianClient("http://localhost:8000");
    const diff = await client.compareProjectBaselines("proj_test_123", "1", "2");

    assert.strictEqual(interceptedRequests.length, 1);
    assert.strictEqual(interceptedRequests[0].pathname, "/api/v1/projects/proj_test_123/baselines/compare");
    assert.match(interceptedRequests[0].search, /base=1/);
    assert.match(interceptedRequests[0].search, /target=2/);
    assert.strictEqual(diff.endpoints_added.length, 1);
    assert.strictEqual(diff.endpoints_modified.length, 1);
  });

  // =========================================================================
  // 2. Scan History & Idempotent Ingestion
  // =========================================================================
  test.it("Scan Ingestion: ingestScanRun posts scan execution with client_run_id idempotently", async () => {
    setupFetchMock([
      {
        pathname: "/api/v1/projects/proj_test_123/scans/ingest",
        method: "POST",
        response: {
          id: "scan_run_500",
          project_id: "proj_test_123",
          scan_type: "codebase",
          detection_mode: "hybrid",
          capabilities_executed: ["codebase_scanner"],
          status: "succeeded",
          duration_seconds: 4.2,
          client_run_id: "client_run_abc_1",
          summary_counts: { discovered_endpoints: 12, discrepancies: 1, findings_total: 1 },
          is_local: true,
          sync_status: "synced",
          created_incidents_count: 1,
          reopened_incidents_count: 0,
        },
      },
    ]);

    const client = new GuardianClient("http://localhost:8000");
    const res = await client.ingestScanRun("proj_test_123", {
      client_run_id: "client_run_abc_1",
      scan_type: "codebase",
      detection_mode: "hybrid",
      capabilities_executed: ["codebase_scanner"],
      duration_seconds: 4.2,
      summary_counts: { discovered_endpoints: 12, discrepancies: 1, findings_total: 1 },
      findings: [
        {
          title: "Missing auth on /api/internal/stats",
          severity: "high",
          fingerprint: "undoc:GET:/api/internal/stats",
          category: "undocumented_api",
          provenance: "codebase_scanner",
          confidence: 0.95,
          evidence: { path: "/api/internal/stats" },
        },
      ],
      status: "succeeded",
    });

    assert.strictEqual(interceptedRequests.length, 1);
    assert.strictEqual(interceptedRequests[0].pathname, "/api/v1/projects/proj_test_123/scans/ingest");
    assert.strictEqual(interceptedRequests[0].method, "POST");
    assert.strictEqual(interceptedRequests[0].body.client_run_id, "client_run_abc_1");
    assert.strictEqual(interceptedRequests[0].body.detection_mode, "hybrid");
    assert.strictEqual(res.client_run_id, "client_run_abc_1");
    assert.strictEqual(res.created_incidents_count, 1);
  });

  test.it("Scan Ingestion: listProjectScans queries historical runs", async () => {
    setupFetchMock([
      {
        pathname: "/api/v1/projects/proj_test_123/scans",
        method: "GET",
        response: [
          {
            id: "scan_run_1",
            project_id: "proj_test_123",
            scan_type: "codebase",
            detection_mode: "algorithmic",
            status: "succeeded",
            duration_seconds: 1.8,
            summary_counts: { findings_total: 2 },
            created_at: new Date().toISOString(),
          },
          {
            id: "scan_run_2",
            project_id: "proj_test_123",
            scan_type: "contract_drift",
            detection_mode: "ai",
            status: "succeeded",
            duration_seconds: 3.5,
            summary_counts: { findings_total: 1 },
            created_at: new Date().toISOString(),
          },
        ],
      },
    ]);

    const client = new GuardianClient("http://localhost:8000");
    const scans = await client.listProjectScans("proj_test_123", 20);

    assert.strictEqual(interceptedRequests.length, 1);
    assert.strictEqual(interceptedRequests[0].pathname, "/api/v1/projects/proj_test_123/scans");
    assert.match(interceptedRequests[0].search, /limit=20/);
    assert.strictEqual(scans.length, 2);
    assert.strictEqual(scans[0].detection_mode, "algorithmic");
    assert.strictEqual(scans[1].detection_mode, "ai");
  });

  // =========================================================================
  // 3. Incident Lifecycle Transitions & Timeline Events
  // =========================================================================
  test.it("Incident Lifecycle: acknowledgeIncident transitions status to acknowledged", async () => {
    setupFetchMock([
      {
        pathname: "/api/v1/incidents/inc_777/acknowledge",
        method: "POST",
        response: {
          id: "inc_777",
          title: "Breaking response schema",
          status: "acknowledged",
          acknowledged_at: new Date().toISOString(),
          review_notes: "Triaged for next sprint",
        },
      },
    ]);

    const client = new GuardianClient("http://localhost:8000");
    const inc = await client.acknowledgeIncident("inc_777", "Triaged for next sprint");

    assert.strictEqual(interceptedRequests.length, 1);
    assert.strictEqual(interceptedRequests[0].pathname, "/api/v1/incidents/inc_777/acknowledge");
    assert.strictEqual(interceptedRequests[0].method, "POST");
    assert.strictEqual(interceptedRequests[0].body.notes, "Triaged for next sprint");
    assert.strictEqual(inc.status, "acknowledged");
  });

  test.it("Incident Lifecycle: resolveIncident transitions status to resolved", async () => {
    setupFetchMock([
      {
        pathname: "/api/v1/incidents/inc_777/resolve",
        method: "POST",
        response: {
          id: "inc_777",
          title: "Breaking response schema",
          status: "resolved",
          resolved_at: new Date().toISOString(),
          resolution_notes: "Fixed client adapters in PR #42",
        },
      },
    ]);

    const client = new GuardianClient("http://localhost:8000");
    const inc = await client.resolveIncident("inc_777", "Fixed client adapters in PR #42");

    assert.strictEqual(interceptedRequests.length, 1);
    assert.strictEqual(interceptedRequests[0].pathname, "/api/v1/incidents/inc_777/resolve");
    assert.strictEqual(interceptedRequests[0].method, "POST");
    assert.strictEqual(interceptedRequests[0].body.notes, "Fixed client adapters in PR #42");
    assert.strictEqual(inc.status, "resolved");
  });

  test.it("Incident Lifecycle: reopenIncident transitions status to reopened", async () => {
    setupFetchMock([
      {
        pathname: "/api/v1/incidents/inc_777/reopen",
        method: "POST",
        response: {
          id: "inc_777",
          title: "Breaking response schema",
          status: "reopened",
          reopened_at: new Date().toISOString(),
          review_notes: "Regression detected in staging",
        },
      },
    ]);

    const client = new GuardianClient("http://localhost:8000");
    const inc = await client.reopenIncident("inc_777", "Regression detected in staging");

    assert.strictEqual(interceptedRequests.length, 1);
    assert.strictEqual(interceptedRequests[0].pathname, "/api/v1/incidents/inc_777/reopen");
    assert.strictEqual(interceptedRequests[0].method, "POST");
    assert.strictEqual(inc.status, "reopened");
  });

  test.it("Incident Lifecycle: getIncidentEvents returns audit trail timeline", async () => {
    setupFetchMock([
      {
        pathname: "/api/v1/incidents/inc_777/events",
        method: "GET",
        response: [
          {
            id: "ev_1",
            incident_id: "inc_777",
            event_type: "detected",
            to_status: "open",
            message: "First detected during codebase scan",
            created_at: new Date().toISOString(),
          },
          {
            id: "ev_2",
            incident_id: "inc_777",
            event_type: "acknowledged",
            from_status: "open",
            to_status: "acknowledged",
            message: "Triaged by engineer",
            created_at: new Date().toISOString(),
          },
        ],
      },
    ]);

    const client = new GuardianClient("http://localhost:8000");
    const events = await client.getIncidentEvents("inc_777");

    assert.strictEqual(interceptedRequests.length, 1);
    assert.strictEqual(interceptedRequests[0].pathname, "/api/v1/incidents/inc_777/events");
    assert.strictEqual(events.length, 2);
    assert.strictEqual(events[0].event_type, "detected");
    assert.strictEqual(events[1].to_status, "acknowledged");
  });

  test.it("Incident Lifecycle: getChanges maps backend incident fields including occurrence_count and provenance", async () => {
    setupFetchMock([
      {
        pathname: "/api/v1/projects",
        method: "GET",
        response: [{ id: "proj_test_123", name: "HackWave Demo Project" }],
      },
      {
        pathname: "/api/v1/projects/proj_test_123/incidents",
        method: "GET",
        response: [
          {
            id: "inc_101",
            project_id: "proj_test_123",
            dependency_id: "dep_users",
            title: "Removed required field 'company_id'",
            description: "API field company_id was dropped in upstream v2.1",
            change_type: "field_removed",
            severity: "high",
            status: "reopened",
            provenance: "external_api_drift",
            confidence: 0.98,
            fingerprint: "drift:rule_01:GET:/users",
            occurrence_count: 3,
            recommended_action: "Update local serializer to make company_id optional",
            review_notes: "Previously resolved; recurrence observed",
            reopened_at: new Date().toISOString(),
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ],
      },
    ]);

    const client = new GuardianClient("http://localhost:8000");
    const changes = await client.getChanges("proj_test_123");

    assert.strictEqual(changes.length, 1);
    assert.strictEqual(changes[0].id, "inc_101");
    assert.strictEqual(changes[0].severity, "high");
    assert.strictEqual(changes[0].status, "reopened");
    assert.strictEqual(changes[0].occurrence_count, 3);
    assert.strictEqual(changes[0].provenance, "external_api_drift");
    assert.strictEqual(changes[0].confidence, 0.98);
    assert.strictEqual(changes[0].fingerprint, "drift:rule_01:GET:/users");
    assert.strictEqual(changes[0].review_notes, "Previously resolved; recurrence observed");
  });

  // =========================================================================
  // 4. Guardian Dashboard Panel UI Elements
  // =========================================================================
  test.it("Dashboard UI: Renders Persistent Baselines, Scan History, and Incident Filters", async () => {
    setupFetchMock([
      {
        pathname: "/api/v1/projects",
        method: "GET",
        response: [{ id: "proj_test_123", name: "HackWave Demo Project" }],
      },
      {
        pathname: "/api/v1/projects/proj_test_123/dependencies",
        method: "GET",
        response: [],
      },
      {
        pathname: "/api/v1/projects/proj_test_123/incidents",
        method: "GET",
        response: [
          {
            id: "inc_001",
            project_id: "proj_test_123",
            dependency_id: "dep_1",
            title: "Breaking schema change",
            severity: "high",
            status: "open",
            provenance: "external_api_drift",
            occurrence_count: 2,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ],
      },
      {
        pathname: "/api/v1/projects/proj_test_123/baselines",
        method: "GET",
        response: {
          items: [
            {
              id: "bl_001",
              project_id: "proj_test_123",
              version_number: 1,
              version_tag: "v1.0.0",
              is_active: true,
              is_promoted: true,
              contracts: {},
              inventory: { endpoints: [] },
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          ],
          total: 1,
          active_baseline: { id: "bl_001", version_number: 1, version_tag: "v1.0.0" },
        },
      },
      {
        pathname: "/api/v1/projects/proj_test_123/scans",
        method: "GET",
        response: [
          {
            id: "scan_001",
            project_id: "proj_test_123",
            scan_type: "codebase",
            detection_mode: "hybrid",
            status: "succeeded",
            duration_seconds: 2.4,
            summary_counts: { findings_total: 1 },
            created_at: new Date().toISOString(),
          },
        ],
      },
      {
        pathname: "/api/v1/incidents/inc_001/repair-proposals",
        method: "GET",
        response: [],
      },
    ]);

    const client = new GuardianClient("http://localhost:8000");
    GuardianDashboardPanel.createOrShow(mockVscode.Uri.file("/ext"), client, undefined);
    assert.ok(GuardianDashboardPanel.currentPanel, "Panel was created");

    await GuardianDashboardPanel.currentPanel.refresh();

    const html = GuardianDashboardPanel.currentPanel._panel.webview.html;
    assert.ok(html.length > 0, "HTML is rendered");

    // Metrics for Active Baseline and Scan History
    assert.match(html, /id="metricBaseline"/, "Active baseline metric is present");
    assert.match(html, /id="metricScans"/, "Scan count metric is present");

    // Navigation Tabs for Baselines and Scans
    assert.match(html, /id="tabBaselines"/, "Baselines tab is present");
    assert.match(html, /id="tabScans"/, "Scan history tab is present");

    // Incident Lifecycle Status Filter Buttons
    assert.match(html, /id="filterBtnAll"/, "Filter pill for All is present");
    assert.match(html, /id="filterBtnOpen"/, "Filter pill for Open is present");
    assert.match(html, /id="filterBtnAck"/, "Filter pill for Acknowledged is present");
    assert.match(html, /id="filterBtnRes"/, "Filter pill for Resolved is present");
    assert.match(html, /id="filterBtnReopen"/, "Filter pill for Reopened is present");

    // Incident Actions in Studio Templates
    assert.match(html, /onclick="ackIncident\(/, "Acknowledge action is present");
    assert.match(html, /onclick="resolveIncident\(/, "Resolve action is present");
    assert.match(html, /onclick="reopenIncident\(/, "Reopen action is present");
    assert.match(html, /Audit Timeline &amp; Events/, "Incident timeline section is present");

    // Baseline Actions
    assert.match(html, /onclick="promptCreateBaseline\(\)"/, "Create baseline snapshot button is present");
    assert.match(html, /id="baselineDiffCard"/, "Baseline diff drawer is present");
    assert.match(html, /id="baselinesTableContainer"/, "Baselines table container is present");
    assert.match(html, /id="scansTableContainer"/, "Scans table container is present");

    GuardianDashboardPanel.currentPanel.dispose();
  });
});
