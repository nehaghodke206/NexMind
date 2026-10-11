"""Response normalizer and deterministic fingerprint generator."""

import hashlib
import json
from typing import Any, Dict


def extract_structural_schema(data: Any) -> Any:
    """Recursively converts data to its structural schema representation."""
    if isinstance(data, dict):
        return {k: extract_structural_schema(v) for k, v in sorted(data.items())}
    elif isinstance(data, list):
        if not data:
            return ["empty_array"]
        # Sample element structure
        return [extract_structural_schema(data[0])]
    elif isinstance(data, bool):
        return "boolean"
    elif isinstance(data, (int, float)):
        return "number"
    elif isinstance(data, str):
        return "string"
    elif data is None:
        return "null"
    return type(data).__name__


def compute_fingerprint(status_code: int, structural_schema: Any) -> str:
    """Computes a deterministic SHA256 fingerprint for a response contract."""
    contract = {
        "status_code": status_code,
        "schema": structural_schema,
    }
    dumped = json.dumps(contract, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def redact_sensitive_data(data: Any) -> Any:
    """Recursively redacts known sensitive keys."""
    sensitive_keys = {"password", "secret", "token", "api_key", "authorization", "cookie"}
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if str(k).lower() in sensitive_keys:
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = redact_sensitive_data(v)
        return cleaned
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    return data
