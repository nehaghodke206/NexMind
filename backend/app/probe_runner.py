"""Bounded HTTP probe runner for executing endpoint health and contract checks."""

import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx

from .config import DependencyConfig, ProbeConfig, SettingsConfig
from .models import ProbeResult
from .normalizer import extract_structural_schema, compute_fingerprint, redact_sensitive_data


async def execute_probe(
    dependency: DependencyConfig,
    probe: ProbeConfig,
    settings: SettingsConfig,
) -> ProbeResult:
    """Executes a single HTTP probe with strict bounds, timeouts, and normalization."""
    url = f"{dependency.base_url}{probe.path}"
    
    # Target safety check: block cloud metadata IP
    if "169.254.169.254" in url:
        return ProbeResult(
            probe_id=probe.id,
            dependency_id=dependency.id,
            method=probe.method,
            path=probe.path,
            status_code=403,
            body={"error": "Access to cloud metadata endpoints is strictly blocked."},
            latency_ms=0.0,
            observed_at=datetime.now(timezone.utc).isoformat(),
            fingerprint="security_blocked",
            error="Forbidden target IP: Cloud metadata service blocked.",
        )

    headers = dict(probe.headers or {})
    start_time = time.perf_counter()
    error_msg = None
    status_code = 0
    safe_body = None
    fingerprint = ""

    timeout = httpx.Timeout(settings.request_timeout_seconds)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            request_args: Dict[str, Any] = {
                "method": probe.method,
                "url": url,
                "headers": headers,
            }
            response = await client.request(**request_args)
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            status_code = response.status_code

            # Bounded response size check
            if len(response.content) > settings.max_response_bytes:
                error_msg = f"Response size ({len(response.content)} bytes) exceeds limit ({settings.max_response_bytes} bytes)"
                safe_body = {"error": error_msg}
                fingerprint = "oversized_response"
            else:
                try:
                    json_data = response.json()
                    safe_body = redact_sensitive_data(json_data)
                    schema = extract_structural_schema(safe_body)
                    fingerprint = compute_fingerprint(status_code, schema)
                except Exception:
                    # Non-JSON response
                    safe_body = {"raw_text": response.text[:1000]}
                    fingerprint = compute_fingerprint(status_code, "text/plain")

    except Exception as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        status_code = 0
        error_msg = str(exc)
        safe_body = {"error": error_msg}
        fingerprint = "probe_failed"

    # Redact sensitive headers
    safe_headers = {}
    if "response" in locals() and hasattr(response, "headers"):
        for k, v in response.headers.items():
            if k.lower() in {"authorization", "cookie", "set-cookie"}:
                safe_headers[k] = "[REDACTED]"
            else:
                safe_headers[k] = v

    return ProbeResult(
        probe_id=probe.id,
        dependency_id=dependency.id,
        method=probe.method,
        path=probe.path,
        status_code=status_code,
        headers=safe_headers,
        body=safe_body,
        latency_ms=round(latency_ms, 2),
        observed_at=datetime.now(timezone.utc).isoformat(),
        fingerprint=fingerprint,
        error=error_msg,
    )
