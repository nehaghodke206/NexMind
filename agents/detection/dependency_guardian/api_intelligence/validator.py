"""
Bounded, safe HTTP probe runner for External API Intelligence and Contract Validation.
Enforces safe read-only operations (GET/HEAD/OPTIONS), bounded concurrency, secret redaction,
and accurate categorization of network/auth/schema outcomes.
"""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
import yaml

from ..contracts.findings import (
    CompatibilityClassification,
    DetectionProvenance,
    DetectionSource,
    Finding,
    RuleId,
    SeverityLevel,
)
from .models import (
    LiveProbeEndpoint,
    LiveProbeResult,
    LiveValidationOptions,
    LiveValidationReport,
    ProbeStatus,
)

logger = logging.getLogger("dependency_guardian.api_intelligence.validator")

SENSITIVE_HEADER_KEYS: Set[str] = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "api-key",
    "apikey",
    "x-auth-token",
    "secret",
    "token",
}

SENSITIVE_PARAM_KEYS: Set[str] = {
    "key",
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "auth",
    "credential",
}


def sanitize_url(raw_url: str) -> str:
    """Redact sensitive query parameter values in URLs."""
    try:
        parsed = urlparse(raw_url)
        if not parsed.query:
            return raw_url

        query_params = parse_qsl(parsed.query, keep_blank_values=True)
        sanitized_params = []
        for k, v in query_params:
            if any(s in k.lower() for s in SENSITIVE_PARAM_KEYS):
                sanitized_params.append((k, "[REDACTED]"))
            else:
                sanitized_params.append((k, v))

        new_query = urlencode(sanitized_params)
        return urlunparse(parsed._replace(query=new_query))
    except Exception:
        return raw_url


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Return dictionary with authorization and secret header values redacted."""
    safe = {}
    for k, v in headers.items():
        if k.lower() in SENSITIVE_HEADER_KEYS or any(s in k.lower() for s in ["auth", "secret", "token"]):
            safe[k] = "[REDACTED]"
        else:
            safe[k] = str(v)
    return safe


def extract_structural_schema(data: Any, max_depth: int = 5) -> Any:
    """
    Extract structural schema (field names and primitive types)
    without retaining sensitive data values.
    """
    if max_depth <= 0:
        return "..."

    if isinstance(data, dict):
        schema = {}
        for k, v in data.items():
            schema[k] = extract_structural_schema(v, max_depth - 1)
        return schema
    elif isinstance(data, list):
        if not data:
            return []
        # Sample first item structure
        return [extract_structural_schema(data[0], max_depth - 1)]
    elif isinstance(data, bool):
        return "boolean"
    elif isinstance(data, int):
        return "integer"
    elif isinstance(data, float):
        return "number"
    elif isinstance(data, str):
        return "string"
    elif data is None:
        return "null"
    return type(data).__name__


def compute_schema_fingerprint(status_code: int, structural_schema: Any) -> str:
    """Compute stable fingerprint of response structure."""
    raw = f"{status_code}:{json.dumps(structural_schema, sort_keys=True)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class LiveApiValidator:
    """
    Executes bounded, safe read-only HTTP validation against explicitly configured endpoints.
    """

    def __init__(
        self,
        options: Optional[LiveValidationOptions] = None,
        ai_provider: Optional[Any] = None,
    ):
        self.options = options or LiveValidationOptions()
        self.ai_provider = ai_provider

    def is_method_safe(self, method: str) -> bool:
        """Enforce strict read-only HTTP operations."""
        return method.upper() in {"GET", "HEAD", "OPTIONS"}

    def is_host_allowed(self, url: str) -> Tuple[bool, Optional[str]]:
        """Validate destination host against cloud metadata and blocked hosts."""
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            if not host:
                return False, "Target URL missing valid hostname."

            for blocked in self.options.blocked_hosts:
                if host == blocked.lower() or host.endswith(f".{blocked.lower()}"):
                    return False, f"Target host '{host}' is explicitly blocked for security."

            return True, None
        except Exception as exc:
            return False, f"Malformed URL: {exc}"

    def prepare_headers(self, endpoint: LiveProbeEndpoint) -> Dict[str, str]:
        """Prepare headers with deliberate, environment-based credentials."""
        headers = dict(endpoint.headers or {})
        headers.setdefault("User-Agent", "DependencyGuardian/1.2 (Safe Probe Runner)")
        headers.setdefault("Accept", "application/json, text/plain, */*")

        if endpoint.auth_env_var:
            token = os.environ.get(endpoint.auth_env_var)
            if token:
                headers["Authorization"] = f"Bearer {token.strip()}"
            else:
                logger.warning(
                    f"Configured auth_env_var '{endpoint.auth_env_var}' is not set in environment."
                )

        return headers

    async def execute_single_probe(
        self,
        endpoint: LiveProbeEndpoint,
        client: httpx.AsyncClient,
    ) -> LiveProbeResult:
        """
        Execute an isolated safe probe with bounds, timeouts, and error classification.
        """
        method_upper = endpoint.method.upper()
        full_url = f"{endpoint.base_url.rstrip('/')}/{endpoint.path.lstrip('/')}"
        clean_url = sanitize_url(full_url)

        # 1. Safety verification: read-only check
        if not self.is_method_safe(method_upper):
            err_msg = (
                f"Mutating HTTP method '{method_upper}' rejected. "
                "Live API validation strictly requires safe read-only methods (GET, HEAD, OPTIONS)."
            )
            finding = Finding(
                rule_id="RULE-API-SECURITY-MUTATING-METHOD-BLOCKED",
                fingerprint=f"live:sec:method:{endpoint.id}",
                compatibility=CompatibilityClassification.BREAKING,
                severity=SeverityLevel.CRITICAL,
                path=endpoint.path or clean_url,
                method=method_upper,
                schema_location="request.method",
                previous_value="GET/HEAD/OPTIONS",
                current_value=method_upper,
                message=err_msg,
                evidence={"url": clean_url, "method": method_upper, "reason": "Unsafe mutating method rejected upfront"},
                provenance="live_probe",
                recommended_action="Use safe read-only methods (GET, HEAD, OPTIONS) for live contract validation.",
            )
            return LiveProbeResult(
                endpoint_id=endpoint.id,
                service_name=endpoint.service_name,
                url=clean_url,
                method=method_upper,
                status_code=0,
                status=ProbeStatus.SECURITY_BLOCKED,
                latency_ms=0.0,
                error_message=err_msg,
                fingerprint="blocked_method",
                findings=[finding],
            )

        # 2. Safety verification: target host check
        is_allowed, block_reason = self.is_host_allowed(full_url)
        if not is_allowed:
            err_msg = block_reason or "Blocked target host"
            finding = Finding(
                rule_id="RULE-API-SECURITY-HOST-BLOCKED",
                fingerprint=f"live:sec:host:{endpoint.id}",
                compatibility=CompatibilityClassification.BREAKING,
                severity=SeverityLevel.CRITICAL,
                path=endpoint.path or clean_url,
                method=method_upper,
                schema_location="request.host",
                previous_value="allowed_host",
                current_value=clean_url,
                message=f"Target host security violation: {err_msg}",
                evidence={"url": clean_url, "reason": err_msg},
                provenance="live_probe",
                recommended_action="Remove cloud metadata or forbidden internal IPs from live validation targets.",
            )
            return LiveProbeResult(
                endpoint_id=endpoint.id,
                service_name=endpoint.service_name,
                url=clean_url,
                method=method_upper,
                status_code=0,
                status=ProbeStatus.SECURITY_BLOCKED,
                latency_ms=0.0,
                error_message=err_msg,
                fingerprint="blocked_host",
                findings=[finding],
            )

        headers = self.prepare_headers(endpoint)
        start_time = time.perf_counter()

        try:
            err_msg: Optional[str] = None
            resp = await client.request(
                method=method_upper,
                url=full_url,
                headers=headers,
            )
            latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            status_code = resp.status_code
            safe_resp_headers = sanitize_headers(dict(resp.headers))

            # Check response size limit
            if len(resp.content) > self.options.max_response_bytes:
                err = f"Response size ({len(resp.content)} bytes) exceeds limit ({self.options.max_response_bytes} bytes)"
                return LiveProbeResult(
                    endpoint_id=endpoint.id,
                    service_name=endpoint.service_name,
                    url=clean_url,
                    method=method_upper,
                    status_code=status_code,
                    status=ProbeStatus.SERVER_FAILURE,
                    latency_ms=latency_ms,
                    error_message=err,
                    fingerprint="oversized_response",
                    safe_headers=safe_resp_headers,
                )

            # Parse response structure safely
            structural_schema: Optional[Dict[str, Any]] = None
            try:
                json_data = resp.json()
                structural_schema = extract_structural_schema(json_data)
            except Exception:
                structural_schema = {"type": "non_json", "content_type": resp.headers.get("content-type", "unknown")}

            fingerprint = compute_schema_fingerprint(status_code, structural_schema)
            findings: List[Finding] = []

            # Outcome classification
            if 200 <= status_code < 300:
                probe_status = ProbeStatus.REACHABLE

                # Check expected status
                if endpoint.expected_status_code and status_code != endpoint.expected_status_code:
                    probe_status = ProbeStatus.CONTRACT_MISMATCH
                    findings.append(
                        Finding(
                            rule_id="RULE-API-STATUS-MISMATCH",
                            fingerprint=f"live:status:{endpoint.id}",
                            compatibility=CompatibilityClassification.BREAKING,
                            severity=SeverityLevel.HIGH,
                            path=endpoint.path,
                            method=method_upper,
                            schema_location=f"response.status_code",
                            previous_value=endpoint.expected_status_code,
                            current_value=status_code,
                            message=f"Endpoint '{endpoint.service_name}' returned status {status_code}, expected {endpoint.expected_status_code}.",
                            evidence={"url": clean_url, "latency_ms": latency_ms, "headers": safe_resp_headers},
                            provenance="live_probe",
                            recommended_action=f"Verify upstream {endpoint.service_name} status code requirements.",
                        )
                    )

                # Check expected schema fields
                if endpoint.expected_fields and isinstance(structural_schema, dict):
                    missing_fields = [f for f in endpoint.expected_fields if f not in structural_schema]
                    if missing_fields:
                        probe_status = ProbeStatus.CONTRACT_MISMATCH
                        findings.append(
                            Finding(
                                rule_id="RULE-API-FIELD-REMOVED",
                                fingerprint=f"live:schema:{endpoint.id}:{'-'.join(missing_fields)}",
                                compatibility=CompatibilityClassification.BREAKING,
                                severity=SeverityLevel.CRITICAL,
                                path=endpoint.path,
                                method=method_upper,
                                schema_location="response.body",
                                previous_value=endpoint.expected_fields,
                                current_value=list(structural_schema.keys()),
                                message=f"Live response from '{endpoint.service_name}' missing expected field(s): {', '.join(missing_fields)}.",
                                evidence={
                                    "url": clean_url,
                                    "missing_fields": missing_fields,
                                    "observed_schema": structural_schema,
                                },
                                provenance="live_probe",
                                recommended_action="Inspect dependent code to handle updated schema or apply repair.",
                            )
                        )

            elif status_code in (401, 403):
                probe_status = ProbeStatus.AUTH_FAILURE
                findings.append(
                    Finding(
                        rule_id="RULE-API-AUTH-FAILURE",
                        fingerprint=f"live:auth:{endpoint.id}",
                        compatibility=CompatibilityClassification.BREAKING,
                        severity=SeverityLevel.HIGH,
                        path=endpoint.path,
                        method=method_upper,
                        schema_location="headers.authorization",
                        previous_value="200 OK",
                        current_value=f"{status_code} Unauthorized/Forbidden",
                        message=f"Live probe to '{endpoint.service_name}' failed with HTTP {status_code} ({'Unauthorized' if status_code == 401 else 'Forbidden'}).",
                        evidence={"url": clean_url, "status_code": status_code, "auth_env_var": endpoint.auth_env_var},
                        provenance="live_probe",
                        recommended_action=f"Configure or refresh credentials in environment variable '{endpoint.auth_env_var or 'API_KEY'}'.",
                    )
                )
            elif 400 <= status_code < 500:
                probe_status = ProbeStatus.CLIENT_ERROR
                findings.append(
                    Finding(
                        rule_id="RULE-API-CLIENT-ERROR",
                        fingerprint=f"live:client:{endpoint.id}:{status_code}",
                        compatibility=CompatibilityClassification.POTENTIALLY_BREAKING,
                        severity=SeverityLevel.MEDIUM,
                        path=endpoint.path,
                        method=method_upper,
                        schema_location="response.status",
                        previous_value=200,
                        current_value=status_code,
                        message=f"Live request to '{endpoint.service_name}' returned client error {status_code} ({resp.reason_phrase}).",
                        evidence={"url": clean_url, "status_code": status_code},
                        provenance="live_probe",
                        recommended_action="Verify request parameters and endpoint path exist on target service.",
                    )
                )
            else:
                probe_status = ProbeStatus.SERVER_FAILURE
                ev_data: Dict[str, Any] = {"url": clean_url, "status_code": status_code}
                diag_msg = None
                if isinstance(json_data, dict):
                    detail_val = json_data.get("detail")
                    if isinstance(detail_val, dict):
                        ev_data.update(detail_val)
                        if "target_url" in detail_val:
                            try:
                                from urllib.parse import urlparse
                                parsed_t = urlparse(detail_val["target_url"])
                                if parsed_t.path:
                                    ev_data["invalid_path"] = parsed_t.path
                            except Exception:
                                pass
                        if "message" in detail_val:
                            diag_msg = detail_val["message"]
                    elif isinstance(detail_val, str):
                        ev_data["detail_message"] = detail_val
                        diag_msg = detail_val

                finding_msg = (
                    f"Upstream service '{endpoint.service_name}' returned server failure {status_code}: {diag_msg}"
                    if diag_msg
                    else f"Upstream service '{endpoint.service_name}' returned server failure {status_code}."
                )

                findings.append(
                    Finding(
                        rule_id="RULE-API-SERVER-FAILURE",
                        fingerprint=f"live:server:{endpoint.id}:{status_code}",
                        compatibility=CompatibilityClassification.BREAKING,
                        severity=SeverityLevel.HIGH,
                        path=endpoint.path,
                        method=method_upper,
                        schema_location="response.status",
                        previous_value=200,
                        current_value=status_code,
                        message=finding_msg,
                        evidence=ev_data,
                        provenance="live_probe",
                        recommended_action=f"Check {endpoint.service_name} service health and logs.",
                    )
                )

            outcome_err = err_msg or (findings[0].message if findings else None)
            return LiveProbeResult(
                endpoint_id=endpoint.id,
                service_name=endpoint.service_name,
                url=clean_url,
                method=method_upper,
                status_code=status_code,
                status=probe_status,
                latency_ms=latency_ms,
                error_message=outcome_err if probe_status != ProbeStatus.REACHABLE else None,
                fingerprint=fingerprint,
                safe_headers=safe_resp_headers,
                structural_schema=structural_schema,
                findings=findings,
            )

        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.NetworkError) as net_err:
            latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            err_type = type(net_err).__name__
            err_msg = f"Network connection failed ({err_type}): {net_err}"

            # Notice: Single probe failure does not mark service broken; marked as unreachable probe
            finding = Finding(
                rule_id="RULE-API-UNREACHABLE",
                fingerprint=f"live:unreachable:{endpoint.id}",
                compatibility=CompatibilityClassification.POTENTIALLY_BREAKING,
                severity=SeverityLevel.MEDIUM,
                path=endpoint.path,
                method=method_upper,
                schema_location="network.connectivity",
                previous_value="reachable",
                current_value=err_type,
                message=f"Endpoint '{endpoint.service_name}' unreachable after {latency_ms}ms ({err_type}). Service may be offline or address misconfigured.",
                evidence={"url": clean_url, "latency_ms": latency_ms, "error": str(net_err)},
                provenance="live_probe",
                recommended_action=f"Ensure target service '{endpoint.service_name}' is running at '{endpoint.base_url}'.",
            )

            return LiveProbeResult(
                endpoint_id=endpoint.id,
                service_name=endpoint.service_name,
                url=clean_url,
                method=method_upper,
                status_code=0,
                status=ProbeStatus.UNREACHABLE,
                latency_ms=latency_ms,
                error_message=err_msg,
                fingerprint="probe_unreachable",
                findings=[finding],
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            err_msg = f"Probe execution error: {exc}"
            return LiveProbeResult(
                endpoint_id=endpoint.id,
                service_name=endpoint.service_name,
                url=clean_url,
                method=method_upper,
                status_code=0,
                status=ProbeStatus.UNREACHABLE,
                latency_ms=latency_ms,
                error_message=err_msg,
                fingerprint="probe_error",
            )

    async def validate_endpoints(
        self,
        endpoints: List[LiveProbeEndpoint],
        on_progress: Optional[Any] = None,
    ) -> LiveValidationReport:
        """
        Validate multiple endpoints concurrently with bounded concurrency and timeouts.
        """
        start_time = time.perf_counter()
        bounded_endpoints = endpoints[: self.options.max_requests]
        semaphore = asyncio.Semaphore(self.options.max_concurrency)

        timeout = httpx.Timeout(self.options.timeout_seconds)
        limits = httpx.Limits(max_connections=self.options.max_concurrency, max_keepalive_connections=2)

        results: List[LiveProbeResult] = []
        all_findings: List[Finding] = []
        total = len(bounded_endpoints)

        async with httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=False) as client:
            async def bounded_worker(idx: int, ep: LiveProbeEndpoint) -> LiveProbeResult:
                async with semaphore:
                    if on_progress:
                        on_progress({
                            "phase": "validating_external_apis",
                            "message": f"Validating API ({idx}/{total}): {ep.service_name} {ep.path}",
                            "endpoint_id": ep.id,
                            "files_processed": idx,
                            "total_files": total,
                        })
                    res = await self.execute_single_probe(ep, client)
                    return res

            tasks = [bounded_worker(i, ep) for i, ep in enumerate(bounded_endpoints, start=1)]
            results = await asyncio.gather(*tasks)

        for res in results:
            all_findings.extend(res.findings)

        duration = round(time.perf_counter() - start_time, 2)

        report = LiveValidationReport(
            total_probes=len(results),
            reachable_count=sum(1 for r in results if r.status == ProbeStatus.REACHABLE),
            auth_failure_count=sum(1 for r in results if r.status == ProbeStatus.AUTH_FAILURE),
            client_error_count=sum(1 for r in results if r.status == ProbeStatus.CLIENT_ERROR),
            server_failure_count=sum(1 for r in results if r.status == ProbeStatus.SERVER_FAILURE),
            unreachable_count=sum(1 for r in results if r.status == ProbeStatus.UNREACHABLE),
            contract_mismatch_count=sum(1 for r in results if r.status == ProbeStatus.CONTRACT_MISMATCH),
            security_blocked_count=sum(1 for r in results if r.status == ProbeStatus.SECURITY_BLOCKED),
            duration_seconds=duration,
            results=results,
            findings=all_findings,
        )

        return report

    @classmethod
    def load_endpoints_from_yaml(cls, config_path: str) -> List[LiveProbeEndpoint]:
        """Load configured probe endpoints from dependency-guardian.yml."""
        path = os.path.abspath(config_path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        endpoints: List[LiveProbeEndpoint] = []
        deps = data.get("dependencies", [])

        for dep in deps:
            dep_id = dep.get("id", "dep")
            dep_name = dep.get("name", dep_id)
            base_url = dep.get("base_url", "http://localhost")
            probes = dep.get("probes", [])

            for p in probes:
                method = (p.get("method") or "GET").upper()
                expected_st = p.get("expected_status_code", p.get("expected_status", 200))
                endpoints.append(
                    LiveProbeEndpoint(
                        id=f"{dep_id}:{p.get('id', p.get('path', 'probe'))}",
                        service_name=dep_name,
                        base_url=base_url,
                        path=p.get("path", "/"),
                        method=method,
                        headers=p.get("headers", {}),
                        auth_env_var=p.get("auth_env_var"),
                        expected_contract=p.get("expected_contract"),
                        expected_status_code=int(expected_st) if expected_st is not None else 200,
                        expected_fields=p.get("expected_fields", []),
                        known_values=p.get("known_values", {}),
                        is_safe_readonly=p.get("is_safe_readonly", True),
                    )
                )

        # Support discovered external integrations from repository-inventory.json
        if not endpoints:
            integrations = data.get("integrations", [])
            for idx, it in enumerate(integrations):
                url = it.get("target_url_or_host", "")
                if url and (url.startswith("http://") or url.startswith("https://")) and "{" not in url:
                    ops = it.get("operations", ["GET"])
                    safe_op = next((op.upper() for op in ops if op.upper() in {"GET", "HEAD", "OPTIONS"}), "GET")
                    svc_name = it.get("service_name") or f"Discovered Integration {idx+1}"
                    parsed = urlparse(url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    path = parsed.path or "/"
                    if parsed.query:
                        path += f"?{parsed.query}"
                    endpoints.append(
                        LiveProbeEndpoint(
                            id=f"discovered:{idx}:{parsed.netloc}",
                            service_name=svc_name,
                            base_url=base_url,
                            path=path,
                            method=safe_op,
                            expected_status_code=200,
                        )
                    )

        return endpoints
