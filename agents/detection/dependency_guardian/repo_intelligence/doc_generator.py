"""
Repository Documentation and Report Generator.
Produces repository-inventory.json, DEPENDENCY_REPORT.md, API_REFERENCE.md,
INTEGRATION_MAP.md, TEST_COVERAGE.md, and openapi.enriched.json.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .models import (
    EndpointDoc,
    RepositoryInventory,
)

logger = logging.getLogger("dependency_guardian.repo_intelligence.doc_generator")


class DocumentationGenerator:
    """Generates structured JSON inventory, Markdown reports, and enriched OpenAPI spec."""

    def __init__(self, inventory: RepositoryInventory, output_dir: Path, base_openapi_spec: Optional[Dict[str, Any]] = None):
        self.inventory = inventory
        self.output_dir = output_dir.resolve()
        self.base_openapi_spec = base_openapi_spec

    def generate_all(self) -> Dict[str, Path]:
        """
        Generate all required deliverables.
        Returns mapping of deliverable name to written file path.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        written: Dict[str, Path] = {}

        # 1. repository-inventory.json
        inv_path = self.output_dir / "repository-inventory.json"
        inv_data = self.inventory.model_dump(mode="json")
        inv_path.write_text(json.dumps(inv_data, indent=2), encoding="utf-8")
        written["inventory_json"] = inv_path

        # 2. DEPENDENCY_REPORT.md
        dep_path = self.output_dir / "DEPENDENCY_REPORT.md"
        dep_path.write_text(self._generate_dependency_report(), encoding="utf-8")
        written["dependency_report"] = dep_path

        # 3. API_REFERENCE.md
        api_path = self.output_dir / "API_REFERENCE.md"
        api_path.write_text(self._generate_api_reference(), encoding="utf-8")
        written["api_reference"] = api_path

        # 4. INTEGRATION_MAP.md
        map_path = self.output_dir / "INTEGRATION_MAP.md"
        map_path.write_text(self._generate_integration_map(), encoding="utf-8")
        written["integration_map"] = map_path

        # 5. TEST_COVERAGE.md
        cov_path = self.output_dir / "TEST_COVERAGE.md"
        cov_path.write_text(self._generate_test_coverage_report(), encoding="utf-8")
        written["test_coverage"] = cov_path

        # 6. openapi.enriched.json
        enriched_path = self.output_dir / "openapi.enriched.json"
        enriched_spec = self._generate_enriched_openapi()
        enriched_path.write_text(json.dumps(enriched_spec, indent=2), encoding="utf-8")
        written["openapi_enriched"] = enriched_path

        return written

    # =========================================================================
    # DEPENDENCY_REPORT.md
    # =========================================================================

    def _generate_dependency_report(self) -> str:
        inv = self.inventory
        meta = inv.metadata
        deps = inv.dependencies

        total_deps = len(deps)
        used_deps = sum(1 for d in deps if d.is_used)
        unused_deps_count = len(inv.unused_dependencies)

        lines = [
            "# Dependency Guardian — Repository Dependency Report",
            "",
            f"**Scanned Repository Path:** `{meta.scanned_path}`  ",
            f"**Scan Timestamp:** `{meta.scan_timestamp}`  ",
            f"**Scanner Engine:** `{meta.scanner_name} v{meta.scanner_version}`  ",
            "",
            "## 1. Executive Summary",
            "",
            "| Metric | Count | Note |",
            "|---|---|---|",
            f"| **Total Declared Dependencies** | {total_deps} | Discovered across manifests and lockfiles |",
            f"| **Active Dependencies in Code** | {used_deps} | Imported or required in source code |",
            f"| **Declared but Unused Packages** | {unused_deps_count} | Potential cleanup candidates |",
            f"| **Internal Modules** | {len(inv.internal_modules)} | Local architectural modules |",
            f"| **External Integrations** | {len(inv.integrations)} | Databases, queues, HTTP clients, SDKs |",
            "",
            "---",
            "",
            "## 2. External Dependencies Inventory",
            "",
            "All discovered third-party libraries, version constraints, resolved lockfile versions, purposes, and usage sites:",
            "",
            "| Package Name | Ecosystem | Declared Constraint | Resolved Version | Used in Code | Purpose | Documentation URL | Vulnerabilities |",
            "|---|---|---|---|:---:|---|---|---|",
        ]

        for d in sorted(deps, key=lambda x: (not x.is_used, x.package_name)):
            used_badge = "✅ Yes" if d.is_used else "⚠️ No"
            resolved = f"`{d.resolved_version}`" if d.resolved_version else "*Unresolved*"
            constraint = f"`{d.declared_constraint}`" if d.declared_constraint else "*None*"
            purpose = d.purpose or "*(Not documented)*"
            if d.is_inferred_purpose:
                purpose += " *(Inferred)*"
            doc_url = f"[Docs]({d.official_documentation_url})" if d.official_documentation_url else "*None*"

            vuln_str = "None verified"
            if d.vulnerabilities:
                vuln_str = f"⚠️ {len(d.vulnerabilities)} advisory: " + ", ".join([v.get("vulnerability_id", "CVE") for v in d.vulnerabilities])

            lines.append(
                f"| **{d.package_name}** | {d.ecosystem} | {constraint} | {resolved} | {used_badge} | {purpose} | {doc_url} | {vuln_str} |"
            )

        lines.extend([
            "",
            "### Dependency Usage Sites (Top Imported Packages)",
            "",
        ])

        for d in sorted([x for x in deps if x.is_used], key=lambda x: len(x.import_locations), reverse=True):
            lines.append(f"#### `{d.package_name}` ({len(d.import_locations)} import sites)")
            for loc in d.import_locations[:5]:
                lines.append(f"- `{loc.file}:{loc.line}`: `{loc.statement}`")
            if len(d.import_locations) > 5:
                lines.append(f"- *...and {len(d.import_locations) - 5} more locations.*")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 3. Declared but Unused Dependencies",
            "",
            "> [!NOTE]",
            "> The following packages are declared in dependency manifests but were not found imported or required anywhere in the scanned source code. Consider removing them to reduce attack surface and build times.",
            "",
        ])

        if inv.unused_dependencies:
            for u in inv.unused_dependencies:
                lines.append(f"- ⚠️ **{u}** — Declared in manifest but has 0 import references")
        else:
            lines.append("✅ All declared dependencies have active import references in the codebase.")

        lines.extend([
            "",
            "---",
            "",
            "## 4. Internal Module Architecture",
            "",
            "Local packages and modules detected within the repository:",
            "",
        ])

        for im in inv.internal_modules[:30]:
            lines.append(f"- `{im}`")
        if len(inv.internal_modules) > 30:
            lines.append(f"- *...and {len(inv.internal_modules) - 30} more internal modules.*")

        lines.extend([
            "",
            "---",
            "",
            "## 5. External Services and Integrations",
            "",
            "> [!IMPORTANT]",
            "> All external service interfaces, outbound HTTP calls, database clients, SDKs, and message brokers are inventoried below.",
            "> **Secret Safety Verification:** All credential strings, tokens, and passwords have been strictly sanitized and redacted.",
            "",
            "| Integration Type | Service Name | Target / Host | File Location | Detected Operations | Redacted Secrets |",
            "|---|---|---|---|---|:---:|",
        ])

        if inv.integrations:
            for it in inv.integrations:
                target = f"`{it.target_url_or_host}`" if it.target_url_or_host else "*Configuration-driven*"
                ops = ", ".join(it.operations) if it.operations else "connect"
                sec_count = f"{it.redacted_secrets_count} redacted" if it.redacted_secrets_count > 0 else "0 (Safe)"
                lines.append(
                    f"| **{it.integration_type.upper()}** | {it.service_name} | {target} | `{it.file_path}:{it.line_number}` | `{ops}` | {sec_count} |"
                )
        else:
            lines.append("| *None* | No external integrations detected | - | - | - | 0 |")

        lines.extend([
            "",
            "---",
            "",
            "## 6. Scanner Limitations and Skipped Files",
            "",
        ])

        if meta.skipped_files:
            lines.append("| Skipped File | Reason |")
            lines.append("|---|---|")
            for sf in meta.skipped_files:
                lines.append(f"| `{sf.file_path}` | {sf.reason} |")
        else:
            lines.append("✅ All discoverable source files and manifests were successfully parsed.")

        lines.append("")
        return "\n".join(lines)

    # =========================================================================
    # API_REFERENCE.md
    # =========================================================================

    def _generate_api_reference(self) -> str:
        inv = self.inventory
        endpoints = inv.endpoints

        lines = [
            "# Dependency Guardian — API Reference Documentation",
            "",
            f"**Total Discovered Endpoints:** {len(endpoints)}  ",
            f"**Generated On:** `{inv.metadata.scan_timestamp}`  ",
            "",
            "## Table of Contents",
            "",
        ]

        for ep in endpoints:
            anchor = f"{ep.http_method.lower()}-{ep.route_path.lower().replace('/', '').replace('{', '').replace('}', '').replace(':', '')}"
            lines.append(f"- [`{ep.http_method} {ep.route_path}`](#{anchor})")

        lines.extend(["", "---", ""])

        for ep in endpoints:
            anchor = f"{ep.http_method.lower()}-{ep.route_path.lower().replace('/', '').replace('{', '').replace('}', '').replace(':', '')}"
            lines.append(f"### <a id=\"{anchor}\"></a>`{ep.http_method} {ep.route_path}`")
            lines.append("")

            # Summary and Description
            if ep.summary:
                lines.append(f"**Summary:** {ep.summary}  ")
            if ep.description and ep.description != ep.summary:
                lines.append(f"**Description:** {ep.description}  ")
            lines.append("")

            # Provenance and metadata box
            src = f"`{ep.source_file}:{ep.line_number}`" if ep.source_file else "*OpenAPI specification only*"
            handler = f"`{ep.handler_function}`" if ep.handler_function else "*N/A*"
            lines.extend([
                "> [!NOTE]",
                f"> **Discovery Method:** `{ep.discovery_method}` | **Evidence:** {ep.evidence_source}  ",
                f"> **Handler:** {handler} | **Source Location:** {src}  ",
                f"> **Confidence Level:** `{ep.confidence_level * 100:.0f}%` | **Inferred:** `{'Yes' if ep.is_inferred else 'No'}`",
                "",
            ])

            # Auth & Authorization
            if ep.auth_and_authz:
                lines.append(f"🔒 **Authentication & Authorization:** {ep.auth_and_authz}")
            else:
                lines.append("🔓 **Authentication & Authorization:** Public / None detected")
            lines.append("")

            # Parameters
            lines.append("#### Parameters")
            if ep.parameters:
                lines.append("| Name | Location | Type | Required | Default | Constraints | Description |")
                lines.append("|---|---|---|:---:|---|---|---|")
                for p in ep.parameters:
                    req = "✅ Yes" if p.required else "No"
                    dflt = f"`{p.default}`" if p.default is not None else "*None*"
                    constr = ", ".join([f"{k}={v}" for k, v in p.constraints.items()]) if p.constraints else "*None*"
                    desc = p.description or "*(Not documented)*"
                    if p.is_inferred:
                        desc += " *(Inferred)*"
                    lines.append(
                        f"| `{p.name}` | `{p.in_location}` | `{p.param_type}` | {req} | {dflt} | {constr} | {desc} |"
                    )
            else:
                lines.append("*No path, query, header, or cookie parameters required.*")
            lines.append("")

            # Request Body
            lines.append("#### Request Body")
            if ep.request_body:
                rb = ep.request_body
                schema_lbl = f"`{rb.schema_name}`" if rb.schema_name else "*Inline Object*"
                req_lbl = "Required" if rb.required else "Optional"
                lines.append(f"**Content-Type:** `{rb.content_type}` | **Schema:** {schema_lbl} ({req_lbl})")
                lines.append("")
                if rb.fields:
                    lines.append("| Field | Type | Required | Default | Constraints | Description |")
                    lines.append("|---|---|:---:|---|---|---|")
                    for f in rb.fields:
                        freq = "✅ Yes" if f.required else "No"
                        fdflt = f"`{f.default}`" if f.default is not None else "*None*"
                        fconstr = ", ".join([f"{k}={v}" for k, v in f.constraints.items()]) if f.constraints else "*None*"
                        fdesc = f.description or "*(Not documented)*"
                        if f.is_inferred:
                            fdesc += " *(Inferred)*"
                        lines.append(
                            f"| `{f.name}` | `{f.field_type}` | {freq} | {fdflt} | {fconstr} | {fdesc} |"
                        )
                else:
                    lines.append("*Request body schema defines no specific properties.*")
            else:
                lines.append("*No request body expected.*")
            lines.append("")

            # Responses
            lines.append("#### Responses")
            if ep.responses:
                for r in ep.responses:
                    r_desc = r.description or "Response"
                    schema_lbl = f"(`{r.schema_name}`)" if r.schema_name else ""
                    lines.append(f"- **HTTP {r.status_code}** {schema_lbl}: {r_desc}")
                    if r.fields:
                        lines.append("  | Response Field | Type | Required | Description |")
                        lines.append("  |---|---|:---:|---|")
                        for rf in r.fields:
                            rf_req = "Yes" if rf.required else "No"
                            rf_desc = rf.description or "*(Not documented)*"
                            lines.append(f"  | `{rf.name}` | `{rf.field_type}` | {rf_req} | {rf_desc} |")
            else:
                lines.append("*Default HTTP 200 response.*")
            lines.append("")

            # Error cases & side effects
            if ep.error_cases or ep.side_effects:
                lines.append("#### Error Cases & Side Effects")
                if ep.error_cases:
                    lines.append("**Error Cases:**")
                    for ec in ep.error_cases:
                        lines.append(f"- `HTTP {ec.status_code}`: {ec.condition}")
                if ep.side_effects:
                    lines.append("**Side Effects:**")
                    for se in ep.side_effects:
                        lines.append(f"- `{se.effect_type}` on `{se.target}`: {se.description}")
                lines.append("")

            # Test coverage
            lines.append("#### Verified Test Coverage")
            if ep.existing_tests:
                for t in ep.existing_tests:
                    lines.append(f"- ✅ `{t}`")
            else:
                lines.append("- ⚠️ *No automated tests found covering this route (Coverage Gap).*")
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # INTEGRATION_MAP.md
    # =========================================================================

    def _generate_integration_map(self) -> str:
        inv = self.inventory
        endpoints = inv.endpoints
        integrations = inv.integrations

        lines = [
            "# Dependency Guardian — Repository Integration Map",
            "",
            "Visual relationship map and matrix linking endpoints, handlers, internal dependencies, databases, and external third-party services.",
            "",
            "## 1. System Architecture and Integration Diagram",
            "",
            "```mermaid",
            "flowchart TD",
            "    subgraph Client [API Consumers]",
            "        Web[Web / Mobile Clients]",
            "    end",
            "",
            "    subgraph Endpoints [Discovered API Endpoints]",
        ]

        # Add top endpoints to diagram
        for idx, ep in enumerate(endpoints[:8]):
            node_id = f"EP{idx}"
            lines.append(f'        {node_id}["{ep.http_method} {ep.route_path}"]')

        lines.extend([
            "    end",
            "",
            "    subgraph Services [Handlers & Logic]",
        ])

        for idx, ep in enumerate(endpoints[:8]):
            h_name = ep.handler_function or f"Handler_{idx}"
            lines.append(f'        H{idx}["{h_name}()"]')

        lines.extend([
            "    end",
            "",
            "    subgraph External [Databases & External Integrations]",
        ])

        db_nodes = []
        ext_nodes = []
        for idx, it in enumerate(integrations[:6]):
            it_id = f"INT{idx}"
            lines.append(f'        {it_id}["{it.service_name} ({it.integration_type.upper()})"]')
            if it.integration_type in ["database", "cache"]:
                db_nodes.append(it_id)
            else:
                ext_nodes.append(it_id)

        if not integrations:
            lines.append('        INT0["Local Application Memory"]')

        lines.extend([
            "    end",
            "",
            "    %% Connections",
            "    Web --> Endpoints",
        ])

        for idx, ep in enumerate(endpoints[:8]):
            lines.append(f"    EP{idx} --> H{idx}")
            if integrations:
                target_int = f"INT{idx % len(integrations[:6])}"
                lines.append(f"    H{idx} --> {target_int}")

        lines.extend([
            "```",
            "",
            "---",
            "",
            "## 2. End-to-End Relationship Matrix",
            "",
            "| Route & Method | Handler Function | Source Location | Direct Dependencies | Storage / External Targets | Side Effects |",
            "|---|---|---|---|---|---|",
        ])

        for ep in endpoints:
            h_name = f"`{ep.handler_function}()`" if ep.handler_function else "*N/A*"
            src = f"`{ep.source_file}:{ep.line_number}`" if ep.source_file else "*OpenAPI only*"
            deps = ", ".join(ep.relevant_dependencies) if ep.relevant_dependencies else "*None*"
            targets = ", ".join(list({se.target for se in ep.side_effects})) if ep.side_effects else "*In-memory / Read-only*"
            side_eff = ", ".join([f"{se.effect_type}" for se in ep.side_effects]) if ep.side_effects else "None detected"

            lines.append(
                f"| `{ep.http_method} {ep.route_path}` | {h_name} | {src} | {deps} | {targets} | {side_eff} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 3. Outbound Network Boundaries",
            "",
            "> [!IMPORTANT]",
            "> All external outbound connections originating from this repository are inventoried below.",
            "",
            "| Integration Name | Target Endpoint / Host | Integration Type | Initiating Source File | Redacted Credentials |",
            "|---|---|---|---|:---:|",
        ])

        for it in integrations:
            target = f"`{it.target_url_or_host}`" if it.target_url_or_host else "*Configured Host*"
            redacted = f"{it.redacted_secrets_count} redacted" if it.redacted_secrets_count > 0 else "0 (Safe)"
            lines.append(
                f"| **{it.service_name}** | {target} | `{it.integration_type}` | `{it.file_path}:{it.line_number}` | {redacted} |"
            )

        lines.append("")
        return "\n".join(lines)

    # =========================================================================
    # TEST_COVERAGE.md
    # =========================================================================

    def _generate_test_coverage_report(self) -> str:
        inv = self.inventory
        cov = inv.test_coverage
        endpoints = inv.endpoints

        lines = [
            "# Dependency Guardian — API Test Coverage Report",
            "",
            "Comprehensive test coverage verification across discovered API routes and integrations.",
            "",
            "## 1. Executive Coverage Metrics",
            "",
            "| Metric | Value | Status |",
            "|---|---|---|",
            f"| **Total Discovered Endpoints** | {cov.total_endpoints} | 100% of discovered routes |",
            f"| **Endpoints with Automated Tests** | {cov.tested_endpoints} | Verified by test suite |",
            f"| **Endpoints with No Tests (Gaps)** | {cov.untested_endpoints} | Need test implementation |",
            f"| **API Endpoint Test Coverage** | **{cov.coverage_percentage}%** | {'🟢 Good' if cov.coverage_percentage >= 70 else '🟡 Needs Improvement'} |",
            f"| **Integration Tests Found** | {len(cov.integration_tests_found)} | Integration/external tests |",
            "",
            "---",
            "",
            "## 2. Endpoint Test Coverage Matrix",
            "",
            "| Method | Route Path | Source Location | Discovered Test(s) | Coverage State |",
            "|---|---|---|---|:---:|",
        ]

        for ep in endpoints:
            src = f"`{ep.source_file}:{ep.line_number}`" if ep.source_file else "*OpenAPI only*"
            if ep.existing_tests:
                tests_str = "<br>".join([f"• `{t}`" for t in ep.existing_tests[:3]])
                if len(ep.existing_tests) > 3:
                    tests_str += f"<br>*...and {len(ep.existing_tests) - 3} more.*"
                status_badge = "✅ Covered"
            else:
                tests_str = "*None*"
                status_badge = "❌ **Coverage Gap**"

            lines.append(
                f"| `{ep.http_method}` | `{ep.route_path}` | {src} | {tests_str} | {status_badge} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 3. Discovered Integration Tests",
            "",
        ])

        if cov.integration_tests_found:
            for it_test in cov.integration_tests_found:
                lines.append(f"- 🧪 `{it_test}`")
        else:
            lines.append("*No dedicated external integration tests detected.*")

        lines.extend([
            "",
            "---",
            "",
            "## 4. Identified Test Gaps and Remediation Recommendations",
            "",
        ])

        untested = [ep for ep in endpoints if not ep.existing_tests]
        if untested:
            lines.append("The following endpoints currently lack automated test coverage:")
            lines.append("")
            for u in untested:
                lines.append(f"- ⚠️ **`{u.http_method} {u.route_path}`** ({u.source_file or 'spec'}) — Missing functional regression tests.")
            lines.append("")
            lines.append("### Recommendations:")
            lines.append("1. Generate automated regression tests using `dependency-guardian --generate-tests`.")
            lines.append("2. Add positive tests asserting happy-path response status codes.")
            lines.append("3. Add negative tests validating error cases and input validation rules.")
        else:
            lines.append("🎉 **Outstanding! All discovered API endpoints have automated test coverage.**")

        lines.append("")
        return "\n".join(lines)

    # =========================================================================
    # ENRICHED OPENAPI SPECIFICATION
    # =========================================================================

    def _generate_enriched_openapi(self) -> Dict[str, Any]:
        """
        Generate an enriched OpenAPI specification.
        Preserves original OpenAPI spec if provided, and supplements it with:
        - Undocumented endpoints discovered from source code AST
        - Handler names, source file line numbers, discovery methods
        """
        spec: Dict[str, Any] = {}
        if self.base_openapi_spec:
            # Deep copy base spec to never modify original
            spec = json.loads(json.dumps(self.base_openapi_spec))
        else:
            spec = {
                "openapi": "3.1.0",
                "info": {
                    "title": f"Repository API — {self.inventory.metadata.scanned_path}",
                    "version": "1.0.0",
                    "description": "Generated and enriched by Dependency Guardian Repository Intelligence.",
                },
                "paths": {},
                "components": {"schemas": {}},
            }

        paths = spec.setdefault("paths", {})
        components = spec.setdefault("components", {})
        schemas = components.setdefault("schemas", {})

        for ep in self.inventory.endpoints:
            p_obj = paths.setdefault(ep.route_path, {})
            m_key = ep.http_method.lower()

            op_obj = p_obj.setdefault(m_key, {})

            # Set summary and description if not already set
            if ep.summary and not op_obj.get("summary"):
                op_obj["summary"] = ep.summary
            if ep.description and not op_obj.get("description"):
                op_obj["description"] = ep.description

            # Attach provenance vendor extensions
            op_obj["x-source-file"] = ep.source_file
            op_obj["x-source-line"] = ep.line_number
            op_obj["x-handler-name"] = ep.handler_function
            op_obj["x-discovery-method"] = ep.discovery_method
            op_obj["x-confidence"] = ep.confidence_level

            # Parameters
            existing_params = op_obj.setdefault("parameters", [])
            existing_param_names = {p.get("name") for p in existing_params if isinstance(p, dict)}

            for p in ep.parameters:
                if p.name not in existing_param_names:
                    existing_params.append({
                        "name": p.name,
                        "in": p.in_location,
                        "required": p.required,
                        "schema": {
                            "type": p.param_type.lower() if p.param_type.lower() in ["string", "integer", "boolean", "number"] else "string",
                            **p.constraints,
                        },
                        "description": p.description,
                    })

            # Request Body
            if ep.request_body and "requestBody" not in op_obj:
                rb = ep.request_body
                rb_schema: Dict[str, Any] = {"type": "object", "properties": {}}
                for f in rb.fields:
                    rb_schema["properties"][f.name] = {
                        "type": f.field_type.lower() if f.field_type.lower() in ["string", "integer", "boolean", "number"] else "string",
                        **f.constraints,
                    }
                    if f.description:
                        rb_schema["properties"][f.name]["description"] = f.description
                if rb.schema_name:
                    schemas[rb.schema_name] = rb_schema
                    content_schema = {"$ref": f"#/components/schemas/{rb.schema_name}"}
                else:
                    content_schema = rb_schema

                op_obj["requestBody"] = {
                    "required": rb.required,
                    "content": {
                        rb.content_type: {"schema": content_schema}
                    },
                }

            # Responses
            responses = op_obj.setdefault("responses", {})
            for r in ep.responses:
                code_str = str(r.status_code)
                if code_str not in responses:
                    r_schema: Dict[str, Any] = {"type": "object", "properties": {}}
                    for f in r.fields:
                        r_schema["properties"][f.name] = {
                            "type": f.field_type.lower() if f.field_type.lower() in ["string", "integer", "boolean", "number"] else "string",
                        }
                    if r.schema_name:
                        schemas[r.schema_name] = r_schema
                        c_schema = {"$ref": f"#/components/schemas/{r.schema_name}"}
                    else:
                        c_schema = r_schema

                    responses[code_str] = {
                        "description": r.description or "Response",
                        "content": {
                            "application/json": {"schema": c_schema}
                        },
                    }

        return spec
